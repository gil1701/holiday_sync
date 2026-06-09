import os
import datetime
import urllib.parse
import urllib.request
import logging
import frappe
from frappe import _

def get_logger():
    """
    Returns a logger that writes to both the console and a file in the site's logs directory.
    """
    logger_name = "holiday_sync"
    log = logging.getLogger(logger_name)
    
    # If the logger already has handlers, don't add more (prevents duplicate logs)
    if log.handlers:
        return log

    log.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console Handler (Stdout)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    log.addHandler(ch)

    # File Handler
    try:
        # Try to get the site path. If we are in a request context, frappe.get_site_path() works.
        # Otherwise, we might be in a scheduler/CLI context.
        site_path = None
        
        # Log to confirm we entered get_logger
        print(f"DEBUG: Initializing logger for {logger_name}")

        try:
            if hasattr(frappe, "local") and hasattr(frappe.local, "site"):
                site_path = frappe.get_site_path()
        except Exception as e:
            print(f"DEBUG: frappe.get_site_path() failed: {str(e)}")
            pass
        
        if not site_path:
            # Try searching in current directory structure for a 'sites' folder
            # Common in frappe-bench
            if os.path.exists("sites"):
                # If we are in frappe-bench root
                # Note: We need to know WHICH site. If there is only one site, we can guess.
                # However, without frappe.local.site, it's risky.
                pass 
            elif os.path.exists("../../sites"):
                # If we are in apps/holiday_sync/holiday_sync
                pass

        # Try another way to get site path if frappe.local.site is missing
        if not site_path and hasattr(frappe, "get_site_path"):
             try:
                 # In some CLI contexts, it might work even without .local.site if passed via --site
                 site_path = frappe.get_site_path()
             except:
                 pass

        if site_path:
            log_dir = os.path.join(site_path, "logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, f"{logger_name}.log")
            fh = logging.FileHandler(log_file)
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            log.addHandler(fh)
            print(f"DEBUG: Logging to {log_file}")
        else:
            # Fallback for log file in a writable temporary directory if site_path is not found
            import tempfile
            temp_log = os.path.join(tempfile.gettempdir(), f"{logger_name}_emergency.log")
            try:
                # Test permissions if file exists
                fh = logging.FileHandler(temp_log)
                fh.setLevel(logging.DEBUG)
                fh.setFormatter(formatter)
                log.addHandler(fh)
                print(f"DEBUG: Site path not found. Logging to emergency log: {temp_log}")
            except Exception:
                # Last resort: fallback in current directory
                try:
                    fh = logging.FileHandler(f"{logger_name}_fallback.log")
                    fh.setLevel(logging.DEBUG)
                    fh.setFormatter(formatter)
                    log.addHandler(fh)
                except:
                    pass
    except Exception as e:
        print(f"DEBUG: Critical error in get_logger: {str(e)}")
        pass

    return log

# Exceptions list for Google Calendar ID
CALENDAR_EXCEPTIONS = {
    "au": "australian",
    "at": "austrian",
    "br": "brazilian",
    "bg": "bulgarian",
    "ca": "canadian",
    "cn": "china",
    "hr": "croatian",
    "cz": "czech",
    "dk": "danish",
    "fi": "finnish",
    "fr": "french",
    "de": "german",
    "gr": "greek",
    "hu": "hungarian",
    "in": "indian",
    "id": "indonesian",
    "ie": "irish",
    "it": "italian",
    "jp": "japanese",
    "lv": "latvian",
    "lt": "lithuanian",
    "my": "malaysia",
    "mx": "mexican",
    "nl": "dutch",
    "nz": "new_zealand",
    "no": "norwegian",
    "ph": "philippines",
    "pl": "polish",
    "pt": "portuguese",
    "ro": "romanian",
    "ru": "russian",
    "sa": "saudiarabian",
    "sg": "singapore",
    "sk": "slovak",
    "si": "slovenian",
    "kr": "south_korea",
    "es": "spain",
    "se": "swedish",
    "tr": "turkish",
    "ua": "ukrainian",
    "us": "usa",
    "vn": "vietnamese",
}

COUNTRY_NAME_TO_CODE = {
    "dominican republic": "do",
    "república dominicana": "do",
    "republica dominicana": "do",
    "united states": "us",
    "estados unidos": "us",
    "spain": "es",
    "españa": "es",
    "mexico": "mx",
    "méxico": "mx",
    "chile": "cl",
    "colombia": "co",
    "argentina": "ar",
    "peru": "pe",
    "perú": "pe",
    "venezuela": "ve",
    "ecuador": "ec",
    "panama": "pa",
    "panamá": "pa",
    "costa rica": "cr",
    "canada": "ca",
    "canadá": "ca",
    "brazil": "br",
    "brasil": "br",
    "united kingdom": "gb",
    "reino unido": "gb",
}

def get_calendar_id(country_code, lang="en"):
    """
    Construct Google Calendar ID based on country code.
    Standard format: {lang}.{country_code_or_name}.official#holiday@group.v.calendar.google.com
    """
    log = get_logger()
    log.debug(f"Getting calendar ID for country code: {country_code}")
    code = country_code.lower().strip()
    
    # ISO-2 corrections for Google Calendar
    if code == "gb":
        code = "uk"
    elif code == "za":
        code = "sa"
        
    country_identifier = CALENDAR_EXCEPTIONS.get(code, code)
    log.debug(f"Country Identifier resolved: {country_identifier}")
    return f"{lang}.{country_identifier}.official#holiday@group.v.calendar.google.com"

def fetch_raw_ics(calendar_id):
    """
    Fetches the raw .ics text content of the public Google Calendar.
    """
    log = get_logger()
    log.info(f"Fetching ICS for calendar ID: {calendar_id}")
    encoded_id = urllib.parse.quote(calendar_id)
    url = f"https://calendar.google.com/calendar/ical/{encoded_id}/public/basic.ics"
    
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        log.error(f"Failed to fetch ICS from {url}: {str(e)}")
        frappe.log_error(message=f"Failed to fetch ICS from {url}: {str(e)}", title="Holiday Sync Fetch Error")
        raise e

def parse_ics_holidays(ics_text, target_year=None):
    """
    Parses ICS content and returns list of dictionaries containing 'date' (YYYY-MM-DD) and 'summary'.
    Filters by target_year if specified.
    """
    log = get_logger()
    log.debug(f"Parsing ICS for year: {target_year}")
    unfolded_lines = []
    for line in ics_text.splitlines():
        if not line:
            continue
        if line.startswith(" ") or line.startswith("\t"):
            if unfolded_lines:
                unfolded_lines[-1] += line[1:]
        else:
            unfolded_lines.append(line)
            
    holidays = []
    current_event = {}
    in_event = False
    
    for line in unfolded_lines:
        if line.startswith("BEGIN:VEVENT"):
            in_event = True
            current_event = {}
        elif line.startswith("END:VEVENT"):
            in_event = False
            if "date" in current_event and "summary" in current_event:
                event_year = int(current_event["date"].split("-")[0])
                if target_year is None or event_year == int(target_year):
                    holidays.append(current_event)
        elif in_event:
            parts = line.split(":", 1)
            if len(parts) == 2:
                key, val = parts[0], parts[1]
                if key.startswith("DTSTART"):
                    # Extract date YYYYMMDD from string
                    date_str = "".join(c for c in val if c.isdigit())[:8]
                    if len(date_str) == 8:
                        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                        current_event["date"] = formatted_date
                elif key.startswith("SUMMARY"):
                    # Unescape characters commonly escaped in ICS
                    summary = val.replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\").strip()
                    current_event["summary"] = summary
                    
    seen = set()
    deduplicated = []
    for h in holidays:
        key = (h["date"], h["summary"])
        if key not in seen:
            seen.add(key)
            deduplicated.append(h)
            
    deduplicated.sort(key=lambda x: x["date"])
    return deduplicated

def sync_holidays(company, year, silent=True):
    """
    Core function to sync holidays for a company and year.
    Creates the Holiday List if it doesn't exist, updates it if it does,
    and links it to the Company defaults.
    """
    log = get_logger()
    log.info(f"Syncing holidays for Company: {company}, Year: {year}")
    
    # 0. Check if DB is connected
    try:
        frappe.db.connect()
    except Exception as e:
        log.warning(f"Note: frappe.db.connect() failed (might be already connected): {str(e)}")

    # 1. Get company's country name
    try:
        country_name = frappe.db.get_value("Company", company, "country")
    except Exception as e:
        log.error(f"Error fetching country for company {company}: {str(e)}")
        if silent: return None
        frappe.throw(_("Error fetching country for company {0}").format(company))

    if not country_name:
        log.warning(f"Company {company} does not have a country set.")
        if silent:
            return None
        frappe.throw(_("Company {0} does not have a country set.").format(company))
        
    # 2. Resolve country code
    country_code = frappe.db.get_value("Country", country_name, "code")
    code = country_code.lower().strip() if country_code else None
    
    if not code:
        log.error(f"Could not resolve country code for country '{country_name}' of company '{company}'.")
        if silent:
            return None
        frappe.throw(
            _("Could not resolve country code for country '{0}' of company '{1}'.").format(country_name, company)
        )
        
    # 3. Get calendar ID and fetch raw ICS
    lang = "en"
    settings_name = "Google Holiday Sync Settings"
    if frappe.db.exists("DocType", settings_name):
        settings = frappe.get_single(settings_name)
        lang = settings.language or "en"
        
    calendar_id = get_calendar_id(code, lang)
    
    try:
        ics_text = fetch_raw_ics(calendar_id)
        log.debug(f"Successfully fetched ICS for {calendar_id}")
    except Exception as e:
        if lang != "en":
            # Fallback to English
            try:
                log.info(f"Retrying with English fallback for {code}")
                calendar_id = get_calendar_id(code, "en")
                ics_text = fetch_raw_ics(calendar_id)
            except Exception as fallback_err:
                log.error(f"Error fetching calendar (fallback) for code {code}: {str(fallback_err)}")
                frappe.log_error(
                    message=f"Error fetching calendar for code {code}: {str(fallback_err)}",
                    title="Google Holiday Sync Fetch Failed"
                )
                if silent:
                    return None
                raise fallback_err
        else:
            log.error(f"Error fetching calendar for code {code}: {str(e)}")
            frappe.log_error(
                message=f"Error fetching calendar for code {code}: {str(e)}",
                title="Google Holiday Sync Fetch Failed"
            )
            if silent:
                return None
            raise e
            
    # 4. Parse events
    holidays_data = parse_ics_holidays(ics_text, target_year=year)
    log.info(f"Parsed {len(holidays_data)} holidays from ICS")
    if not holidays_data:
        if not silent:
            frappe.msgprint(_("No holidays found in Google Calendar for country code {0} and year {1}.").format(code, year))
        return None
        
    # 5. Create or update Holiday List
    holiday_list_name = f"Holidays - {company} - {year}"
    
    if frappe.db.exists("Holiday List", holiday_list_name):
        log.debug(f"Updating existing Holiday List: {holiday_list_name}")
        holiday_list = frappe.get_doc("Holiday List", holiday_list_name)
        holiday_list.set("holidays", [])
    else:
        log.debug(f"Creating new Holiday List: {holiday_list_name}")
        holiday_list = frappe.new_doc("Holiday List")
        holiday_list.holiday_list_name = holiday_list_name
        holiday_list.from_date = f"{year}-01-01"
        holiday_list.to_date = f"{year}-12-31"
        
    # Append holidays
    for hol in holidays_data:
        holiday_list.append("holidays", {
            "holiday_date": hol["date"],
            "description": hol["summary"]
        })
        
    holiday_list.save(ignore_permissions=True)
    frappe.db.commit()
    log.info(f"Saved Holiday List {holiday_list_name}")
    
    # 6. Set as default holiday list for the company
    try:
        if frappe.db.get_value("Company", company, "default_holiday_list") != holiday_list_name:
            log.info(f"Setting {holiday_list_name} as default for company {company}")
            frappe.db.set_value("Company", company, "default_holiday_list", holiday_list_name, update_modified=False)
            frappe.db.commit()
    except Exception as e:
        log.error(f"Error setting default holiday list for {company}: {str(e)}")
        # Don't fail the whole sync if only setting the default fails
        pass
    
    return holiday_list_name

@frappe.whitelist()
def sync_company_holidays(company, year=None):
    """
    Exposed whitelisted API to sync holidays manually.
    """
    if not year:
        year = datetime.datetime.now().year
    year = int(year)
    
    holiday_list_name = sync_holidays(company, year, silent=False)
    if holiday_list_name:
        frappe.msgprint(
            _("Successfully synced holidays for Company {0} and set '{1}' as the default Holiday List.").format(
                company, holiday_list_name
            )
        )
    return holiday_list_name

def sync_all_companies_holidays():
    """
    Run sync for all companies for the current year (called by scheduler).
    """
    log = get_logger()
    try:
        year = datetime.datetime.now().year
        companies = frappe.get_all("Company", fields=["name"])
        log.info(f"Syncing holidays for {len(companies)} companies for year {year}...")
    
        # Ensure DB connection for scheduled task
        try:
            if not frappe.db:
                frappe.connect()
        except Exception as e:
            log.warning(f"Could not ensure DB connection in sync_all_companies_holidays: {str(e)}")
    
        success_count = 0
        fail_count = 0
        
        for comp in companies:
            company_name = comp["name"]
            try:
                res = sync_holidays(company_name, year, silent=True)
                if res:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                log.error(f"Failed to sync holidays for company {company_name} on Scheduler Event: {str(e)}")
                frappe.log_error(
                    message=f"Failed to sync holidays for company {company_name} on Scheduler Event: {str(e)}",
                    title="Google Holiday Sync Scheduled Job Failed"
                )
                
        log.info(f"Scheduled sync complete. Success: {success_count}, Failed: {fail_count}")
    except Exception as e:
        log.critical(f"Critical error in scheduled task sync_all_companies_holidays: {str(e)}")
        frappe.log_error(message=frappe.get_traceback(), title="Holiday Sync Critical Failure")