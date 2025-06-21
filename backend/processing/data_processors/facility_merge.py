#!/usr/bin/env python3
"""
Facility Merge Script

This script merges detention center inspection data from odo_inspections.jsonl
with facility coordinates from all_facilities_with_coordinates.csv based on
name similarity matching.
"""

import json
import csv
import sys
from difflib import SequenceMatcher
from pathlib import Path


def calculate_similarity(str1, str2):
    """
    Calculate similarity between two strings using SequenceMatcher.
    Returns a value between 0 and 1, where 1 is identical.
    """
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def get_confidence_level(similarity_score):
    """
    Convert similarity score to a human-readable confidence level.
    """
    if similarity_score >= 0.9:
        return "HIGH"
    elif similarity_score >= 0.7:
        return "MEDIUM"
    elif similarity_score >= 0.5:
        return "LOW"
    else:
        return "VERY_LOW"


def find_best_match(detention_center_name, facilities):
    """
    Find the facility with the most similar name to the detention center.
    Returns the best matching facility and its similarity score.
    """
    best_match = None
    best_score = 0.0
    
    for facility in facilities:
        facility_name = facility['name']
        score = calculate_similarity(detention_center_name, facility_name)
        
        if score > best_score:
            best_score = score
            best_match = facility
    
    return best_match, best_score


def load_facilities(csv_path):
    """
    Load facilities from CSV file.
    """
    facilities = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            facilities.append(row)
    return facilities


def process_inspections(jsonl_path, facilities, output_path):
    """
    Process inspections and merge with facility coordinates.
    """
    processed_count = 0
    matched_count = 0
    unmatched_count = 0
    low_confidence_count = 0
    
    with open(jsonl_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            try:
                # Parse JSON line
                inspection = json.loads(line.strip())
                detention_center = inspection.get('Detention Center', '')
                
                if not detention_center:
                    print(f"Warning: No detention center name found in line {line_num}")
                    unmatched_count += 1
                    # Write original record without coordinates
                    outfile.write(line)
                    continue
                
                # Find best matching facility
                best_match, similarity_score = find_best_match(detention_center, facilities)
                
                if best_match and similarity_score >= 0.3:  # Threshold for acceptable match
                    # Add coordinates and matching info to the inspection record
                    inspection['latitude'] = best_match.get('Latitude', '')
                    inspection['longitude'] = best_match.get('Longitude', '')
                    inspection['matched_facility_name'] = best_match.get('name', '')
                    inspection['similarity_score'] = round(similarity_score, 3)
                    inspection['confidence_level'] = get_confidence_level(similarity_score)
                    
                    # Add additional facility info for manual verification
                    inspection['facility_field_office'] = best_match.get('field_office', '')
                    inspection['facility_city'] = best_match.get('city', '')
                    inspection['facility_state'] = best_match.get('state', '')
                    inspection['facility_street'] = best_match.get('street', '')
                    
                    matched_count += 1
                    
                    # Track low confidence matches
                    if similarity_score < 0.7:
                        low_confidence_count += 1
                        print(f"LOW CONFIDENCE: '{detention_center}' -> '{best_match['name']}' (score: {similarity_score:.3f}, confidence: {get_confidence_level(similarity_score)})")
                    else:
                        print(f"Matched: '{detention_center}' -> '{best_match['name']}' (score: {similarity_score:.3f}, confidence: {get_confidence_level(similarity_score)})")
                else:
                    # No good match found
                    inspection['latitude'] = ''
                    inspection['longitude'] = ''
                    inspection['matched_facility_name'] = ''
                    inspection['similarity_score'] = 0.0
                    inspection['confidence_level'] = 'NO_MATCH'
                    inspection['facility_field_office'] = ''
                    inspection['facility_city'] = ''
                    inspection['facility_state'] = ''
                    inspection['facility_street'] = ''
                    unmatched_count += 1
                    print(f"No match found for: '{detention_center}' (best score: {similarity_score:.3f})")
                
                # Write the updated record
                outfile.write(json.dumps(inspection) + '\n')
                processed_count += 1
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON on line {line_num}: {e}")
                continue
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                continue
    
    return processed_count, matched_count, unmatched_count, low_confidence_count


def main():
    """
    Main function to run the facility merge process.
    """
    # Define file paths using absolute paths
    jsonl_path = Path('/Users/jackvu/Desktop/latex_projects/icemap/data/distilled_data/odo_inspections.jsonl')
    csv_path = Path('/Users/jackvu/Desktop/latex_projects/icemap/data/all_facilities_with_coordinates.csv')
    output_path = Path('/Users/jackvu/Desktop/latex_projects/icemap/data/distilled_data/odo_inspections_with_coordinates.jsonl')
    
    # Check if input files exist
    if not jsonl_path.exists():
        print(f"Error: Input file not found: {jsonl_path}")
        sys.exit(1)
    
    if not csv_path.exists():
        print(f"Error: Facilities file not found: {csv_path}")
        sys.exit(1)
    
    print("Loading facilities...")
    facilities = load_facilities(csv_path)
    print(f"Loaded {len(facilities)} facilities")
    
    print("Processing inspections...")
    processed, matched, unmatched, low_confidence = process_inspections(jsonl_path, facilities, output_path)
    
    print(f"\nProcessing complete!")
    print(f"Total records processed: {processed}")
    print(f"Successfully matched: {matched}")
    print(f"Unmatched: {unmatched}")
    print(f"Low confidence matches (score < 0.7): {low_confidence}")
    print(f"Match rate: {(matched/processed)*100:.1f}%")
    print(f"Low confidence rate: {(low_confidence/matched)*100:.1f}% of matches")
    print(f"Output written to: {output_path}")
    print(f"\nConfidence levels:")
    print(f"  HIGH: similarity >= 0.9")
    print(f"  MEDIUM: similarity >= 0.7")
    print(f"  LOW: similarity >= 0.5")
    print(f"  VERY_LOW: similarity < 0.5")
    print(f"  NO_MATCH: no match found")


if __name__ == "__main__":
    main()
