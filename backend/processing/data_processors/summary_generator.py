#!/usr/bin/env python3
"""
Summary Generator for Detention Center Inspection Data

This script processes each detention center in facilities_with_coordinates_results.jsonl
and generates investigative journalist-style summaries using the DeepSeek API.
The summaries are appended to the existing data and output to a new JSONL file.
"""

import json
import os
import logging
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

# DeepSeek API configuration
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# The prompt template for generating summaries
SUMMARY_PROMPT = """You are an investigative journalist.  
Using the inspection excerpts below, write a vivid, front-page style summary **<150 words>** that:

• If there are significant findings or violations: Lead with the single worst recurring issue, weave in telling quotes or numbers, name 2–3 secondary issues, and end with a one-sentence outlook about conditions.
• If there are few or no detailed findings (minimal inspection text): Lead with the positive inference that the facility appears to be operating within standards, mention the inspection process itself, and note that limited findings suggest compliance with regulations.

Then output a JSON object with:  
  "summary": <your paragraph>,  
  "score": <1–10 number following the rubric>.

### Scoring rubric (embed, do not output):  
Start at 10, subtract:  
  • 3 pts for each critical issue repeated ≥2 times (medical neglect, suicide risk, excessive force, food safety).  
  • 1 pt for each major issue appearing once.  
Add +1 if the most recent inspection shows clear resolution of every critical item.
**IMPORTANT**: If inspection data is minimal or shows few/no detailed findings, this typically indicates good compliance - score accordingly (8-10 range).

### Inspection data
<<<PASTE INSPECTION TEXT>>>
"""

# The prompt template for generating summaries with minimal inspection data
MINIMAL_DATA_PROMPT = """You are an investigative journalist covering detention center oversight.  
The inspection data below shows minimal findings or violations. Write a balanced, front-page style summary **<150 words>** that:

• Leads with the positive inference that limited inspection findings typically indicate compliance with detention standards.
• Mentions the inspection process and regulatory oversight framework.
• Notes that the absence of detailed findings or violation reports suggests the facility is operating within acceptable parameters.
• Acknowledges that while limited data makes comprehensive assessment difficult, what is available suggests good standing.
• Ends with a measured outlook about the facility's apparent compliance status.

**IMPORTANT**: Take a positive inference from the lack of detailed findings or violation reports - this usually means the facility passed inspection without significant issues.

Then output a JSON object with:  
  "summary": <your paragraph>,  
  "score": <8-10 number reflecting good compliance>.

### Scoring guidance (embed, do not output):  
Score 8-10 for facilities with minimal findings or violations, as this typically indicates good compliance with detention center standards and regulations.

### Inspection data
<<<PASTE INSPECTION TEXT>>>
"""


def extract_inspection_text(inspections: List[Dict]) -> str:
    """
    Extract and format inspection text from the inspections data.
    
    Args:
        inspections: List of inspection dictionaries
        
    Returns:
        Formatted inspection text for the prompt
    """
    if not inspections:
        return "No inspection data available."
    
    inspection_texts = []
    has_any_detailed_findings = False
    
    for inspection in inspections:
        # Extract key fields that contain detailed information
        key_fields = [
            ("SAFETY", inspection.get("SAFETY", "N/A")),
            ("SECURITY", inspection.get("SECURITY", "N/A")),
            ("CARE", inspection.get("CARE", "N/A")),
            ("ACTIVITIES", inspection.get("ACTIVITIES", "N/A")),
            ("JUSTICE", inspection.get("JUSTICE", "N/A")),
            ("CONCLUSION", inspection.get("CONCLUSION", "N/A"))
        ]
        
        # Build inspection summary
        inspection_summary = f"Inspection Date: {inspection.get('Inspection Date', 'Unknown')}\n"
        inspection_summary += f"Inspection Type: {inspection.get('Inspection Type', 'Unknown')}\n"
        
        # Add detailed findings
        has_detailed_findings = False
        for field_name, field_value in key_fields:
            if field_value and field_value != "N/A" and len(str(field_value).strip()) > 10:
                inspection_summary += f"{field_name}: {field_value}\n"
                has_detailed_findings = True
                has_any_detailed_findings = True
        
        # If no detailed findings but inspection was conducted, note this
        if not has_detailed_findings:
            inspection_summary += "NOTE: No detailed findings or violations were documented in this inspection.\n"
        
        inspection_texts.append(inspection_summary)
    
    # Add overall context about the facility's compliance status
    if not has_any_detailed_findings and len(inspections) > 0:
        combined_text = "\n---\n".join(inspection_texts)
        combined_text += f"\n\nOVERALL ASSESSMENT: This facility has undergone {len(inspections)} inspection(s). The absence of detailed findings or violation reports typically indicates compliance with detention center standards and regulations."
    else:
        combined_text = "\n---\n".join(inspection_texts)
    
    return combined_text


def has_minimal_inspection_data(inspections: List[Dict]) -> bool:
    """
    Determine if the facility has minimal inspection data based on textual findings.
    
    Args:
        inspections: List of inspection dictionaries
        
    Returns:
        True if minimal inspection data, False otherwise
    """
    if not inspections:
        return True
    
    # Check if there are detailed textual findings in any inspection
    has_detailed_findings = False
    for inspection in inspections:
        for field in ['SAFETY', 'SECURITY', 'CARE', 'ACTIVITIES', 'JUSTICE', 'CONCLUSION']:
            field_value = inspection.get(field)
            if field_value and field_value != "N/A" and len(str(field_value).strip()) > 10:
                has_detailed_findings = True
                break
        if has_detailed_findings:
            break
    
    return not has_detailed_findings


