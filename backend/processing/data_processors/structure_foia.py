#!/usr/bin/env python3
"""
Pure-LLM ICE-ODO dataset builder  ⚡ PARALLEL EDITION
----------------------------------------------------
• Reads foia_library_entries.csv
• Downloads every '*odo-compliance-inspections*' PDF
• Extracts full text + every table via pdfplumber
• Sends the raw payload to DeepSeek-Chat
• Writes one JSON object per inspection to odo_inspections.jsonl
• Uses a ThreadPoolExecutor for massive speed-ups on I/O-heavy steps

Dependencies
------------
pip install pandas pdfplumber requests openai tqdm python-dotenv
"""

from __future__ import annotations

import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

import dotenv
import pandas as pd
import pdfplumber
import requests
from openai import OpenAI          # openai>=1.0.0
from tqdm import tqdm

# ──────────────── env & constants ──────────────── #
dotenv.load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    raise RuntimeError("Add DEEPSEEK_API_KEY to .env")

CSV_PATH        = Path("data/foia_library_entries.csv")
CACHE_DIR       = Path("pdf_cache")
OUT_PATH        = Path("data/distilled_data/odo_inspections.jsonl")
CHECKPOINT_PATH = Path("data/distilled_data/checkpoint.txt")
MODEL           = "deepseek-chat"
MAX_TOKENS      = 4096
SAVE_INTERVAL   = 10                # checkpoint cadence

# Parallelism → env override (default 6, good for M-series)
CONCURRENCY = int(os.getenv("CONCURRENCY", "6"))

# ─────────────── deficiency setup ─────────────── #
DEFICIENCY_CATEGORIES: List[str] = [
    "Environmental Health and Safety",
    "Admission and Release",
    "Custody Classification",
    "System Facility",
    "Security and Control",
    "Funds and Personal Property",
    "Post Orders",
    "Searches of Detainees",
    "Use of Force and Restraints",
    "Special Management Units",
    "Staff-Detainee Communication",
    "Sexual Abuse and Assault Prevention and Intervention",
    "Food Service",
    "Hunger Strikes",
    "Medical Care",
    "Personal Hygiene Significant",
    "Self-Harm and Suicide Prevention and Intervention",
    "Correspondence and Other Mail",
    "Religious Practices",
    "Telephone Access",
    "Voluntary Work Program",
    "Grievance System",
    "Law Libraries and Legal Materials",
    "Detention Files Detainee Transfers",
]

DESIRED_KEYS: List[str] = [
    "Detention Center",
    "Inspection Type",
    "URL",
    "Inspection Date",
    "Field Office",
    "Announced vs Unannounced",
    *DEFICIENCY_CATEGORIES,
    "Total Deficiencies",
    "Interviews Conducted",
    "Interview Attempts Failed",
    "SAFETY",
    "SECURITY",
    "CARE",
    "ACTIVITIES",
    "JUSTICE",
    "CONCLUSION",
]

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# ─────────────── helpers ─────────────── #
def download_pdf(url: str, cache_dir: Path) -> Path:
    cache_dir.mkdir(exist_ok=True)
    local = cache_dir / Path(url).name
    if not local.exists():
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        local.write_bytes(r.content)
    return local


def table_to_csv(tbl: List[List[str | None]]) -> str:
    return "\n".join(
        ",".join("" if cell is None else str(cell).replace(",", " ") for cell in row)
        for row in tbl
    )


def find_deficiency_table(
    tables: List[List[List[str | None]]]
) -> Optional[str]:
    for i, table in enumerate(tables):
        flat = " ".join(str(cell) for row in table for cell in row if cell)
        if any(
            phrase in flat.lower()
            for phrase in (
                "findings by national detention standards",
                "major categories",
                "deficiency",
                "environmental health and safety",
            )
        ):
            return f"TABLE_{i}:\n{table_to_csv(table)}"
    return None


