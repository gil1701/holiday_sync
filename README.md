# Holiday Sync App for ERPNext 16

A custom Frappe application designed for ERPNext 16 to sync and manage company holidays automatically from Google Calendar.

## Features

1. **Google Calendar Integration**: Fetches public holiday lists directly from Google Calendar's public iCal (.ics) endpoints. Does not require configuration of Google Cloud API keys.
2. **Dynamic Country Resolution**: Automatically maps the company's country to the correct Google Calendar holiday ID (handling exceptions like US -> `usa`, GB -> `uk`, ZA -> `sa`).
3. **Automated Holiday List Management**: Creates a `Holiday List` named `Holidays - {Company} - {Year}` if one does not exist, updates it if it does, and assigns it as the default Holiday List for the Company.
4. **Automated Scheduler**: Runs automatically on the 1st of January every year to generate holiday lists for the new year.
5. **Manual Desk Action**: Adds a button to the `Company` DocType form to trigger manual synchronizations for any custom year.
6. **Multi-lingual Support**: Resolves calendar language settings through `Google Holiday Sync Settings` (defaults to English, falling back gracefully if necessary).

## Installation

Run the following commands on your bench directory:

```bash
bench get-app https://github.com/your-username/holiday_sync.git
bench --site your-site-name install-app holiday_sync
```

## Folder Structure

```text
holiday_sync/
├── pyproject.toml
├── requirements.txt
├── MANIFEST.in
├── README.md
└── holiday_sync/
    ├── __init__.py
    ├── hooks.py
    ├── patches.txt
    ├── modules.txt
    ├── public/
    │   └── js/
    │       └── company.js
    └── holiday_sync/
        ├── __init__.py
        ├── utils.py
        └── doctype/
            ├── __init__.py
            └── google_holiday_sync_settings/
                ├── google_holiday_sync_settings.json
                ├── google_holiday_sync_settings.py
                └── google_holiday_sync_settings.js
```

## License

MIT
