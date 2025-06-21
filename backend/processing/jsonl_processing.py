import json
from collections import defaultdict

# Load input .jsonl file
input_path = "data/distilled_data/odo_inspections.jsonl"
output_path = "merged_by_center.jsonl"

# Dictionary to hold lists of entries per center
merged_data = defaultdict(list)

with open(input_path, "r") as infile:
    for line in infile:
        entry = json.loads(line)
        center = entry["Detention Center"]
        merged_data[center].append(entry)

# Save merged entries, one per center, with "entries" as a list
with open(output_path, "w") as outfile:
    for center, entries in merged_data.items():
        json.dump({"Detention Center": center, "Inspections": entries}, outfile)
        outfile.write("\n")
