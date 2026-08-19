"""
Main scraper implementation for the South Bend Events Scraper.
"""

import asyncio
import datetime
import json
import logging
import os
from typing import Any, Dict, List, Optional, Set
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse

from playwright.async_api import BrowserContext, Page, async_playwright

try:
    from .config import (
        BASE_URL,
        BROWSER_CONFIG,
        EVENTS_URL,
        EXCLUDED_PATHS,
        MAX_CONCURRENT_REQUESTS,
        OUTPUT_ICS_PATH,
        OUTPUT_JSON_PATH,
        PAGE_LOAD_TIMEOUT_MS,
        SCROLL_DELAY_MS,
        SCROLL_ITERATIONS,
        WEBHOOK_URL,
    )
    from .formatter import build_ics_calendar
    from .utils import expand_event_schedules, format_location_address
except ImportError:
    from config import (
        BASE_URL,
        BROWSER_CONFIG,
        EVENTS_URL,
        EXCLUDED_PATHS,
        MAX_CONCURRENT_REQUESTS,
        OUTPUT_ICS_PATH,
        OUTPUT_JSON_PATH,
        PAGE_LOAD_TIMEOUT_MS,
        SCROLL_DELAY_MS,
        SCROLL_ITERATIONS,
        WEBHOOK_URL,
    )
    from formatter import build_ics_calendar
    from utils import expand_event_schedules, format_location_address

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SouthBendScraper")


