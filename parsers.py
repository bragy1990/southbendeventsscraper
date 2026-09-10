"""
Date and time parsing functions for the South Bend Events Scraper.
"""

import datetime
import re
from typing import List, Optional, Set, Tuple

try:
    from .config import MONTH_NAME_TO_INT, WEEKDAY_NAME_TO_INT
except ImportError:
    from config import MONTH_NAME_TO_INT, WEEKDAY_NAME_TO_INT

# ---------------------------------------------------------------------------
# Module-level Pre-compiled Regular Expressions (O(1) pattern matching)
# ---------------------------------------------------------------------------
RE_DASHES = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2015\-–—]")
RE_NBSP = re.compile(r"[\u00a0\xa0]")
RE_SPACES = re.compile(r"\s+")

_TIME_MARKER = r"(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm)|noon|midnight)"
_ANY_TIME = r"(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?|noon|midnight)"

RE_STRIP_TIME_RANGE_1 = re.compile(_TIME_MARKER + r"\s*-\s*" + _ANY_TIME, re.IGNORECASE)
RE_STRIP_TIME_RANGE_2 = re.compile(_ANY_TIME + r"\s*-\s*" + _TIME_MARKER, re.IGNORECASE)
RE_STANDALONE_TIME = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b|\b(?:noon|midnight)\b|\b\d{1,2}:\d{2}\b", re.IGNORECASE)

RE_PARSE_TIME_STRING = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", re.IGNORECASE)
RE_PARSE_TIME_RANGE_1 = re.compile(r"(" + _TIME_MARKER + r")\s*-\s*(" + _ANY_TIME + r")", re.IGNORECASE)
RE_PARSE_TIME_RANGE_2 = re.compile(r"(" + _ANY_TIME + r")\s*-\s*(" + _TIME_MARKER + r")", re.IGNORECASE)
RE_STANDALONE_START_TIME = re.compile(r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)|noon|midnight)", re.IGNORECASE)
RE_AM_PM = re.compile(r"am|pm", re.IGNORECASE)
RE_HOUR_PREFIX = re.compile(r"^(\d{1,2})")

_DAY_REGEX = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)"
RE_WEEKDAY_RANGE = re.compile(r"\b" + _DAY_REGEX + r"\s*-\s*" + _DAY_REGEX + r"\b", re.IGNORECASE)

RE_YEAR = re.compile(r"\b(202\d|203\d)\b")
_MONTHS_REGEX = (
    r"(january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
)

RE_MONTH_DAY = re.compile(r"\b" + _MONTHS_REGEX + r"\b\.?\s*(\d{1,2})(?:st|nd|rd|th)?\b", re.IGNORECASE)
RE_DAY_MONTH = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*" + _MONTHS_REGEX + r"\b", re.IGNORECASE)
RE_SAME_MONTH_RANGE = re.compile(
    r"\b" + _MONTHS_REGEX + r"\b\.?\s*(\d{1,2})(?:st|nd|rd|th)?\s*-\s*(\d{1,2})(?:st|nd|rd|th)?(?:,\s*(202\d|203\d))?",
    re.IGNORECASE,
)
RE_TO_THROUGH = re.compile(r"\b(to|through)\b", re.IGNORECASE)


def clean_text(text: Optional[str]) -> str:
    """Normalize whitespace and standardize dash/hyphen characters."""
    if not text:
        return ""
    text = RE_DASHES.sub(" - ", text)
    text = RE_NBSP.sub(" ", text)
    return RE_SPACES.sub(" ", text).strip()


def strip_time_expressions(text: str) -> str:
    """Remove time expressions (e.g., '7:00 PM – 9:00 PM', '12:00 PM', 'Noon - 5:00 PM') from date strings."""
    text = clean_text(text)
    text = RE_STRIP_TIME_RANGE_1.sub("", text)
    text = RE_STRIP_TIME_RANGE_2.sub("", text)
    text = RE_STANDALONE_TIME.sub("", text)
    return clean_text(text)


