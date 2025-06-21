#!/usr/bin/env python3
"""
Script to process detention centers and add coordinates from existing data or highest confidence records.
Outputs in the same JSONL format with additional location and confidence fields.
"""

import json
import csv
import os
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from difflib import SequenceMatcher

def load_jsonl_data(file_path: str) -> List[Dict]:
    """Load data from JSONL file."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def load_facilities_csv(file_path: str) -> Dict[str, Dict]:
    """
    Load facilities with coordinates from CSV file.
    
    Returns:
        Dictionary mapping facility names to their coordinate data
    """
    facilities = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['name'].strip()
            if name and row.get('Latitude') and row.get('Longitude'):
                facilities[name] = {
                    'name': name,
                    'field_office': row.get('field_office', ''),
                    'street': row.get('street', ''),
                    'city': row.get('city', ''),
                    'state': row.get('state', ''),
                    'zipcode': row.get('zipcode', ''),
                    'latitude': float(row['Latitude']),
                    'longitude': float(row['Longitude']),
                    'source': 'existing_coordinates'
                }
    return facilities

def calculate_string_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity between two strings using SequenceMatcher.
    
    Args:
        str1: First string
        str2: Second string
        
    Returns:
        Similarity score between 0 and 1
    """
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def find_most_similar_facility(facility_name: str, existing_facilities: Dict[str, Dict]) -> Tuple[Optional[Dict], float]:
    """
    Find the most similar facility in the existing facilities data.
    
    Args:
        facility_name: Name of the facility to find
        existing_facilities: Dictionary of existing facilities with coordinates
        
    Returns:
        Tuple of (matching facility data, similarity score) or (None, 0.0) if not found
    """
    # Try exact match first
    if facility_name in existing_facilities:
        return existing_facilities[facility_name], 1.0
    
    # Try normalized match
    normalized_name = normalize_facility_name(facility_name)
    for existing_name, facility_data in existing_facilities.items():
        if normalize_facility_name(existing_name) == normalized_name:
            return facility_data, 0.95  # High confidence for normalized match
    
    # Try partial match
    for existing_name, facility_data in existing_facilities.items():
        if (facility_name.lower() in existing_name.lower() or 
            existing_name.lower() in facility_name.lower()):
            similarity = calculate_string_similarity(facility_name, existing_name)
            return facility_data, similarity
    
    # Find the most similar facility using fuzzy matching
    best_match = None
    best_similarity = 0.0
    
    for existing_name, facility_data in existing_facilities.items():
        similarity = calculate_string_similarity(facility_name, existing_name)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = facility_data
    
    return best_match, best_similarity

def normalize_facility_name(name: str) -> str:
    """
    Normalize facility name for better matching.
    
    Args:
        name: Facility name to normalize
        
    Returns:
        Normalized facility name
    """
    # Convert to lowercase and remove extra whitespace
    normalized = name.lower().strip()
    
    # Remove common variations
    normalized = normalized.replace('ice processing center', '')
    normalized = normalized.replace('detention center', '')
    normalized = normalized.replace('detention facility', '')
    normalized = normalized.replace('correctional center', '')
    normalized = normalized.replace('correctional facility', '')
    normalized = normalized.replace('jail', '')
    normalized = normalized.replace('processing center', '')
    
    # Clean up extra whitespace and punctuation
    normalized = ' '.join(normalized.split())
    normalized = normalized.strip(' ,.-')
    
    return normalized

def find_highest_confidence_record(records: List[Dict]) -> Optional[Dict]:
    """
    Find the record with the highest confidence level among a list of records.
    
    Args:
        records: List of inspection records for a facility
        
    Returns:
        Record with highest confidence, or None if no confidence data
    """
    if not records:
        return None
    
    # Look for records with confidence_level or similarity_score
    best_record = None
    best_score = -1
    
    for record in records:
        # Try to get confidence score from various possible fields
        confidence_score = None
        
        # Check for similarity_score first
        if 'similarity_score' in record:
            confidence_score = record['similarity_score']
        # Check for confidence_level as a number
        elif 'confidence_level' in record and isinstance(record['confidence_level'], (int, float)):
            confidence_score = record['confidence_level']
        # Check for confidence_level as string that might be numeric
        elif 'confidence_level' in record and str(record['confidence_level']).replace('.', '').isdigit():
            confidence_score = float(record['confidence_level'])
        
        if confidence_score is not None and confidence_score > best_score:
            best_score = confidence_score
            best_record = record
    
    return best_record

