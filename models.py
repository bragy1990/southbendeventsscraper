"""
Data models and typed schemas for South Bend Events Scraper.
"""

from typing import List, Optional, TypedDict


class ScheduleInstance(TypedDict):
    """Represents a single concrete occurrence of an event."""
    date: str
    start_time: Optional[str]
    end_time: Optional[str]
    all_day: bool


class EventData(TypedDict):
    """Represents full structured metadata for a scraped event listing."""
    title: str
    url: str
    location: str
    description: str
    raw_date: str
    raw_recurrence: str
    upcoming_dates: List[str]
    schedule_instances: List[ScheduleInstance]


class DiffResult(TypedDict):
    """Represents the difference between previous and current event scrapes."""
    added: List[EventData]
    removed: List[EventData]
