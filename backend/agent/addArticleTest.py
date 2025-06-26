import argparse
import json
import sys
from pathlib import Path
import dotenv
import requests
import os
# ---------------------------------------------------------------------------

# Load environment variables
dotenv.load_dotenv()

SAMPLE_PAYLOAD = {
    "title": "ICE arrests 15 at Houston warehouse sting",
    "date":  "2025-06-25T15:30:00Z",
    "url":   "https://www.example.com/news/ice-houston-sting",
    "coordinates": {"lat": 29.7604, "lon": -95.3698},
    "publisher": "Example News",
    "category":  "immigration-enforcement"
}

# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Test the putArticle endpoint")
    ap.add_argument("--file", type=Path, help="Path to JSON article file")
    ap.add_argument("--put",  action="store_true", help="Use PUT instead of POST")
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    # Get API key and URL from environment variables
    api_key = os.getenv("ARTICLES_API_KEY")
    api_url = os.getenv("ARTICLES_API")
    
    if not api_url:
        sys.exit("✖ ARTICLES_API environment variable is required")
    
    if not api_key:
        sys.exit("✖ ARTICLES_API_KEY environment variable is required")

    # Load payload
    if args.file:
        try:
            payload = json.loads(args.file.read_text())
        except Exception as exc:  # noqa: BLE001
            sys.exit(f"✖ Could not read {args.file}: {exc}")
    else:
        payload = SAMPLE_PAYLOAD

    # Headers
    headers = {"Content-Type": "application/json"}
    headers["x-api-key"] = api_key

    # Choose verb
    verb = requests.put if args.put else requests.post

    print(f"→ {verb.__name__.upper()} {api_url}")
    resp = verb(api_url, headers=headers, json=payload, timeout=10)

    # Pretty-print result
    try:
        body = resp.json()
        body_out = json.dumps(body, indent=2)
    except ValueError:
        body_out = resp.text

    print(f"← HTTP {resp.status_code}\n{body_out}")


if __name__ == "__main__":
    main()