def extract_payload(pdf_path: Path) -> Dict[str, str]:
    texts: List[str] = []
    all_tables: List[List[List[str | None]]] = []
    csv_tables: List[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
            for tbl in page.extract_tables():
                all_tables.append(tbl)
                csv_tables.append(table_to_csv(tbl))

    return {
        "text": "\n".join(texts),
        "tables": "\n\n".join(csv_tables) or "(no tables)",
        "deficiency_table": find_deficiency_table(all_tables)
        or "(no deficiency table found)",
    }


def deepseek_extract(url: str, payload: Dict[str, str]) -> Dict:
    system_prompt = (
        "You are an information-extraction assistant for ICE detention facility "
        "inspection reports. Follow instructions exactly and return ONLY valid JSON."
    )

    user_prompt = (
        f"Extract the following keys, returning valid JSON only:\n"
        f"{json.dumps(DESIRED_KEYS)}\n\n"
        f"Rules:\n"
        f"1. Use integers for deficiency counts; 0 means none; missing category → 'N/A'.\n"
        f"2. Narrative sections (SAFETY … CONCLUSION) → full text or 'N/A'.\n"
        f"3. Interview numbers: derive from phrasing like 'ODO interviewed X detainees'. "
        f"Failed attempts = declined / refused counts.\n"
        f"4. Total Deficiencies = sum of category counts.\n\n"
        f"=== PDF TEXT ===\n{payload['text']}\n"
        f"=== ALL TABLES ===\n{payload['tables']}\n"
        f"=== DEFICIENCY TABLE ===\n{payload['deficiency_table']}\n"
    )

    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = resp.choices[0].message.content.strip()
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise ValueError("DeepSeek response missing JSON braces")
    obj = json.loads(content[start : end + 1])

    # post-process to guarantee numeric types
    for cat in DEFICIENCY_CATEGORIES + ["Total Deficiencies"]:
        if cat in obj and isinstance(obj[cat], str) and obj[cat].isdigit():
            obj[cat] = int(obj[cat])
    for fld in ("Interviews Conducted", "Interview Attempts Failed"):
        if fld in obj and isinstance(obj[fld], str) and obj[fld].isdigit():
            obj[fld] = int(obj[fld])
    obj["URL"] = url
    return obj


# ─────────────── checkpoint helpers ─────────────── #
def load_checkpoint() -> int:
    if CHECKPOINT_PATH.exists():
        try:
            return int(CHECKPOINT_PATH.read_text().strip())
        except Exception:
            pass
    return 0


def save_checkpoint(idx: int) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(str(idx))


# ─────────────── parallel machinery ─────────────── #
_write_lock = threading.Lock()
_ckpt_lock = threading.Lock()
_processed = load_checkpoint()


def _process_row(idx: int, row: pd.Series, fout) -> None:
    global _processed
    url = row["link"]
    try:
        pdf_path = download_pdf(url, CACHE_DIR)
        payload = extract_payload(pdf_path)
        record = deepseek_extract(url, payload)

        with _write_lock:
            json.dump(record, fout, ensure_ascii=False)
            fout.write("\n")
            fout.flush()
    except Exception as ex:
        print(f"[!] {url} → {ex}")

    with _ckpt_lock:
        _processed += 1
        if _processed % SAVE_INTERVAL == 0:
            save_checkpoint(_processed)


# ─────────────── main ─────────────── #
def main() -> None:
    df = pd.read_csv(CSV_PATH)
    rows = df[df["link"].str.contains("odo-compliance-inspections", na=False)]

    if _processed:
        print(f"Resuming at row {_processed}")
        rows = rows.iloc[_processed :].reset_index(drop=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if _processed else "w"

    with OUT_PATH.open(mode, encoding="utf-8") as fout, ThreadPoolExecutor(
        max_workers=CONCURRENCY
    ) as pool:
        futures = {
            pool.submit(_process_row, idx, row, fout)
            for idx, row in rows.iterrows()
        }

        for _ in tqdm(
            as_completed(futures),
            total=len(futures),
            desc=f"ODO PDFs (×{CONCURRENCY})",
        ):
            pass

    save_checkpoint(_processed)
    print(f"\n✓ Finished {_processed} reports → {OUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
