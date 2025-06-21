#!/usr/bin/env python3
"""
Pure-LLM ICE-ODO dataset builder
--------------------------------
• Reads foia_library_entries.csv
• Downloads every '*odo-compliance-inspections*' PDF
• Extracts full text + every table via pdfplumber
• Sends the raw payload to DeepSeek-Chat
• Writes one JSON object per inspection to odo_inspections.jsonl

Dependencies
------------
pip install pandas pdfplumber requests openai tqdm python-dotenv
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import dotenv
import pandas as pd
import pdfplumber
import requests
from openai import OpenAI          # openai>=1.0.0
from tqdm import tqdm

# ──────────────── load env & constants ──────────────── #
dotenv.load_dotenv()
API_KEY       = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    raise RuntimeError("Add DEEPSEEK_API_KEY to .env")

CSV_PATH      = Path("data/foia_library_entries.csv")
CACHE_DIR     = Path("pdf_cache")
OUT_PATH      = Path("data/distilled_data/odo_inspections.jsonl")
CHECKPOINT_PATH = Path("data/distilled_data/checkpoint.txt")  # Track progress
MODEL         = "deepseek-chat"
MAX_TOKENS    = 4096               # response cap (adjust ≤ model limit)
SAVE_INTERVAL = 10                 # Save progress every N reports

# Deficiency categories that should be extracted from the findings table
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
    "Detention Files Detainee Transfers"
]

# Keys DeepSeek must supply verbatim
DESIRED_KEYS: List[str] = [
    "Detention Center", "Inspection Type", "URL", "Inspection Date",
    "Field Office", "Announced vs Unannounced",
    # deficiency categories (24) + total
    *DEFICIENCY_CATEGORIES,
    "Total Deficiencies",
    # interviews
    "Interviews Conducted", "Interview Attempts Failed",
    # narrative sections
    "SAFETY", "SECURITY", "CARE", "ACTIVITIES", "JUSTICE", "CONCLUSION"
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
    """Convert a list-of-lists table to RFC-4180 style CSV text."""
    return "\n".join(
        ",".join("" if cell is None else str(cell).replace(",", " ") for cell in row)
        for row in tbl
    )

def find_deficiency_table(tables: List[List[List[str | None]]]) -> Optional[str]:
    """Find the deficiency findings table by looking for key phrases."""
    for i, table in enumerate(tables):
        table_text = " ".join(str(cell) for row in table for cell in row if cell)
        if any(phrase.lower() in table_text.lower() for phrase in [
            "findings by national detention standards",
            "major categories",
            "deficiency",
            "environmental health and safety"
        ]):
            return f"TABLE_{i}:\n{table_to_csv(table)}"
    return None

def extract_payload(pdf_path: Path) -> Dict[str, str]:
    """Return {'text': full_text, 'tables': combined_csv_string, 'deficiency_table': specific_table}."""
    texts: List[str] = []
    all_tables: List[List[List[str | None]]] = []
    csv_tables: List[str] = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            texts.append(txt)
            for tbl in page.extract_tables():
                all_tables.append(tbl)
                csv_tables.append(table_to_csv(tbl))
    
    # Find the specific deficiency table
    deficiency_table = find_deficiency_table(all_tables)
    
    return {
        "text": "\n".join(texts),
        "tables": "\n\n".join(csv_tables) or "(no tables)",
        "deficiency_table": deficiency_table or "(no deficiency table found)"
    }

def deepseek_extract(url: str, payload: Dict[str, str]) -> Dict:
    system_prompt = (
        "You are an information-extraction assistant for ICE detention facility inspection reports. "
        "Extract specific data from PDF text and tables, returning only valid JSON with exact keys provided. "
        "For deficiency counts, look for numbers in the findings table. For narrative sections, extract full text content. "
        "For interview data, carefully parse the detainee relations section to count interviews conducted and failed attempts. "
        "IMPORTANT: Use 0 (number) for zero deficiencies, not 'N/A' or '0' (string)."
    )

    user_prompt = (
        f"Extract information from this ICE detention facility inspection report.\n\n"
        f"Return a JSON object with these exact keys:\n"
        f"{json.dumps(DESIRED_KEYS)}\n\n"
        f"IMPORTANT INSTRUCTIONS:\n"
        f"1. For deficiency categories, extract the NUMBER of deficiencies from the findings table. "
        f"   Look for a table with headers like 'FINDINGS BY NATIONAL DETENTION STANDARDS' or similar. "
        f"   If a category has no deficiencies, use 0 (as a number, not string). If the category is not found in the table, use 'N/A'.\n"
        f"2. For narrative sections (SAFETY, SECURITY, CARE, ACTIVITIES, JUSTICE, CONCLUSION), "
        f"   extract the full text content of each section, excluding footnotes. "
        f"   If a section is not found, use 'N/A'.\n"
        f"3. For interview data, look for patterns like:\n"
        f"   - 'ODO interviewed X detainees' → 'Interviews Conducted' = X\n"
        f"   - 'ODO requested interviews with X additional detainees; however, all X detainees declined' → 'Interview Attempts Failed' = X\n"
        f"   - Look for variations like 'declined', 'refused', 'denied', 'did not agree' etc.\n"
        f"   - If no specific numbers found, use 0 for both fields\n"
        f"4. For other fields, extract from the text or use 'N/A' if not found.\n"
        f"5. For 'Total Deficiencies', sum all the deficiency counts and return as a number.\n\n"
        f"=== BEGIN PDF RAW TEXT ===\n{payload['text']}\n"
        f"=== END PDF RAW TEXT ===\n\n"
        f"=== BEGIN ALL TABLES (CSV) ===\n{payload['tables']}\n"
        f"=== END ALL TABLES ===\n\n"
        f"=== BEGIN DEFICIENCY TABLE (if found) ===\n{payload['deficiency_table']}\n"
        f"=== END DEFICIENCY TABLE ===\n\n"
        f"Focus especially on the deficiency table to extract accurate counts for each category. "
        f"Remember: 0 deficiencies = 0 (number), missing category = 'N/A' (string). "
        f"For interviews, look for the detainee relations section and count both successful interviews and failed attempts."
    )

    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )
    content = resp.choices[0].message.content.strip()
    
    # Extract JSON by finding first '{' and last '}'
    start_idx = content.find('{')
    end_idx = content.rfind('}')
    
    if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
        raise ValueError(f"Could not find valid JSON braces in response: {content[:120]}…")
    
    json_content = content[start_idx:end_idx + 1]
    
    try:
        result = json.loads(json_content)
        
        # Validate that all required keys are present
        missing_keys = [key for key in DESIRED_KEYS if key not in result]
        if missing_keys:
            print(f"Warning: Missing keys in response: {missing_keys}")
            # Add missing keys with "N/A"
            for key in missing_keys:
                result[key] = "N/A"
        
        # Post-process deficiency fields to ensure proper types
        for category in DEFICIENCY_CATEGORIES + ["Total Deficiencies"]:
            if category in result:
                value = result[category]
                # If it's a string that looks like a number, convert it
                if isinstance(value, str) and value.strip().isdigit():
                    result[category] = int(value)
                # If it's "0" or 0, ensure it's the number 0
                elif value == "0" or value == 0:
                    result[category] = 0
                # If it's empty or None, make it 0 for deficiencies
                elif value == "" or value is None:
                    result[category] = 0
        
        # Post-process interview fields to ensure proper types
        for field in ["Interviews Conducted", "Interview Attempts Failed"]:
            if field in result:
                value = result[field]
                # If it's a string that looks like a number, convert it
                if isinstance(value, str) and value.strip().isdigit():
                    result[field] = int(value)
                # If it's "0" or 0, ensure it's the number 0
                elif value == "0" or value == 0:
                    result[field] = 0
                # If it's empty, None, or "N/A", make it 0 for interviews
                elif value == "" or value is None or value == "N/A":
                    result[field] = 0
        
        return result
    except json.JSONDecodeError as e:
        raise ValueError(f"DeepSeek returned invalid JSON: {json_content[:120]}…") from e

# ─────────────── main loop ─────────────── #

def load_checkpoint() -> int:
    """Load the last processed index from checkpoint file."""
    if CHECKPOINT_PATH.exists():
        try:
            return int(CHECKPOINT_PATH.read_text().strip())
        except (ValueError, IOError):
            return 0
    return 0

def save_checkpoint(index: int) -> None:
    """Save the current index to checkpoint file."""
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(str(index))

def main() -> None:
    df = pd.read_csv(CSV_PATH)
    rows = df[df["link"].str.contains("odo-compliance-inspections", na=False)]
    
    # Load checkpoint to resume from where we left off
    start_index = load_checkpoint()
    if start_index > 0:
        print(f"Resuming from index {start_index} (processed {start_index} reports)")
        rows = rows.iloc[start_index:].reset_index(drop=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    wrote = 0
    processed_count = start_index

    # Open file in append mode if resuming, write mode if starting fresh
    mode = "a" if start_index > 0 else "w"
    
    with OUT_PATH.open(mode, encoding="utf-8") as fout:
        for idx, row in tqdm(rows.iterrows(), total=len(rows), desc="ODO PDFs"):
            url: str = row["link"]
            try:
                pdf_path = download_pdf(url, CACHE_DIR)
                payload  = extract_payload(pdf_path)
                record   = deepseek_extract(url, payload)
                record["URL"] = url
                json.dump(record, fout, ensure_ascii=False)
                fout.write("\n")
                fout.flush()  # Ensure data is written immediately
                wrote += 1
                processed_count += 1
                
                # Save checkpoint every SAVE_INTERVAL reports
                if processed_count % SAVE_INTERVAL == 0:
                    save_checkpoint(processed_count)
                    print(f"\n✓ Checkpoint saved at {processed_count} reports")
                    
            except Exception as exc:
                print(f"[!] {url} → {exc}")
                # Still save checkpoint even on error to avoid reprocessing
                save_checkpoint(processed_count)

    # Save final checkpoint
    save_checkpoint(processed_count)
    print(f"\n✓ Wrote {wrote} inspections → {OUT_PATH.resolve()}")
    print(f"✓ Final checkpoint saved at {processed_count} reports")

if __name__ == "__main__":
    main()
