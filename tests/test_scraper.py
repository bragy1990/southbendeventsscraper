"""
Unit tests for the South Bend Events Scraper modules.
"""

import datetime
import unittest

from config import MONTH_NAME_TO_INT, TIMEZONE_ID, WEEKDAY_NAME_TO_INT
from formatter import build_ics_calendar, fold_line, generate_uid, ical_escape
from parsers import (
    clean_text,
    parse_date_range_or_single,
    parse_date_segment,
    parse_time_range,
    parse_time_string,
    parse_weekday_pattern,
    resolve_year,
    strip_time_expressions,
)
from scraper import detect_event_diffs, dispatch_webhook
from utils import expand_event_schedules, format_location_address


class TestParsers(unittest.TestCase):
    def setUp(self):
        self.base_date = datetime.date(2026, 8, 18)

    def test_clean_text(self):
        self.assertEqual(clean_text("Event – Name — Special"), "Event - Name - Special")
        self.assertEqual(clean_text("Hello\u00a0World   123"), "Hello World 123")
        self.assertEqual(clean_text(""), "")
        self.assertEqual(clean_text(None), "")

    def test_parse_time_string(self):
        self.assertEqual(parse_time_string("Noon"), datetime.time(12, 0))
        self.assertEqual(parse_time_string("midnight"), datetime.time(0, 0))
        self.assertEqual(parse_time_string("7:00 PM"), datetime.time(19, 0))
        self.assertEqual(parse_time_string("7:05 pm"), datetime.time(19, 5))
        self.assertEqual(parse_time_string("12:30 AM"), datetime.time(0, 30))
        self.assertEqual(parse_time_string("12:00 PM"), datetime.time(12, 0))
        self.assertEqual(parse_time_string("5 PM"), datetime.time(17, 0))
        self.assertIsNone(parse_time_string("invalid"))

    def test_parse_time_range_ampm_inference(self):
        # Explicit AM and PM
        t1, t2 = parse_time_range("10:00 AM - 2:00 PM")
        self.assertEqual(t1, datetime.time(10, 0))
        self.assertEqual(t2, datetime.time(14, 0))

        # Inferred AM when start hour > end hour (e.g. 10:00 to 2:00 PM -> 10 AM to 2 PM)
        t1, t2 = parse_time_range("10:00 - 2:00 PM")
        self.assertEqual(t1, datetime.time(10, 0))
        self.assertEqual(t2, datetime.time(14, 0))

        # Same meridiem when start hour <= end hour (e.g. 1:00 to 3:00 PM -> 1 PM to 3 PM)
        t1, t2 = parse_time_range("1:00 - 3:00 PM")
        self.assertEqual(t1, datetime.time(13, 0))
        self.assertEqual(t2, datetime.time(15, 0))

        # Noon start
        t1, t2 = parse_time_range("Noon - 5:00 PM")
        self.assertEqual(t1, datetime.time(12, 0))
        self.assertEqual(t2, datetime.time(17, 0))

        # Standalone single time
        t1, t2 = parse_time_range("7:30 PM")
        self.assertEqual(t1, datetime.time(19, 30))
        self.assertIsNone(t2)

    def test_parse_weekday_pattern(self):
        # Ranges
        self.assertEqual(parse_weekday_pattern("Wednesday - Sunday"), {2, 3, 4, 5, 6})
        self.assertEqual(parse_weekday_pattern("Mon-Fri"), {0, 1, 2, 3, 4})
        self.assertEqual(parse_weekday_pattern("Friday - Saturday"), {4, 5})

        # Plural and lists
        self.assertEqual(parse_weekday_pattern("Fridays"), {4})
        self.assertEqual(parse_weekday_pattern("Saturdays and Sundays"), {5, 6})
        self.assertEqual(parse_weekday_pattern("Every Tuesday"), {1})
        self.assertIsNone(parse_weekday_pattern("Daily event with no weekdays mentioned"))

    def test_parse_date_segment_with_ordinals(self):
        # Standard format
        self.assertEqual(parse_date_segment("August 19", self.base_date), datetime.date(2026, 8, 19))
        self.assertEqual(parse_date_segment("Aug 21, 2026", self.base_date), datetime.date(2026, 8, 21))

        # Ordinal suffixes (1st, 2nd, 3rd, 19th)
        self.assertEqual(parse_date_segment("August 19th", self.base_date), datetime.date(2026, 8, 19))
        self.assertEqual(parse_date_segment("Aug 1st", self.base_date), datetime.date(2026, 8, 1))
        self.assertEqual(parse_date_segment("September 2nd, 2026", self.base_date), datetime.date(2026, 9, 2))
        self.assertEqual(parse_date_segment("October 3rd", self.base_date), datetime.date(2026, 10, 3))

        # Day Month format
        self.assertEqual(parse_date_segment("19th August 2026", self.base_date), datetime.date(2026, 8, 19))

    def test_resolve_year_and_rollover(self):
        # Same month or upcoming month
        self.assertEqual(resolve_year(8, 20, self.base_date), 2026)
        self.assertEqual(resolve_year(12, 15, self.base_date), 2026)

        # Distant past month rolls over to next year for upcoming event scraping
        self.assertEqual(resolve_year(1, 15, self.base_date), 2027)

    def test_parse_date_range_or_single(self):
        # Same month range
        res = parse_date_range_or_single("Aug 17 - 23", self.base_date)
        self.assertEqual(res, [(datetime.date(2026, 8, 17), datetime.date(2026, 8, 23))])

        # Cross month range
        res = parse_date_range_or_single("August 21 to December 11", self.base_date)
        self.assertEqual(res, [(datetime.date(2026, 8, 21), datetime.date(2026, 12, 11))])

        # Cross year range
        res = parse_date_range_or_single("December 20 - January 5", self.base_date)
        self.assertEqual(res, [(datetime.date(2026, 12, 20), datetime.date(2027, 1, 5))])

        # Single date with time string
        res = parse_date_range_or_single("August 19, 2026 | 7:00 PM", self.base_date)
        self.assertEqual(res, [(datetime.date(2026, 8, 19), datetime.date(2026, 8, 19))])


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.base_date = datetime.date(2026, 8, 18)

    def test_format_location_address(self):
        loc = format_location_address("Morris Performing Arts Center", "211 N Michigan St", "South Bend, IN 46601")
        self.assertEqual(loc, "Morris Performing Arts Center | 211 N Michigan St | South Bend, IN 46601")

        loc_partial = format_location_address("Century Center", "", "South Bend, IN")
        self.assertEqual(loc_partial, "Century Center | South Bend, IN")
        self.assertEqual(format_location_address("", "", ""), "")

    def test_expand_event_schedules_single_day(self):
        instances = expand_event_schedules(
            raw_date_str="August 19, 2026",
            raw_time_str="7:00 PM - 9:00 PM",
            raw_recur_str="",
            upcoming_dates=[],
            overview_text="",
            base_date=self.base_date,
        )
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]["date"], "2026-08-19")
        self.assertEqual(instances[0]["start_time"], "19:00:00")
        self.assertEqual(instances[0]["end_time"], "21:00:00")
        self.assertFalse(instances[0]["all_day"])

    def test_expand_event_schedules_recurring_filter(self):
        # Aug 17 to Aug 23, 2026: Mon(17), Tue(18), Wed(19), Thu(20), Fri(21), Sat(22), Sun(23)
        # Recurrence: "Fridays and Saturdays" -> Only Aug 21 and Aug 22 should be generated
        instances = expand_event_schedules(
            raw_date_str="Aug 17 - 23, 2026",
            raw_time_str="8:00 PM",
            raw_recur_str="Fridays and Saturdays",
            upcoming_dates=[],
            overview_text="",
            base_date=self.base_date,
        )
        self.assertEqual(len(instances), 2)
        dates = [inst["date"] for inst in instances]
        self.assertEqual(dates, ["2026-08-21", "2026-08-22"])


