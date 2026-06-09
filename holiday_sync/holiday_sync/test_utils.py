import unittest
import frappe
from holiday_sync.holiday_sync.utils import get_calendar_id, parse_ics_holidays

class TestHolidaySync(unittest.TestCase):
    def test_calendar_id_construction(self):
        # Test standard mapping
        self.assertEqual(
            get_calendar_id("do"), 
            "en.do.official#holiday@group.v.calendar.google.com"
        )
        self.assertEqual(
            get_calendar_id("cl"), 
            "en.cl.official#holiday@group.v.calendar.google.com"
        )
        
        # Test special case mapping
        self.assertEqual(
            get_calendar_id("us"), 
            "en.usa.official#holiday@group.v.calendar.google.com"
        )
        self.assertEqual(
            get_calendar_id("gb"), 
            "en.uk.official#holiday@group.v.calendar.google.com"
        )
        self.assertEqual(
            get_calendar_id("za"), 
            "en.sa.official#holiday@group.v.calendar.google.com"
        )
        
        # Test custom language mapping
        self.assertEqual(
            get_calendar_id("es", lang="es"), 
            "es.spain.official#holiday@group.v.calendar.google.com"
        )

    def test_parse_ics_holidays(self):
        # Sample mini-ICS content to test folding and parsing logic
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Google Inc//Google Calendar//EN
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260101
DTEND;VALUE=DATE:20260102
SUMMARY:New Year's Day
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20261225
DTEND;VALUE=DATE:20261226
SUMMARY:Christmas 
 Day
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20270101
DTEND;VALUE=DATE:20270102
SUMMARY:New Year's Day
END:VEVENT
END:VCALENDAR"""

        # Parse holidays only for 2026
        holidays_2026 = parse_ics_holidays(ics_content, target_year=2026)
        
        # Assertions
        self.assertEqual(len(holidays_2026), 2)
        self.assertEqual(holidays_2026[0]["date"], "2026-01-01")
        self.assertEqual(holidays_2026[0]["summary"], "New Year's Day")
        
        # Check that folded line was correctly unfolded ("Christmas Day")
        self.assertEqual(holidays_2026[1]["date"], "2026-12-25")
        self.assertEqual(holidays_2026[1]["summary"], "Christmas Day")
        
        # Check that 2027 event was ignored when filtering by 2026
        self.assertTrue(all(h["date"].startswith("2026") for h in holidays_2026))

        # Parse holidays for 2027
        holidays_2027 = parse_ics_holidays(ics_content, target_year=2027)
        self.assertEqual(len(holidays_2027), 1)
        self.assertEqual(holidays_2027[0]["date"], "2027-01-01")
