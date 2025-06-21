#!/usr/bin/env python3
"""
Script to remove specified fields from facilities_with_coordinates_results.jsonl and create a trimmed version.
"""

import json
import os
from pathlib import Path

def trim_facilities_inspections():
    """
    Remove specified fields from facilities_with_coordinates_results.jsonl and create trimmed_facilities_with_coordinates_results.jsonl
    """
    # Fields to remove from each inspection (as specified in the user query)
    fields_to_remove = [
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
        "Total Deficiencies"
    ]
    
    # Input and output file paths (relative to current working directory)
    input_file = Path("../../../data/distilled_data/facilities_with_coordinates_results.jsonl")
    output_file = Path("../../../data/distilled_data/trimmed_facilities_with_coordinates_results.jsonl")
    
    # Ensure input file exists
    if not input_file.exists():
        print(f"Error: Input file {input_file} does not exist.")
        return
    
    # Create output directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    processed_count = 0
    error_count = 0
    
    print(f"Processing {input_file}...")
    print(f"Removing {len(fields_to_remove)} fields from each inspection...")
    
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
                
            try:
                # Parse JSON from the line
                data = json.loads(line)
                
                # Process each inspection in the Inspections array
                if 'Inspections' in data and isinstance(data['Inspections'], list):
                    for inspection in data['Inspections']:
                        # Remove specified fields from each inspection
                        for field in fields_to_remove:
                            inspection.pop(field, None)  # Use pop with default to avoid KeyError
                
                # Write the trimmed data back to output file
                json.dump(data, outfile, ensure_ascii=False)
                outfile.write('\n')
                
                processed_count += 1
                
                # Progress indicator
                if processed_count % 100 == 0:
                    print(f"Processed {processed_count} facilities...")
                    
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON on line {line_num}: {e}")
                error_count += 1
                continue
            except Exception as e:
                print(f"Unexpected error on line {line_num}: {e}")
                error_count += 1
                continue
    
    print(f"\nProcessing complete!")
    print(f"Successfully processed: {processed_count} facilities")
    print(f"Errors encountered: {error_count}")
    print(f"Output file: {output_file}")
    
    # Verify the output file was created and has content
    if output_file.exists():
        file_size = output_file.stat().st_size
        print(f"Output file size: {file_size:,} bytes")
        
        # Show a sample of the first record to verify structure
        with open(output_file, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line:
                sample_data = json.loads(first_line)
                if 'Inspections' in sample_data and sample_data['Inspections']:
                    first_inspection = sample_data['Inspections'][0]
                    remaining_fields = list(first_inspection.keys())
                    print(f"\nSample of remaining fields in first inspection ({len(remaining_fields)} total):")
                    for field in remaining_fields[:10]:  # Show first 10 fields
                        print(f"  - {field}")
                    if len(remaining_fields) > 10:
                        print(f"  ... and {len(remaining_fields) - 10} more fields")

if __name__ == "__main__":
    trim_facilities_inspections()
