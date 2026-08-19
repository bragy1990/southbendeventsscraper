"""
Utility functions for the South Bend Events Scraper.
"""

import datetime
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from .parsers import (
        clean_text,
        parse_date_range_or_single,
        parse_time_range,
        parse_weekday_pattern,
        strip_time_expressions,
    )
except ImportError:
    from parsers import (
        clean_text,
        parse_date_range_or_single,
        parse_time_range,
        parse_weekday_pattern,
        strip_time_expressions,
    )

logger = logging.getLogger("SouthBendScraper")


def format_location_address(venue: str, address: str, city_state_zip: str) -> str:
    """Format structured venue and address patterns into 'Venue | Address | City, State ZIP'."""
    parts = []
    if venue:
        parts.append(venue)
    if address:
        parts.append(address)
    if city_state_zip:
        parts.append(city_state_zip)

    return " | ".join(parts) if parts else ""


def expand_event_schedules(
    raw_date_str: str,
    raw_time_str: str,
    raw_recur_str: str,
    upcoming_dates: List[str],
    overview_text: str,
    base_date: datetime.date,
) -> List[Dict[str, Any]]:
    """Intelligently parse dates, times, weekday recurrences, and generate individual schedule instances."""
    # 1. Parse time components
    start_time, end_time = parse_time_range(raw_time_str)
    if not start_time:
        start_time, end_time = parse_time_range(raw_date_str)
    if not start_time and raw_recur_str:
        start_time, end_time = parse_time_range(raw_recur_str)

    # 2. Detect weekday recurrence pattern
    weekday_pattern = parse_weekday_pattern(raw_recur_str)
    if not weekday_pattern and raw_date_str:
        weekday_pattern = parse_weekday_pattern(raw_date_str)
    if not weekday_pattern and overview_text:
        if re.search(r"\bevery\s+(friday|saturday|sunday|monday|tuesday|wednesday|thursday)\b", overview_text, re.IGNORECASE):
            weekday_pattern = parse_weekday_pattern(overview_text)

    # 3. Collect candidate date ranges
    date_ranges: List[Tuple[datetime.date, datetime.date, Optional[Set[int]]]] = []

    # Prioritize UPCOMING DATES list if available
    if upcoming_dates:
        for u_date in upcoming_dates:
            u_date_clean = strip_time_expressions(u_date)
            parsed_ranges = parse_date_range_or_single(u_date_clean, base_date)
            item_weekdays = parse_weekday_pattern(u_date) or weekday_pattern
            for d1, d2 in parsed_ranges:
                date_ranges.append((d1, d2, item_weekdays))
    else:
        raw_date_clean = strip_time_expressions(raw_date_str)
        parsed_ranges = parse_date_range_or_single(raw_date_clean, base_date)
        for d1, d2 in parsed_ranges:
            date_ranges.append((d1, d2, weekday_pattern))

    # 4. Expand ranges into concrete event dates
    expanded_instances: List[Dict[str, Any]] = []
    seen_keys: Set[Tuple[str, str, str]] = set()

    for d1, d2, pattern in date_ranges:
        day_count = (d2 - d1).days + 1
        if day_count > 366:
            day_count = 366

        for i in range(day_count):
            day = d1 + datetime.timedelta(days=i)
            if pattern is not None and day.weekday() not in pattern:
                continue

            key = (day.isoformat(), str(start_time), str(end_time))
            if key not in seen_keys:
                seen_keys.add(key)
                expanded_instances.append({
                    "date": day.isoformat(),
                    "start_time": start_time.strftime("%H:%M:%S") if start_time else None,
                    "end_time": end_time.strftime("%H:%M:%S") if end_time else None,
                    "all_day": start_time is None,
                })

    return expanded_instances