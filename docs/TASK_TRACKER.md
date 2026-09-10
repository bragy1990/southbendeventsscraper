# South Bend Events Scraper V2: Task Tracker & Design Goal Ledger

**Document Version:** 1.1.0  
**Last Updated:** September 9, 2026  
**Tracking System:** Granular Design Tasks with Change & Supersession Logs  

This document tracks all actionable tasks derived from [docs/DESIGN_DOCUMENT.md](DESIGN_DOCUMENT.md). When working on any task, future AI agents and developers must:
1. Update task checkboxes (`[ ]` Pending -> `[/]` In Progress -> `[x]` Completed -> `[-]` Superseded).
2. Record any modifications or supersessions in the **Task History & Change Log** under each task.
3. Cross-reference completed tasks in [docs/IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md).

---

## Task Progress Summary

| Workstream | Total Tasks | Completed | In Progress | Pending | Superseded |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **WS-1: Visit South Bend Ingestion Pipeline** | 3 | 3 | 0 | 0 | 0 |
| **WS-2: iCalendar & Distribution Engine** | 3 | 3 | 0 | 0 | 0 |
| **WS-3: Code Quality & Architecture Modernization** | 3 | 3 | 0 | 0 | 0 |
| **TOTAL** | **9** | **9** | **0** | **0** | **0** |

---

## Detailed Task Catalog

### WS-1: Visit South Bend Ingestion Pipeline

#### `TASK-1.1` Asynchronous event listing scraper
* **Status:** `[x] Completed`
* **Target Acceptance Criteria:**
  * Playwright async crawling, auto-scrolling, URL deduplication, and concurrent detail scraping.
* **Task History & Change Log:**
  * *2026-09-02 (Baseline): Task registered.*
  * *2026-09-09 (Antigravity): Implemented in `scraper.py` with semaphore-controlled concurrency.*

#### `TASK-1.2` Event categorization and metadata enrichment
* **Status:** `[x] Completed`
* **Target Acceptance Criteria:**
  * Extraction of structured title, date preheadings, recurrence strings, venue, and descriptions.
* **Task History & Change Log:**
  * *2026-09-02 (Baseline): Task registered.*
  * *2026-09-09 (Antigravity): Scrapes rich metadata and structures it into `EventData` TypedDict.*

#### `TASK-1.3` Venue geocoding and recurrence expansion
* **Status:** `[x] Completed`
* **Target Acceptance Criteria:**
  * Intelligent multi-day date range expansion, AM/PM inference, weekday filtering, and location formatting.
* **Task History & Change Log:**
  * *2026-09-02 (Baseline): Task registered.*
  * *2026-09-09 (Antigravity): Fully functional in `parsers.py` and `utils.py`.*

---

### WS-2: iCalendar & Distribution Engine

#### `TASK-2.1` Static .ics calendar export and delta updates
* **Status:** `[x] Completed`
* **Target Acceptance Criteria:**
  * RFC 5545 `.ics` file generation with line folding (75 octets), deterministic UIDs, and diff detection.
* **Task History & Change Log:**
  * *2026-09-02 (Baseline): Task registered.*
  * *2026-09-09 (Antigravity): Implemented in `formatter.py` and `scraper.py`.*

#### `TASK-2.2` Automated deployment and RSS/web distribution
* **Status:** `[x] Completed`
* **Target Acceptance Criteria:**
  * GitHub Actions workflow with scheduled cron, webhook triggers, live `webcal://` link, and outbound Discord/Slack notifications.
* **Task History & Change Log:**
  * *2026-09-02 (Baseline): Task registered.*
  * *2026-09-09 (Antigravity): Configured `.github/workflows/update_calendar.yml` and async-safe webhook dispatch.*

#### `TASK-2.3` Validation and regression test suite
* **Status:** `[x] Completed`
* **Target Acceptance Criteria:**
  * Automated unit tests covering all parsers, formatting, utils, diffing, and configuration.
* **Task History & Change Log:**
  * *2026-09-02 (Baseline): Task registered.*
  * *2026-09-09 (Antigravity): 18 unit tests in `tests/test_scraper.py` (100% passing).*

---

### WS-3: Code Quality & Architecture Modernization

#### `TASK-3.1` Strongly-Typed Data Contracts
* **Status:** `[x] Completed`
* **Target Acceptance Criteria:**
  * Defined `ScheduleInstance`, `EventData`, and `DiffResult` in `models.py` with type validation.
* **Task History & Change Log:**
  * *2026-09-09 (Antigravity): Created `models.py` and linked across all modules.*

#### `TASK-3.2` Pre-compiled Regular Expressions
* **Status:** `[x] Completed`
* **Target Acceptance Criteria:**
  * Extracted module-level pre-compiled regex objects in `parsers.py` and `utils.py` for $O(1)$ performance.
* **Task History & Change Log:**
  * *2026-09-09 (Antigravity): Refactored `parsers.py` with compiled regex patterns.*

#### `TASK-3.3` Cross-Platform Pathlib & Non-Blocking Async Webhooks
* **Status:** `[x] Completed`
* **Target Acceptance Criteria:**
  * Migrated to `pathlib.Path` and wrapped outbound webhooks in `asyncio.to_thread`.
* **Task History & Change Log:**
  * *2026-09-09 (Antigravity): Implemented in `config.py` and `scraper.py` along with CLI argument support.*