def generate_summary_with_deepseek(inspection_text: str, facility_name: str, inspections: List[Dict] = None) -> Dict:
    """
    Generate a summary using the DeepSeek API.
    
    Args:
        inspection_text: Formatted inspection text
        facility_name: Name of the detention center
        inspections: List of inspection dictionaries (for determining if minimal data)
        
    Returns:
        Dictionary containing summary and score
    """
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY environment variable is required")
    
    # Determine if this facility has minimal inspection data
    is_minimal = has_minimal_inspection_data(inspections) if inspections else False
    
    # Use appropriate prompt based on data availability
    if is_minimal:
        prompt = MINIMAL_DATA_PROMPT.replace("<<<PASTE INSPECTION TEXT>>>", inspection_text)
    else:
        prompt = SUMMARY_PROMPT.replace("<<<PASTE INSPECTION TEXT>>>", inspection_text)
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        content = response.json()["choices"][0]["message"]["content"]
        
        # Extract JSON from the response
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            logger.warning(f"Could not find JSON in DeepSeek response for {facility_name}")
            return {"summary": "Unable to generate summary due to API response format.", "score": 5}
        
        json_content = content[json_start:json_end]
        result = json.loads(json_content)
        
        # Validate the response structure
        if "summary" not in result or "score" not in result:
            logger.warning(f"Invalid response structure from DeepSeek for {facility_name}")
            return {"summary": "Unable to generate summary due to invalid response structure.", "score": 5}
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from DeepSeek for {facility_name}: {e}")
        return {"summary": "Unable to generate summary due to JSON parsing error.", "score": 5}
    except requests.RequestException as e:
        logger.error(f"Error calling DeepSeek API for {facility_name}: {e}")
        return {"summary": "Unable to generate summary due to API error.", "score": 5}
    except Exception as e:
        logger.error(f"Unexpected error generating summary for {facility_name}: {e}")
        return {"summary": "Unable to generate summary due to unexpected error.", "score": 5}


def process_facility_record(record: Dict) -> Dict:
    """
    Process a single facility record and add summary data.
    
    Args:
        record: Single facility record from JSONL
        
    Returns:
        Updated record with summary data
    """
    facility_name = record.get("Detention Center", "Unknown Facility")
    inspections = record.get("Inspections", [])
    
    # Check if this facility has minimal inspection data
    is_minimal = has_minimal_inspection_data(inspections)
    if is_minimal:
        logger.info(f"Processing {facility_name} with minimal inspection data - using positive inference approach")
    
    # Extract inspection text
    inspection_text = extract_inspection_text(inspections)
    
    # Generate summary
    summary_data = generate_summary_with_deepseek(inspection_text, facility_name, inspections)
    
    # Add summary data to the record
    record["generated_summary"] = summary_data["summary"]
    record["summary_score"] = summary_data["score"]
    record["minimal_data_flag"] = is_minimal  # Add flag for tracking
    
    return record


def process_jsonl_file(input_file: str, output_file: str, start_from: int = 0):
    """
    Process the entire JSONL file and generate summaries.
    
    Args:
        input_file: Path to input JSONL file
        output_file: Path to output JSONL file
        start_from: Index to start processing from (for resuming)
    """
    if not DEEPSEEK_API_KEY:
        print("Error: DEEPSEEK_API_KEY environment variable is not set.")
        print("Please set it with: export DEEPSEEK_API_KEY='your-api-key-here'")
        return
    
    # Read all records
    with open(input_file, 'r', encoding='utf-8') as f:
        records = [json.loads(line.strip()) for line in f if line.strip()]
    
    total_records = len(records)
    print(f"Found {total_records} facility records to process")
    
    if start_from >= total_records:
        print(f"Start index {start_from} >= total records {total_records}, nothing to do.")
        return
    
    # Process records with progress bar
    processed_records = []
    
    for i, record in enumerate(tqdm(records[start_from:], 
                                   desc="Processing facilities", 
                                   unit="facility",
                                   initial=start_from)):
        try:
            processed_record = process_facility_record(record)
            processed_records.append(processed_record)
            
            # Log progress every 10 records
            if (i + start_from + 1) % 10 == 0:
                logger.info(f"Processed {i + start_from + 1}/{total_records} facilities")
                
        except Exception as e:
            logger.error(f"Error processing facility {record.get('Detention Center', 'Unknown')}: {e}")
            # Add the original record without summary data
            record["generated_summary"] = "Error occurred during processing."
            record["summary_score"] = 5
            processed_records.append(record)
    
    # Write processed records to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        for record in processed_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"Successfully processed {len(processed_records)} facilities")
    print(f"Output written to: {output_file}")


def main():
    """Main function to run the summary generator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate summaries for detention center inspection data")
    parser.add_argument("--input", "-i", 
                       default="data/distilled_data/facilities_with_coordinates_results.jsonl",
                       help="Input JSONL file path")
    parser.add_argument("--output", "-o", 
                       default="data/distilled_data/facilities_with_coordinates_results.jsonl",
                       help="Output JSONL file path")
    parser.add_argument("--start-from", "-s", 
                       type=int, default=0,
                       help="Start processing from this index (for resuming)")
    
    args = parser.parse_args()
    
    # Find the icemap root directory (3 levels up from this script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icemap_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    
    # Resolve paths relative to icemap root
    input_file = os.path.join(icemap_root, args.input)
    output_file = os.path.join(icemap_root, args.output)
    
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        return
    
    print(f"Processing: {input_file}")
    print(f"Output: {output_file}")
    print(f"Starting from index: {args.start_from}")
    
    process_jsonl_file(input_file, output_file, args.start_from)


if __name__ == "__main__":
    main()
