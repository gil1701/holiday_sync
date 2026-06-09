import datetime
import urllib.parse
import urllib.request
import frappe
from frappe import _

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
    print(f"Getting calendar ID for country code: {country_code}")
    code = country_code.lower().strip()
    print(f"Resolved code: {code}")
    
    # ISO-2 corrections for Google Calendar
    if code == "gb":
        code = "uk"
    elif code == "za":
        code = "sa"
        
    country_identifier = CALENDAR_EXCEPTIONS.get(code, code)
    print(f"Country Identifier: {country_identifier}")
    return f"{lang}.{country_identifier}.official#holiday@group.v.calendar.google.com"

def fetch_raw_ics(calendar_id):
    """
    Fetches the raw .ics text content of the public Google Calendar.
    """
    print(f"Fetching ICS for calendar ID: {calendar_id}")
    encoded_id = urllib.parse.quote(calendar_id)
    print(f"Encoded ID: {encoded_id}")
    url = f"https://calendar.google.com/calendar/ical/{encoded_id}/public/basic.ics"
    
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        print(f"Request URL: {req.get_full_url()}")
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        frappe.log_error(message=f"Failed to fetch ICS from {url}: {str(e)}", title="Holiday Sync Fetch Error")
        raise e

def parse_ics_holidays(ics_text, target_year=None):
    """
    Parses ICS content and returns list of dictionaries containing 'date' (YYYY-MM-DD) and 'summary'.
    Filters by target_year if specified.
    """
    print(f"Parsing ICS for year: {target_year}")
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
    print(f"Syncing holidays for Company: {company}, Year: {year}")
    # 1. Get company's country name
    country_name = frappe.db.get_value("Company", company, "country")
    print(f"Country Name: {country_name}")
    if not country_name:
        if silent:
            return None
        frappe.throw(_("Company {0} does not have a country set.").format(company))
        
    # 2. Resolve country code
    country_code = frappe.db.get_value("Country", country_name, "code")
    print(f"Country Code: {country_code}")
    code = country_code.lower().strip() if country_code else None
    print(f"Resolved Code: {code}")
    
    if not code:
        # Try fuzzy match or more options if needed
        pass
        
    if not code:
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
        print(f"Settings: {settings}")
        lang = settings.language or "en"
        print(f"Language: {lang}")
        
    calendar_id = get_calendar_id(code, lang)
    print(f"Calendar ID: {calendar_id}")
    
    try:
        ics_text = fetch_raw_ics(calendar_id)
        print(f"Fetched ICS Text: {ics_text[:100]}...")
    except Exception as e:
        if lang != "en":
            # Fallback to English
            try:
                calendar_id = get_calendar_id(code, "en")
                ics_text = fetch_raw_ics(calendar_id)
            except Exception as fallback_err:
                frappe.log_error(
                    message=f"Error fetching calendar for code {code}: {str(fallback_err)}",
                    title="Google Holiday Sync Fetch Failed"
                )
                if silent:
                    return None
                raise fallback_err
        else:
            frappe.log_error(
                message=f"Error fetching calendar for code {code}: {str(e)}",
                title="Google Holiday Sync Fetch Failed"
            )
            if silent:
                return None
            raise e
            
    # 4. Parse events
    holidays_data = parse_ics_holidays(ics_text, target_year=year)
    print(f"Parsed Holidays: {len(holidays_data)}")
    if not holidays_data:
        if not silent:
            frappe.msgprint(_("No holidays found in Google Calendar for country code {0} and year {1}.").format(code, year))
        return None
        
    # 5. Create or update Holiday List
    holiday_list_name = f"Holidays - {company} - {year}"
    print(f"Holiday List Name: {holiday_list_name}")
    
    if frappe.db.exists("Holiday List", holiday_list_name):
        holiday_list = frappe.get_doc("Holiday List", holiday_list_name)
        holiday_list.set("holidays", [])
    else:
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
    
    # 6. Set as default holiday list for the company
    if frappe.db.get_value("Company", company, "default_holiday_list") != holiday_list_name:
        frappe.db.set_value("Company", company, "default_holiday_list", holiday_list_name, update_modified=False)
    
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
    year = datetime.datetime.now().year
    companies = frappe.get_all("Company", fields=["name"])
    print(f"Syncing holidays for {len(companies)} companies for year {year}...")
    
    success_count = 0
    fail_count = 0
    
    for comp in companies:
        company_name = comp["name"]
        print(f"Syncing holidays for company: {company_name}")
        try:
            res = sync_holidays(company_name, year, silent=True)
            print(f"Sync result for {company_name}: {res}")
            if res:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            fail_count += 1
            frappe.log_error(
                message=f"Failed to sync holidays for company {company_name} on Scheduler Event: {str(e)}",
                title="Google Holiday Sync Scheduled Job Failed"
            )
            
    print(f"Scheduled sync complete. Success: {success_count}, Failed: {fail_count}")