class TestFormatter(unittest.TestCase):
    def test_ical_escape(self):
        raw = "Line 1, with commas; semicolons & \\ backslashes\r\nLine 2"
        escaped = ical_escape(raw)
        self.assertIn(r"\,", escaped)
        self.assertIn(r"\;", escaped)
        self.assertIn(r"\\", escaped)
        self.assertIn(r"\nLine 2", escaped)

    def test_fold_line(self):
        short_line = "SUMMARY:Short Event Title"
        self.assertEqual(fold_line(short_line), short_line)

        long_line = "DESCRIPTION:" + "A" * 150
        folded = fold_line(long_line)
        lines = folded.split("\r\n")
        self.assertTrue(len(lines) > 1)
        for i, l in enumerate(lines):
            self.assertTrue(len(l.encode("utf-8")) <= 75)
            if i > 0:
                self.assertTrue(l.startswith(" "))

    def test_generate_uid(self):
        uid1 = generate_uid("https://www.visitsouthbend.com/events/1/", "2026-08-19", "19:00:00")
        uid2 = generate_uid("https://www.visitsouthbend.com/events/1/", "2026-08-19", "19:00:00")
        uid3 = generate_uid("https://www.visitsouthbend.com/events/2/", "2026-08-19", "19:00:00")

        self.assertEqual(uid1, uid2)
        self.assertNotEqual(uid1, uid3)
        self.assertTrue(uid1.endswith("@visitsouthbend.com"))

    def test_build_ics_calendar(self):
        events = [
            {
                "title": "South Bend Jazz Festival",
                "url": "https://www.visitsouthbend.com/events/jazz-fest/",
                "location": "Howard Park | 219 S St Louis Blvd | South Bend, IN 46617",
                "description": "Annual outdoor jazz festival featuring local musicians.",
                "schedule_instances": [
                    {
                        "date": "2026-08-22",
                        "start_time": "14:00:00",
                        "end_time": "22:00:00",
                        "all_day": False,
                    },
                    {
                        "date": "2026-08-23",
                        "start_time": None,
                        "end_time": None,
                        "all_day": True,
                    },
                ],
            }
        ]

        ics = build_ics_calendar(events)
        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("VERSION:2.0", ics)
        self.assertIn("BEGIN:VTIMEZONE", ics)
        self.assertIn(f"TZID:{TIMEZONE_ID}", ics)
        self.assertIn("SUMMARY:South Bend Jazz Festival", ics)
        self.assertIn(f"DTSTART;TZID={TIMEZONE_ID}:20260822T140000", ics)
        self.assertIn(f"DTEND;TZID={TIMEZONE_ID}:20260822T220000", ics)
        self.assertIn("DTSTART;VALUE=DATE:20260823", ics)
        self.assertIn("DTEND;VALUE=DATE:20260824", ics)  # +1 day exclusive
        self.assertIn("END:VCALENDAR", ics)


class TestScraperDiffAndWebhook(unittest.TestCase):
    def test_detect_event_diffs(self):
        old_events = [
            {"title": "Old Event 1", "url": "https://www.visitsouthbend.com/events/old-1/"},
            {"title": "Continuing Event", "url": "https://www.visitsouthbend.com/events/continuing/"},
        ]
        new_events = [
            {"title": "Continuing Event", "url": "https://www.visitsouthbend.com/events/continuing/"},
            {"title": "New Event 2", "url": "https://www.visitsouthbend.com/events/new-2/"},
        ]

        diff = detect_event_diffs(old_events, new_events)
        self.assertEqual(len(diff["added"]), 1)
        self.assertEqual(diff["added"][0]["title"], "New Event 2")
        self.assertEqual(len(diff["removed"]), 1)
        self.assertEqual(diff["removed"][0]["title"], "Old Event 1")

    def test_dispatch_webhook_empty_url(self):
        # Empty webhook url should return False without raising errors
        res = dispatch_webhook("", {"added": [], "removed": []}, 10, 20)
        self.assertFalse(res)


if __name__ == "__main__":
    unittest.main()
