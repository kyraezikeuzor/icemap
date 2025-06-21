#!/usr/bin/env python3
"""
Optimized ICE Article Categorization & Location Extraction Script
- Parallelized location extraction
- Simplified "start from" resume logic (no checkpoints)
- Skips extraction for non-ICE-related articles (category "unknown")
- Robust address extraction via DeepSeek + Google Places API
"""

import csv
import uuid
import requests
import os
import re
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables
load_dotenv()
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

# Configuration
CATEGORIES = ["raid", "arrest", "detention", "protest", "policy", "opinion", "unknown"]
EXTRACT_CATEGORIES = ["raid", "arrest", "detention", "protest"]
BATCH_SIZE = 20
MAX_WORKERS = 5

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fetch_article_content(url: str) -> str:
    """Fetch & clean article text (first 5000 chars)."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.content, 'html.parser')
        for tag in soup(['script', 'style']):
            tag.decompose()
        text = soup.get_text(separator=' ', strip=True)
        return re.sub(r'\s+', ' ', text)[:5000]
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return ""


def categorize_batch(batch: list[dict]) -> list[dict]:
    """Batch categorize via DeepSeek."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is required")
    prompts = []
    for art in batch:
        prompts.append(f"Title: {art['title']}\nDesc: {art['description']}\nURL: {art['url']}")
    prompt = (
        "You are a content categorization expert for ICE-related articles. "
        f"Classify each into exactly one of: {', '.join(CATEGORIES[:-1])}, or 'unknown' if completely unrelated. "
        "Respond with a JSON array matching the input order, each object: {\"category\":\"...\",\"publisher\":\"...\"}.\n\n"
        + "\n---\n".join(prompts)
    )
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "deepseek-chat", "messages":[{"role":"user","content":prompt}],
               "temperature":0.1, "max_tokens":1000}
    try:
        r = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        arr = content[content.find('['):content.rfind(']')+1]
        parsed = json.loads(arr)
    except Exception as e:
        logger.error(f"DeepSeek categorization failed: {e}")
        parsed = []
    results = []
    for idx, art in enumerate(batch):
        try:
            cat = parsed[idx].get('category','unknown').lower()
            pub = parsed[idx].get('publisher','Unknown')
            if cat not in CATEGORIES:
                cat = 'unknown'
        except Exception:
            cat, pub = 'unknown', 'Unknown'
        results.append({'category': cat, 'publisher': pub})
    return results


