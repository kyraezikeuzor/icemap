#!/usr/bin/env python3
"""
Collect U.S. news stories mentioning ICE enforcement activity via the
MediaCloud v4 API and append them to data/mediacloud_articles.csv,
deduplicating on URL. This script is for historical backfill: it uses the
OLDEST article in the CSV as the END date, and fetches further back in time.
"""
from __future__ import annotations

import csv
import os
import sys
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Set

from dotenv import load_dotenv
import mediacloud.api  # v4 client (≥ 4.0)

# ─────────────────────────────
# Config
# ─────────────────────────────
load_dotenv()

API_KEY = os.getenv("MEDIACLOUD_API_KEY_4")
if not API_KEY:
    sys.exit("❌  MEDIACLOUD_API_KEY not found in your .env file")

OUTPUT_CSV = Path("data/mediacloud_articles.csv")
RATE_LIMIT_DELAY = 1            # seconds between requests
LOOKBACK_DAYS = 365             # how far back to fetch
US_NATIONAL_COLLECTION = 34412234

QUERY = r"""
("Immigration and Customs Enforcement"~0
 OR "Servicio de Inmigración y Control de Aduanas"~0
 OR ("ICE"~0 AND (arrest OR raid OR custody OR detainer OR sweep OR detention)))
AND NOT ("ice cream" OR "ice hockey" OR "meth" OR "ice storm")
""".strip()

# ─────────────────────────────
# Helpers
# ─────────────────────────────
def mc_client() -> mediacloud.api.SearchApi:
    return mediacloud.api.SearchApi(API_KEY)


def load_existing_urls() -> Set[str]:
    if OUTPUT_CSV.exists():
        with OUTPUT_CSV.open("r", encoding="utf-8") as fh:
            return {row["url"] for row in csv.DictReader(fh) if row.get("url")}
    return set()


def save_articles(rows: List[Dict[str, str]]) -> None:
    if not rows:
        print("🟡  No new stories found.")
        return

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    first_write = not OUTPUT_CSV.exists()

    with OUTPUT_CSV.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["title", "description", "date", "url"], extrasaction="ignore"
        )
        if first_write:
            writer.writeheader()
        writer.writerows(rows)

    print(f"✅  Saved {len(rows):,} new stories → {OUTPUT_CSV}")


def fetch_articles(
    mc: mediacloud.api.SearchApi,
    since: date,
    until: date,
    seen: Set[str],
) -> List[Dict[str, str]]:
    new_rows: List[Dict[str, str]] = []
    token: str | None = None

    while True:
        time.sleep(RATE_LIMIT_DELAY)
        try:
            page, token = mc.story_list(
                QUERY,
                start_date=since,
                end_date=until,
                collection_ids=[US_NATIONAL_COLLECTION],
                pagination_token=token,
            )
        except Exception as exc:
            print(f"🛑  API error: {exc}")
            break

        if not page:
            break

        for story in page:
            url = story.get("url")
            if url and url not in seen:
                title = story.get("title", "")
                description = story.get("description", "")
                
                new_rows.append(
                    {
                        "title": title.strip() if title else "",
                        "description": description.strip() if description else "",
                        "date": story.get("publish_date", ""),
                        "url": url,
                    }
                )
                seen.add(url)

        print(f"…fetched {len(new_rows):,} unique so far")
        if token is None:
            break

    return new_rows


def get_oldest_date_from_csv() -> date:
    """Return the oldest (last) date in the CSV as a date object."""
    if not OUTPUT_CSV.exists():
        sys.exit(f"❌  {OUTPUT_CSV} does not exist!")
    with OUTPUT_CSV.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        last_row = None
        for row in reader:
            last_row = row
        if not last_row or not last_row.get("date"):
            sys.exit("❌  Could not find a valid date in the last row of the CSV.")
        try:
            return datetime.strptime(last_row["date"], "%Y-%m-%d").date()
        except Exception as e:
            sys.exit(f"❌  Failed to parse date '{last_row['date']}' in last row: {e}")

# ─────────────────────────────
# Main
# ─────────────────────────────
def main() -> None:
    mc = mc_client()

    seen_urls = load_existing_urls()
    print(f"🔍  {len(seen_urls):,} URLs already on disk; avoiding duplicates")

    end_date = get_oldest_date_from_csv()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)
    print(f"Fetching from {start_date} to {end_date} (historical backfill)")

    fresh_rows = fetch_articles(mc, start_date, end_date, seen_urls)
    save_articles(fresh_rows)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user – exiting.")
