#!/usr/bin/env python3
"""
Scan data/foia_library_entries.csv. For every record whose `link`
is a PDF, download it, extract the *Capacity & Population Statistics*
table and write the result to capacity_population_summary.csv.

DeepSeek's OpenAI-compatible endpoint is used **only** to pull the
four values when local PDF parsing can't find them outright.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import pdfplumber           # pip install pdfplumber
import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm
from openai import OpenAI   # pip install --upgrade openai>=1.0.0

# ─────────────────────────── configuration ────────────────────────────
load_dotenv()

SOURCE_CSV  = Path("data/foia_library_entries.csv")
OUTPUT_CSV  = SOURCE_CSV.parent / "capacity_population_summary.csv"
HEADERS     = [
    "ICE Bed Capacity",
    "Average ICE Population",
    "Adult Male Population",
    "Adult Female Population",
]
REDACT      = re.compile(r"(REDACTED|█|■|▇)", re.I)
BATCH_SIZE  = 10

API_KEY     = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    sys.exit("Missing DEEPSEEK_API_KEY in .env")

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# ─────────────────────────── helpers ──────────────────────────────────
def fetch_pdf(link: str, tmp_dir: Path) -> tuple[Optional[Path], str]:
    """Return (path, status_message)."""
    try:
        if link.lower().startswith(("http://", "https://")):
            r = requests.get(link, timeout=30)
            r.raise_for_status()
            path = tmp_dir / Path(link).name
            path.write_bytes(r.content)
            return path, "Downloaded"
        else:                                       # local file
            src = Path(link).expanduser()
            if not src.is_file():
                return None, "Local file not found"
            path = tmp_dir / src.name
            shutil.copy(src, path)
            return path, "Copied local file"
    except Exception as exc:
        return None, f"Failed to fetch: {exc}"

def find_table_locally(pdf_path: Path) -> tuple[Optional[Dict[str, str]], str]:
    """Return (values_dict, status_message)."""
    out: Dict[str, str] = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    for row in table:
                        if not row or len(row) < 2:
                            continue
                        label, val = row[0].strip(), (row[1] or "").strip()
                        label_nodate = re.sub(r"\s*\(.*?\)", "", label).strip()
                        if label_nodate in HEADERS:
                            out[label_nodate] = (
                                "REDACTED" if REDACT.search(val) or not val else val
                            )
                if len(out) == len(HEADERS):
                    return out, "Found table locally"
    except Exception as exc:
        return None, f"PDF parsing failed: {exc}"

    return None, "No table found locally"

SYSTEM_MSG = (
    "You are a strict JSON extraction assistant. "
    "Given the raw text of a U.S. ICE detention report, "
    "return ONLY a JSON object with exactly these keys: "
    "'ICE Bed Capacity', 'Average ICE Population', "
    "'Adult Male Population', 'Adult Female Population'. "
    "If a value is redacted or missing, use the string REDACTED. "
    "Return no other keys and no surrounding text."
)

def ask_llm(raw_text: str) -> tuple[Optional[Dict[str, str]], str]:
    """Return (values_dict, status_message)."""
    raw_text = raw_text[:12000]      # keep prompt tiny
    try:
        rsp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_MSG},
                {"role": "user", "content": raw_text},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=200,
        )
        content = rsp.choices[0].message.content
        data = json.loads(content)
        result = {
            k: ("REDACTED" if REDACT.search(str(v)) or not str(v).strip() else str(v))
            for k, v in data.items()
            if k in HEADERS
        }
        if len(result) == len(HEADERS):
            return result, "Found table via LLM"
        return None, "LLM found incomplete data"
    except Exception as exc:
        return None, f"LLM failed: {exc}"

def extract_table_values(pdf_path: Path) -> tuple[Optional[Dict[str, str]], str]:
    """Return (values_dict, status_message)."""
    vals, status = find_table_locally(pdf_path)
    if vals and len(vals) == len(HEADERS):
        return vals, status

    # Fallback: extract page text & ask model
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n\n".join(page.extract_text() or "" for page in pdf.pages)
        vals, llm_status = ask_llm(text)
        if vals and len(vals) == len(HEADERS):
            return vals, llm_status
        return None, f"{status} → {llm_status}"
    except Exception as exc:
        return None, f"{status} → Failed fallback: {exc}"

def save(rows: List[Dict[str, str]], writer: csv.DictWriter, fh) -> None:
    writer.writerows(rows)
    fh.flush()

# ─────────────────────────── main ─────────────────────────────────────
def main() -> None:
    if not SOURCE_CSV.is_file():
        sys.exit(f"{SOURCE_CSV} not found")

    df = pd.read_csv(SOURCE_CSV, dtype=str).fillna("")
    processed = success = 0
    buf: List[Dict[str, str]] = []

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["title", "date", *HEADERS])
        w.writeheader()

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bar = tqdm(df.iterrows(), total=len(df), desc="FOIA PDFs")

            for _, rec in bar:
                processed += 1
                title = rec.get("title", "").strip()
                link = str(rec.get("link", "")).strip()
                
                if not link.lower().endswith(".pdf"):
                    status = "Not a PDF"
                    bar.set_postfix(status=status)
                    print(f"\n{title}: {status}")
                    continue

                pdf, fetch_status = fetch_pdf(link, tmp)
                if not pdf:
                    bar.set_postfix(status=fetch_status)
                    print(f"\n{title}: {fetch_status}")
                    continue

                vals, extract_status = extract_table_values(pdf)
                if not vals:
                    bar.set_postfix(status=extract_status)
                    print(f"\n{title}: {extract_status}")
                    continue

                buf.append(
                    {
                        "title": title,
                        "date": rec.get("date", "").strip(),
                        **vals,
                    }
                )
                success += 1
                bar.set_postfix(
                    status="Success",
                    rate=f"{success/processed:0.1%}"
                )
                print(f"\n{title}: Success ({extract_status})")

                if len(buf) >= BATCH_SIZE:
                    save(buf, w, fh)
                    buf.clear()

            if buf:
                save(buf, w, fh)

    if success:
        print(f"\n✓ Done — {success}/{processed} ({success/processed:0.1%}) saved to {OUTPUT_CSV}")
    else:
        print("\nNo matching tables found.")

if __name__ == "__main__":
    main()
