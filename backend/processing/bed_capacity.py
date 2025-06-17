#!/usr/bin/env python3
"""
Iterate through data/foia_library_entries.csv.  
For every record whose `link` field points at a PDF, download (or open) the file,
search each page for the two-column table headed

    Capacity and Population Statistics | Quantity

When the table is found, pull the following rows:

  • ICE Bed Capacity
  • Average ICE Population
  • Adult Male Population (ignore the printed date)
  • Adult Female Population (ignore the printed date)

If a cell is redacted (either the literal word “REDACTED” or a black-box ▇ character),
store the string “REDACTED”.  
If the table is absent, skip the record entirely.

Output: capacity_population_summary.csv with columns

    title, date, ICE Bed Capacity, Average ICE Population,
    Adult Male Population, Adult Female Population
"""
from __future__ import annotations

import csv
import io
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import pdfplumber
import requests
from tqdm import tqdm

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
SOURCE_CSV = Path("data/foia_library_entries.csv")
OUTPUT_CSV = SOURCE_CSV.parent / "capacity_population_summary.csv"
HEADERS = [
    "ICE Bed Capacity",
    "Average ICE Population",
    "Adult Male Population",
    "Adult Female Population",
]
REDACTION_PATTERN = re.compile(r"(REDACTED|█|■|▇)", re.I)  # matches common redaction


# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #
def fetch_pdf(link: str, tmp_dir: Path) -> Optional[Path]:
    """
    Download the PDF (if it's remote) or copy it into tmp_dir (if it's a local path),
    returning the local filesystem path. On any failure, return None.
    """
    try:
        if link.lower().startswith(("http://", "https://")):
            resp = requests.get(link, timeout=30)
            resp.raise_for_status()
            pdf_path = tmp_dir / Path(link).name
            pdf_path.write_bytes(resp.content)
        else:
            # Treat as local file
            src = Path(link).expanduser()
            if not src.is_file():
                return None
            pdf_path = tmp_dir / src.name
            shutil.copy(src, pdf_path)
        return pdf_path
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Could not fetch {link}: {exc}", file=sys.stderr)
        return None


def extract_table_values(pdf_path: Path) -> Optional[Dict[str, str]]:
    """
    Scan every page for the targeted table.  The moment we find it, parse the values
    into a dict keyed by HEADERS.  Return None if the table doesn't exist.
    """
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    # pdfplumber returns a list-of-lists; normalise empties to ""
                    rows = [[cell or "" for cell in row] for row in table]
                    if not rows:
                        continue

                    # A header row must contain BOTH keywords
                    header_row = rows[0]
                    joined_header = " ".join(header_row).lower()
                    if "capacity and population statistics" not in joined_header:
                        continue
                    if "quantity" not in joined_header:
                        continue

                    # Build a simple dict: first column = label, last column = value
                    results: Dict[str, str] = {}
                    for row in rows[1:]:
                        label = row[0].strip()
                        value = row[-1].strip()

                        # Normalise labels so they match HEADERS list
                        label = re.sub(r"\s*\(.*?\)", "", label).strip()  # remove parenthetical dates

                        if label in HEADERS:
                            if REDACTION_PATTERN.search(value):
                                value = "REDACTED"
                            results[label] = value or "REDACTED"

                    # Ensure we captured at least one field; otherwise keep searching
                    if results:
                        # Fill any missing keys explicitly as REDACTED so the CSV has every column
                        for key in HEADERS:
                            results.setdefault(key, "REDACTED")
                        return results
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Failed parsing {pdf_path}: {exc}", file=sys.stderr)

    return None  # table not found on any page or error


# --------------------------------------------------------------------------- #
# Main routine
# --------------------------------------------------------------------------- #
def main() -> None:
    if not SOURCE_CSV.is_file():
        sys.exit(f"ERROR: {SOURCE_CSV} not found")

    df = pd.read_csv(SOURCE_CSV, dtype=str).fillna("")

    output_rows = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        for _, record in tqdm(df.iterrows(), total=len(df), desc="Processing FOIA PDFs"):
            link: str = record.get("link", "")
            if not link.lower().endswith(".pdf"):
                continue  # non-PDF entry

            pdf_path = fetch_pdf(link, tmp_dir)
            if pdf_path is None:
                continue

            vals = extract_table_values(pdf_path)
            if vals is None:
                continue  # table absent → skip record

            output_rows.append(
                {
                    "title": record.get("title", "").strip(),
                    "date": record.get("date", "").strip(),
                    **vals,
                }
            )

    if not output_rows:
        print("No matching tables were found in any PDF.")
        return

    # Write output CSV
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "date", *HEADERS])
        writer.writeheader()
        for row in output_rows:
            writer.writerow(row)

    print(f"✓ Extracted {len(output_rows)} record(s) → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