def parse_time_string(time_str: str) -> Optional[datetime.time]:
    """Parse time representations such as '7:00 PM', '12:30 AM', 'Noon', 'Midnight', '7:05 PM', '5 PM'."""
    time_str = time_str.strip().lower()
    if time_str == "noon":
        return datetime.time(12, 0)
    if time_str == "midnight":
        return datetime.time(0, 0)

    m = RE_PARSE_TIME_STRING.match(time_str)
    if not m:
        return None
    hours = int(m.group(1))
    minutes = int(m.group(2)) if m.group(2) else 0
    meridiem = m.group(3)

    if meridiem == "pm" and hours < 12:
        hours += 12
    elif meridiem == "am" and hours == 12:
        hours = 0
    elif not meridiem and hours > 23:
        return None

    try:
        return datetime.time(hours, minutes)
    except ValueError:
        return None


def parse_time_range(text: str) -> Tuple[Optional[datetime.time], Optional[datetime.time]]:
    """Parse time expressions into start and end times (e.g. '7:00 PM - 9:00 PM', '10:00 - 2:00 PM', 'Noon - 5:00 PM')."""
    text_clean = clean_text(text)

    # 1. Range match: require at least one side to have an explicit time indicator (colon, am/pm, noon, midnight)
    range_match = RE_PARSE_TIME_RANGE_1.search(text_clean)
    if not range_match:
        range_match = RE_PARSE_TIME_RANGE_2.search(text_clean)

    if range_match:
        t1_str, t2_str = range_match.group(1).strip(), range_match.group(2).strip()
        t2 = parse_time_string(t2_str)

        if (
            not RE_AM_PM.search(t1_str)
            and RE_AM_PM.search(t2_str)
            and t1_str.lower() not in ("noon", "midnight")
        ):
            meridiem = RE_AM_PM.search(t2_str).group(0).lower()
            t1_hour_match = RE_HOUR_PREFIX.match(t1_str)
            t1_hour = int(t1_hour_match.group(1)) if t1_hour_match else 0

            # If t2 is PM and t1_hour > t2's 12-hour value (and t1_hour != 12), t1 is AM
            # Example: "10:00 - 2:00 PM" -> 10:00 AM to 2:00 PM
            if meridiem == "pm" and t2 and t1_hour > (t2.hour % 12) and t1_hour != 12:
                t1 = parse_time_string(f"{t1_str} am")
            else:
                t1 = parse_time_string(f"{t1_str} {meridiem}")
        else:
            t1 = parse_time_string(t1_str)

        return t1, t2

    # 2. Standalone start time match: "7:05 PM", "7 PM", "Noon"
    single_match = RE_STANDALONE_START_TIME.search(text_clean)
    if single_match:
        t = parse_time_string(single_match.group(1))
        return t, None

    return None, None


def parse_weekday_pattern(text: str) -> Optional[Set[int]]:
    """Detect recurring weekday patterns (e.g. 'Wednesday - Sunday', 'Fridays', 'Every Saturday', 'Mon-Fri')."""
    text = clean_text(text).lower()

    # Check for weekday range: e.g. "Wednesday - Sunday"
    range_match = RE_WEEKDAY_RANGE.search(text)
    if range_match:
        start_day = WEEKDAY_NAME_TO_INT[range_match.group(1).lower()]
        end_day = WEEKDAY_NAME_TO_INT[range_match.group(2).lower()]
        if start_day <= end_day:
            return set(range(start_day, end_day + 1))
        else:
            return set(list(range(start_day, 7)) + list(range(0, end_day + 1)))

    # Check for individual or plural day names: "Fridays", "Friday", "Saturdays and Sundays"
    days = set()
    for name, day_num in WEEKDAY_NAME_TO_INT.items():
        if re.search(rf"\b{name}s?\b", text):
            days.add(day_num)

    return days if days else None