def extract_location_with_deepseek(title: str, content: str) -> dict:
    """Ask DeepSeek to pull address, city, state, and zip code."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is required")
    prompt = (
        f"You are an expert in geographic extraction. Given the following article,\n"
        f"Title: {title}\nContent Snippet: {content[:1000]}...\n"
        "Extract a JSON object with exactly these fields:\n"
        "{\"address\": \"<street address>\", \"city\": \"<city>\", "
        "\"state\": \"<state or abbreviation>\", \"zip\": \"<postal code>\"}\n"
        "If any field cannot be determined, use empty string \"\"."
    )
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "deepseek-chat", "messages":[{"role":"user","content":prompt}],
            "temperature":0.1, "max_tokens":200}
    try:
        r = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"]
        js = txt[txt.find('{'):txt.rfind('}')+1]
        loc = json.loads(js)
    except Exception as e:
        logger.warning(f"DeepSeek location extraction failed: {e}")
        loc = {"address": "", "city": "", "state": "", "zip": ""}
    # ensure all keys exist
    for k in ["address","city","state","zip"]:
        loc.setdefault(k, "")
    return loc


def enhance_location_with_google_places(loc: dict) -> dict:
    """Use Google Places to fill in lat/lng and verify address components."""
    if not GOOGLE_PLACES_API_KEY or not loc.get("address"):
        return loc
    try:
        # 1) Text Search to get place_id & geometry
        query = f"{loc['address']}, {loc['city']}, {loc['state']}".strip(", ")
        ts_resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={"query": query, "key": GOOGLE_PLACES_API_KEY},
            timeout=15
        )
        ts_resp.raise_for_status()
        results = ts_resp.json().get("results", [])
        if not results:
            return loc
        top = results[0]
        geometry = top.get("geometry", {}).get("location", {})
        loc["latitude"] = geometry.get("lat", "")
        loc["longitude"] = geometry.get("lng", "")

        # 2) Place Details for structured address components
        place_id = top.get("place_id")
        if place_id:
            pd_resp = requests.get(
                "https://maps.googleapis.com/maps/api/place/details/json",
                params={
                    "place_id": place_id,
                    "fields": "address_component",
                    "key": GOOGLE_PLACES_API_KEY
                },
                timeout=15
            )
            pd_resp.raise_for_status()
            components = pd_resp.json().get("result", {}).get("address_components", [])
            street_num = route = ""
            for comp in components:
                types = comp.get("types", [])
                if "street_number" in types:
                    street_num = comp.get("long_name", "")
                elif "route" in types:
                    route = comp.get("long_name", "")
                elif "locality" in types:
                    loc["city"] = comp.get("long_name", loc["city"])
                elif "administrative_area_level_1" in types:
                    loc["state"] = comp.get("short_name", loc["state"])
                elif "postal_code" in types:
                    loc["zip"] = comp.get("long_name", loc["zip"])
            if street_num and route:
                loc["address"] = f"{street_num} {route}"
    except Exception as e:
        logger.warning(f"Google Places enhancement failed: {e}")
    return loc


def process_article(row: dict, result: dict, scrape_date: str) -> dict:
    """Process single article: fetch, extract, enhance."""
    art = {
        'id': str(uuid.uuid4()),
        'title': row['title'],
        'publisher': result['publisher'],
        'scrape_date': scrape_date,
        'category': result['category'],
        'url': row['url'],
        # default placeholders
        'address': '', 'city': '', 'state': '', 'zip': '',
        'latitude': '', 'longitude': ''
    }
    if result['category'] in EXTRACT_CATEGORIES:
        content = fetch_article_content(row['url'])
        loc = extract_location_with_deepseek(row['title'], content)
        loc = enhance_location_with_google_places(loc)
        art.update(loc)
    return art


def process_articles(input_file: str, output_file: str, start_from: int = 0):
    """Main pipeline: categorize & extract with --start-from resume."""
    with open(input_file, newline='', encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f) if r.get('title') and r.get('url')]
    total = len(rows)
    if start_from >= total:
        print(f"Start index {start_from} >= total articles {total}, nothing to do.")
        return

    mode = 'a' if start_from > 0 else 'w'
    with open(output_file, mode, newline='', encoding='utf-8') as outf:
        fieldnames = [
            'id','title','publisher','scrape_date','category','url',
            'address','city','state','zip','latitude','longitude'
        ]
        writer = csv.DictWriter(outf, fieldnames=fieldnames)
        if start_from == 0:
            writer.writeheader()

        pbar = tqdm(total=total - start_from, desc="Processing articles", unit="article")
        scrape_date = datetime.now().strftime("%Y-%m-%d")

        for i in range(start_from, total, BATCH_SIZE):
            batch = rows[i:i+BATCH_SIZE]
            batch_data = [
                {'title': r['title'], 'description': r.get('description',''), 'url': r['url']}
                for r in batch
            ]
            results = categorize_batch(batch_data)

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [
                    executor.submit(process_article, r, res, scrape_date)
                    for r, res in zip(batch, results)
                ]
                for fut in as_completed(futures):
                    art = fut.result()
                    writer.writerow(art)
                    pbar.update(1)
        pbar.close()
    print(f"Finished. Output saved to {output_file}")


def main():
    import sys
    input_file = "data/mediacloud_report.csv"
    output_file = "data/mediacloud_report_processed.csv"
    start_from = 0
    args = sys.argv[1:]
    if args and args[0] in ('-h', '--help'):
        print("Usage: python categorization.py [--start-from N]")
        return
    if args and args[0] == '--start-from' and len(args) > 1:
        try:
            start_from = int(args[1])
        except ValueError:
            print("Error: start index must be an integer.")
            return

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return
    if not DEEPSEEK_API_KEY:
        print("Error: DEEPSEEK_API_KEY is not set.")
        return

    total = len(list(csv.DictReader(open(input_file, encoding='utf-8'))))
    print(f"Starting from article {start_from+1} of {total}")
    process_articles(input_file, output_file, start_from)


if __name__ == "__main__":
    main()
