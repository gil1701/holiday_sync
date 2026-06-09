app_name = "holiday_sync"
app_title = "Holiday Sync"
app_publisher = "Antigravity"
app_description = "Syncs holidays from Google Calendar into ERPNext Holiday Lists based on company country"
app_email = "antigravity@google.com"
app_license = "mit"

# Apps
# ------------------
required_apps = ["erpnext"]

# DocType JS
# ------------------
doctype_js = {
    "Company": "public/js/company.js"
}

# Scheduler Events
# ----------------
scheduler_events = {
    "cron": {
        "0 0 1 1 *": [
            "holiday_sync.holiday_sync.utils.sync_all_companies_holidays"
        ]
    }
}