def resolve_year(month: int, day: int, base_date: Optional[datetime.date] = None) -> int:
    """Correctly resolve the year for upcoming events relative to base_date."""
    base_date = base_date or datetime.date.today()
    year = base_date.year
    safe_day = min(day, 28)
    try:
        candidate_date = datetime.date(year, month, safe_day)
        # If candidate date is more than 30 days in the past, roll over to next year
        if candidate_date < (base_date - datetime.timedelta(days=30)):
            year += 1
    except ValueError:
        if month < base_date.month:
            year += 1
    return year


def parse_date_segment(seg: str, base_date: Optional[datetime.date] = None) -> Optional[datetime.date]:
    """Parse a single date component like 'Aug 19', 'Aug 19th', 'Wednesday, August 19', 'August 21, 2026', 'December 11'."""
    base_date = base_date or datetime.date.today()
    seg = clean_text(seg)
    year_match = RE_YEAR.search(seg)
    explicit_year = int(year_match.group(1)) if year_match else None

    # Match Month + Day (e.g. "August 19", "August 19th", "Aug 1st")
    m = RE_MONTH_DAY.search(seg)
    if not m:
        # Match Day + Month (e.g. "19 August", "19th August", "1st Aug")
        m = RE_DAY_MONTH.search(seg)
        if m:
            day = int(m.group(1))
            month_str = m.group(2).lower()
        else:
            return None
    else:
        month_str = m.group(1).lower()
        day = int(m.group(2))

    month = MONTH_NAME_TO_INT.get(month_str)
    if not month:
        return None

    year = explicit_year if explicit_year else resolve_year(month, day, base_date)
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def parse_date_range_or_single(
    date_text: str,
    base_date: Optional[datetime.date] = None,
) -> List[Tuple[datetime.date, datetime.date]]:
    """Parse complex date strings: 'Aug 17 to Aug 23', 'Aug 17 - 23', 'Friday, August 21 to Friday, December 11', 'Aug 19'."""
    base_date = base_date or datetime.date.today()
    normalized = RE_TO_THROUGH.sub(" - ", date_text)
    normalized = clean_text(normalized)

    # 1. Format: "Month Day1 - Day2" (e.g. "Aug 17 - 23", "August 17th - 23rd, 2026")
    m_same_month = RE_SAME_MONTH_RANGE.search(normalized)
    if m_same_month:
        month_str = m_same_month.group(1).lower()
        day1 = int(m_same_month.group(2))
        day2 = int(m_same_month.group(3))
        explicit_year = int(m_same_month.group(4)) if m_same_month.group(4) else None
        month = MONTH_NAME_TO_INT[month_str]
        year = explicit_year if explicit_year else resolve_year(month, day1, base_date)
        try:
            d1 = datetime.date(year, month, day1)
            d2 = datetime.date(year, month, day2)
            return [(d1, d2)]
        except ValueError:
            pass

    # 2. Format: "DateSeg1 - DateSeg2" (e.g. "Aug 21 - Dec 11", "August 21 to December 18")
    if " - " in normalized:
        parts = normalized.split(" - ")
        if len(parts) >= 2:
            d1 = parse_date_segment(parts[0], base_date)
            d2 = parse_date_segment(parts[-1], base_date)
            if d1 and d2:
                # Year Rollover: If d2 precedes d1, roll d2 to next year
                if d2 < d1 and d2.year == d1.year:
                    try:
                        d2 = datetime.date(d1.year + 1, d2.month, d2.day)
                    except ValueError:
                        d2 = datetime.date(d1.year + 1, d2.month, min(d2.day, 28))
                return [(d1, d2)]
            elif d1 and not d2:
                return [(d1, d1)]

    # 3. Single Date
    d = parse_date_segment(normalized, base_date)
    if d:
        return [(d, d)]

    return []