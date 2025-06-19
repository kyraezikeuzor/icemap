import csv
import os
from datetime import datetime

# Paths
DATA_DIR = os.path.join(os.path.dirname(__file__), '../../data/distilled_data')
NEWSROOM_FILE = os.path.join(DATA_DIR, 'newsroom_incidents.csv')
ARRESTS_FILE = os.path.join(DATA_DIR, 'arrests.csv')
OUTPUT_FILE = os.path.join(DATA_DIR, 'aggregated_incidents.csv')

# Read CSV and return list of dicts
def read_csv(filepath):
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames

# Get superset of all columns
def get_all_columns(*fieldnames_lists):
    columns = set()
    for fields in fieldnames_lists:
        columns.update(fields)
    return list(columns)

# Main merge logic
def merge_csvs():
    newsroom_rows, newsroom_fields = read_csv(NEWSROOM_FILE)
    arrests_rows, arrests_fields = read_csv(ARRESTS_FILE)

    # Ensure 'category' and 'date' are in columns
    all_columns = set(newsroom_fields) | set(arrests_fields)
    all_columns.add('category')
    all_columns.add('date')
    all_columns = list(all_columns)

    merged_rows = []

    # Process newsroom rows (category as-is)
    for row in newsroom_rows:
        merged_row = {col: row.get(col, 'Unknown') or 'Unknown' for col in all_columns}
        merged_rows.append(merged_row)

    # Process arrests rows (category = 'arrest', date = 'Unknown' if missing)
    for row in arrests_rows:
        merged_row = {col: row.get(col, 'Unknown') or 'Unknown' for col in all_columns}
        merged_row['category'] = 'arrest'
        if not merged_row.get('date') or merged_row['date'] == 'Unknown':
            merged_row['date'] = 'Unknown'
        merged_rows.append(merged_row)

    # Sort by date (Unknowns last)
    def parse_date(d):
        if d in (None, '', 'Unknown'):
            return datetime.max
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(d, fmt)
            except Exception:
                continue
        return datetime.max

    merged_rows.sort(key=lambda r: parse_date(r.get('date', 'Unknown')))

    # Write output
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_columns)
        writer.writeheader()
        for row in merged_rows:
            writer.writerow(row)

if __name__ == '__main__':
    merge_csvs()