def detect_event_diffs(old_events: List[Dict[str, Any]], new_events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Compare previous event dataset against newly scraped dataset to identify added and removed events."""
    old_by_url = {e.get("url"): e for e in old_events if e.get("url")}
    new_by_url = {e.get("url"): e for e in new_events if e.get("url")}

    added = [e for url, e in new_by_url.items() if url not in old_by_url]
    removed = [e for url, e in old_by_url.items() if url not in new_by_url]

    return {
        "added": added,
        "removed": removed,
    }


def dispatch_webhook(
    webhook_url: str,
    diff: Dict[str, List[Dict[str, Any]]],
    total_events: int,
    total_instances: int,
) -> bool:
    """Send an outbound notification payload to a Discord, Slack, or generic webhook endpoint."""
    if not webhook_url:
        return False

    added_events = diff.get("added", [])
    removed_events = diff.get("removed", [])

    # Format notification content
    summary_lines = [
        f"📅 **South Bend Events Calendar Updated**",
        f"• Total Active Events: **{total_events}** ({total_instances} calendar entries)",
    ]

    if added_events:
        summary_lines.append(f"\n✨ **Newly Discovered Events ({len(added_events)}):**")
        for e in added_events[:5]:
            title = e.get("title", "Event")
            url = e.get("url", "")
            summary_lines.append(f"- [{title}]({url})" if url else f"- {title}")
        if len(added_events) > 5:
            summary_lines.append(f"_...and {len(added_events) - 5} more_")

    if removed_events:
        summary_lines.append(f"\n🗑️ **Removed Events ({len(removed_events)}):**")
        for e in removed_events[:3]:
            summary_lines.append(f"- {e.get('title', 'Event')}")

    message_text = "\n".join(summary_lines)

    # Compatible payload for Discord & Slack & generic JSON webhooks
    payload = {
        "content": message_text,
        "text": message_text,
        "total_events": total_events,
        "total_instances": total_instances,
        "added_count": len(added_events),
        "removed_count": len(removed_events),
    }

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "SouthBendScraper/2.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            logger.info(f"Dispatched webhook notification (HTTP status {response.status}).")
            return True
    except Exception as e:
        logger.warning(f"Failed to dispatch webhook notification: {e}")
        return False


async def extract_event_detail(context: BrowserContext, event_url: str, base_date: datetime.date) -> Optional[Dict[str, Any]]:
    """Visit an individual event detail page and extract structured metadata."""
    page: Optional[Page] = None
    try:
        page = await context.new_page()
        logger.info(f"Scraping detail page: {event_url}")
        await page.goto(event_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
        await page.wait_for_timeout(1500)

        # Extract DOM fields via browser context
        extracted = await page.evaluate(
            """() => {
            // 1. Title extraction
            let title = document.querySelector('h1')?.innerText?.trim() || '';
            if (!title || title.toLowerCase() === 'navigation') {
                title = document.querySelector('.detail__header, .card__heading')?.innerText?.trim() || document.title;
            }

            // 2. Date and Time Preheading
            const datePreheading = document.querySelector('.detail__date-preheading, [class*="date-preheading"]')?.innerText?.trim() || '';

            // 3. Recurrence / Sub-schedule / Additional times (scoped to primary section)
            let recurText = document.querySelector('.card__date-recurs, .detail__primary-content .faux-subheading, .detail__primary .faux-subheading')?.innerText?.trim() || '';
            if (/^(e-newsletter|newsletter|map|admission|n\\/a|share|save|itinerary builder)$/i.test(recurText)) {
                recurText = '';
            }

            // 4. Structured Location / Venue / Address
            let venue = '';
            let street = '';
            let cityStateZip = '';
            let fullLocaleText = '';

            const localeEl = document.querySelector('.detail__locale, .detail__address, [class*="detail__address"]');
            if (localeEl) {
                fullLocaleText = localeEl.innerText.trim();
                const lines = fullLocaleText.split('\\n').map(l => l.trim()).filter(l => l.length > 0 && !l.startsWith('('));
                if (lines.length >= 3) {
                    venue = lines[0];
                    street = lines[1];
                    cityStateZip = lines[2];
                } else if (lines.length === 2) {
                    venue = lines[0];
                    cityStateZip = lines[1];
                } else if (lines.length === 1) {
                    venue = lines[0];
                }
            }

            // 5. Overview / Description
            let overview = '';
            const overviewEl = document.querySelector('.detail__overview, [class*="overview-content"]');
            if (overviewEl) {
                overview = overviewEl.innerText.trim();
            } else {
                const headings = Array.from(document.querySelectorAll('h2, h3, h4'));
                const overviewHeading = headings.find(h => h.innerText.trim().toUpperCase() === 'OVERVIEW');
                if (overviewHeading && overviewHeading.nextElementSibling) {
                    overview = overviewHeading.nextElementSibling.innerText.trim();
                } else {
                    const contentEl = document.querySelector('.detail__content, .detail__body, main');
                    if (contentEl) {
                        overview = contentEl.innerText.slice(0, 1000).trim();
                    }
                }
            }

            // 6. Upcoming Dates List
            const upcomingDates = [];
            const upcomingListItems = document.querySelectorAll('.detail__dates li, [class*="upcoming-dates"] li, .list--multi-column li');
            upcomingListItems.forEach(li => {
                const txt = li.innerText.trim();
                if (txt && !upcomingDates.includes(txt)) {
                    upcomingDates.push(txt);
                }
            });

            return {
                title,
                datePreheading,
                recurText,
                venue,
                street,
                cityStateZip,
                fullLocaleText,
                overview,
                upcomingDates
            };
        }"""
        )

        title = extracted.get("title", "").strip()
        if not title or title.lower() == "navigation":
            title = event_url.rstrip("/").split("/")[-1].replace("-", " ").title()

        venue = extracted.get("venue", "").strip()
        street = extracted.get("street", "").strip()
        city_state_zip = extracted.get("cityStateZip", "").strip()
        location = format_location_address(venue, street, city_state_zip)
        if not location and extracted.get("fullLocaleText"):
            location = " | ".join(
                [line.strip() for line in extracted["fullLocaleText"].split("\n") if line.strip() and not line.strip().startswith("(")]
            )

        date_preheading = extracted.get("datePreheading", "")
        recur_text = extracted.get("recurText", "")
        overview = extracted.get("overview", "")
        upcoming_dates = extracted.get("upcomingDates", [])

        # Parse schedule instances
        schedule_instances = expand_event_schedules(
            raw_date_str=date_preheading,
            raw_time_str=date_preheading,
            raw_recur_str=recur_text,
            upcoming_dates=upcoming_dates,
            overview_text=overview,
            base_date=base_date,
        )

        event_data = {
            "title": title,
            "url": event_url,
            "location": location,
            "description": overview,
            "raw_date": date_preheading,
            "raw_recurrence": recur_text,
            "upcoming_dates": upcoming_dates,
            "schedule_instances": schedule_instances,
        }

        return event_data

    except Exception as e:
        logger.error(f"Error scraping detail page {event_url}: {e}")
        return None
    finally:
        if page:
            await page.close()


async def scrape_event_urls(page: Page) -> List[str]:
    """Scroll dynamic listings page and discover unique event detail URLs."""
    logger.info(f"Navigating to {EVENTS_URL}...")
    await page.goto(EVENTS_URL, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
    await page.wait_for_timeout(3000)

    logger.info("Executing smooth scrolling to trigger dynamic/lazy-loaded cards...")
    discovered_urls: Set[str] = set()

    for scroll_idx in range(SCROLL_ITERATIONS):
        await page.evaluate("window.scrollBy(0, 800)")
        await page.wait_for_timeout(SCROLL_DELAY_MS)

        # Collect current links from DOM
        links = await page.evaluate(
            """() => {
            return Array.from(document.querySelectorAll('a[href]')).map(a => a.href);
        }"""
        )

        for href in links:
            parsed = urlparse(href)
            path = parsed.path.rstrip("/")
            if "/events/" in parsed.path:
                if (
                    path not in EXCLUDED_PATHS
                    and f"{path}/" not in EXCLUDED_PATHS
                    and not parsed.query.startswith("page=")
                    and not href.endswith("#")
                    and parsed.netloc.endswith("visitsouthbend.com")
                ):
                    clean_url = urljoin(BASE_URL, parsed.path)
                    if not clean_url.endswith("/"):
                        clean_url += "/"
                    if clean_url not in EXCLUDED_PATHS:
                        discovered_urls.add(clean_url)

    logger.info(f"Discovered {len(discovered_urls)} unique event detail links.")
    return sorted(list(discovered_urls))


async def main():
    """Main execution pipeline."""
    logger.info("Starting Visit South Bend Events Scraper...")
    base_date = datetime.date.today()

    # Load existing events for diff detection if available
    old_events: List[Dict[str, Any]] = []
    if os.path.exists(OUTPUT_JSON_PATH):
        try:
            with open(OUTPUT_JSON_PATH, "r", encoding="utf-8") as f:
                old_events = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load existing {OUTPUT_JSON_PATH} for diffing: {e}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent=BROWSER_CONFIG["user_agent"],
                viewport=BROWSER_CONFIG["viewport"],
            )
            main_page = await context.new_page()

            # Step 1: Collect event detail URLs
            event_urls = await scrape_event_urls(main_page)
            await main_page.close()

            # Step 2: Extract details for each event concurrently (controlled batch size)
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

            async def worker(url: str):
                async with semaphore:
                    return await extract_event_detail(context, url, base_date)

            tasks = [worker(url) for url in event_urls]
            extracted_results = await asyncio.gather(*tasks)
            events = [e for e in extracted_results if e is not None]
        finally:
            await browser.close()

    logger.info(f"Successfully scraped {len(events)} events.")

    # Step 3: Compute diffs against previous run
    diff = detect_event_diffs(old_events, events)
    if diff["added"]:
        logger.info(f"Discovered {len(diff['added'])} new events.")
    if diff["removed"]:
        logger.info(f"{len(diff['removed'])} previously listed events have completed/been removed.")

    # Step 4: Save raw JSON output
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved raw extracted events to {OUTPUT_JSON_PATH}")

    # Step 5: Generate and save iCalendar .ics file
    ics_content = build_ics_calendar(events)
    with open(OUTPUT_ICS_PATH, "w", encoding="utf-8") as f:
        f.write(ics_content)
    logger.info(f"Saved generated iCalendar to {OUTPUT_ICS_PATH}")

    total_instances = sum(len(e.get("schedule_instances", [])) for e in events)
    logger.info(f"Pipeline complete: {len(events)} events converted into {total_instances} calendar entries.")

    # Step 6: Dispatch outbound webhook if configured
    if WEBHOOK_URL:
        dispatch_webhook(WEBHOOK_URL, diff, len(events), total_instances)


if __name__ == "__main__":
    asyncio.run(main())