def process_facilities_jsonl(data_file: str, facilities_csv: str, output_file: str = None):
    """
    Process facilities and add coordinates, maintaining the original JSONL format.
    
    Args:
        data_file: Path to the JSONL file with inspection data
        facilities_csv: Path to the CSV file with existing facility coordinates
        output_file: Optional output file for results
    """
    print(f"Loading inspection data from {data_file}...")
    data = load_jsonl_data(data_file)
    print(f"Loaded {len(data)} detention center records")
    
    print(f"Loading existing facilities from {facilities_csv}...")
    existing_facilities = load_facilities_csv(facilities_csv)
    print(f"Loaded {len(existing_facilities)} facilities with coordinates")
    
    # Process each detention center record
    results = []
    total_facilities = len(data)
    
    for i, center_record in enumerate(data, 1):
        detention_center = center_record.get('Detention Center', 'Unknown')
        inspections = center_record.get('Inspections', [])
        
        print(f"\n[{i}/{total_facilities}] Processing: {detention_center}")
        print(f"  Number of inspection records: {len(inspections)}")
        
        # Find the most similar facility in the CSV
        matching_facility, similarity_score = find_most_similar_facility(detention_center, existing_facilities)
        
        if matching_facility:
            print(f"  Found similar facility: {matching_facility['name']} (similarity: {similarity_score:.3f})")
            print(f"  Coordinates: {matching_facility['latitude']}, {matching_facility['longitude']}")
            
            # Add location and confidence fields to the center record
            center_record['location_latitude'] = matching_facility['latitude']
            center_record['location_longitude'] = matching_facility['longitude']
            center_record['location_address'] = f"{matching_facility['street']}, {matching_facility['city']}, {matching_facility['state']} {matching_facility['zipcode']}".strip()
            center_record['location_field_office'] = matching_facility['field_office']
            center_record['location_source'] = 'csv_facilities'
            center_record['name_similarity_score'] = similarity_score
            center_record['matched_facility_name'] = matching_facility['name']
        else:
            print(f"  No similar facility found in CSV")
            
            # Try to find coordinates from inspection records with highest confidence
            best_record = find_highest_confidence_record(inspections)
            
            if best_record and best_record.get('latitude') and best_record.get('longitude'):
                print(f"  Using coordinates from highest confidence inspection record")
                
                center_record['location_latitude'] = best_record['latitude']
                center_record['location_longitude'] = best_record['longitude']
                center_record['location_address'] = best_record.get('address', '')
                center_record['location_field_office'] = best_record.get('field_office', '')
                center_record['location_source'] = 'highest_confidence_inspection'
                center_record['name_similarity_score'] = 0.0
                center_record['matched_facility_name'] = None
                
                # Add confidence score if available
                if 'similarity_score' in best_record:
                    center_record['confidence_score'] = best_record['similarity_score']
                    center_record['confidence_source'] = 'similarity_score'
                elif 'confidence_level' in best_record:
                    center_record['confidence_score'] = best_record['confidence_level']
                    center_record['confidence_source'] = 'confidence_level'
                else:
                    center_record['confidence_score'] = None
                    center_record['confidence_source'] = None
            else:
                print(f"  No coordinates available")
                
                center_record['location_latitude'] = None
                center_record['location_longitude'] = None
                center_record['location_address'] = ''
                center_record['location_field_office'] = ''
                center_record['location_source'] = 'no_coordinates_available'
                center_record['name_similarity_score'] = 0.0
                center_record['matched_facility_name'] = None
                center_record['confidence_score'] = None
                center_record['confidence_source'] = None
        
        results.append(center_record)
    
    # Print summary
    csv_matches = sum(1 for r in results if r['location_source'] == 'csv_facilities')
    inspection_matches = sum(1 for r in results if r['location_source'] == 'highest_confidence_inspection')
    no_coords = sum(1 for r in results if r['location_source'] == 'no_coordinates_available')
    
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"Total facilities processed: {len(results)}")
    print(f"Matched with CSV facilities: {csv_matches}")
    print(f"Used highest confidence inspection: {inspection_matches}")
    print(f"No coordinates available: {no_coords}")
    print(f"{'='*60}")
    
    # Save results to file if specified
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        print(f"\nResults saved to: {output_file}")
    
    return results

def main():
    """Main function."""
    # Configuration
    data_file = "data/distilled_data/merged_by_center.jsonl"
    facilities_csv = "data/all_facilities_with_coordinates.csv"
    output_file = "facilities_with_coordinates_results.jsonl"
    
    if not os.path.exists(data_file):
        print(f"Error: Data file not found: {data_file}")
        return
    
    if not os.path.exists(facilities_csv):
        print(f"Error: Facilities CSV file not found: {facilities_csv}")
        return
    
    # Process the data
    results = process_facilities_jsonl(data_file, facilities_csv, output_file)
    
    if results:
        print("\nSample results:")
        for i, result in enumerate(results[:5], 1):  # Show first 5 results
            facility_name = result['Detention Center']
            lat = result.get('location_latitude')
            lng = result.get('location_longitude')
            source = result.get('location_source')
            similarity = result.get('name_similarity_score')
            
            print(f"\n{i}. {facility_name}")
            print(f"   Source: {source}")
            if lat and lng:
                print(f"   Coordinates: {lat}, {lng}")
            if similarity is not None:
                print(f"   Name similarity: {similarity:.3f}")
            if result.get('matched_facility_name'):
                print(f"   Matched to: {result['matched_facility_name']}")

if __name__ == "__main__":
    main()
