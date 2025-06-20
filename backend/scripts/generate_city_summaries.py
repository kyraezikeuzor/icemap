#!/usr/bin/env python3
"""
Script to pre-generate immigration activity summaries for major cities and save to JSON.
This way, city summaries can be loaded instantly without API calls when users click city markers.
"""

import os
import sys
import json
import logging
import requests
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path so we can import modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

# Import the functions from city_summaries.py
sys.path.append(str(project_root / "backend"))
from api.city_summaries import load_city_data, generate_summary_with_deepseek

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set output paths
OUTPUT_DIR = project_root / "frontend" / "public"
OUTPUT_FILE = OUTPUT_DIR / "city_summaries.json"

# List of top 25 cities to generate summaries for
CITIES = [
    "New York",
    "Los Angeles",
    "Chicago",
    "Houston",
    "Phoenix",
    "Philadelphia",
    "San Antonio",
    "San Diego",
    "Dallas",
    "Jacksonville",
    "Fort Worth",
    "San Jose",
    "Austin",
    "Charlotte",
    "Columbus",
    "Indianapolis",
    "San Francisco",
    "Seattle",
    "Denver",
    "Oklahoma City",
    "Nashville",
    "Washington",
    "El Paso",
    "Las Vegas",
    "Boston"
]

def generate_all_city_summaries():
    """Generate summaries for all cities and save to a JSON file"""
    logger.info(f"Generating summaries for {len(CITIES)} cities")
    
    # Dictionary to hold all city summaries
    all_summaries = {}
    
    # Generate summary for each city
    for i, city in enumerate(CITIES):
        logger.info(f"[{i+1}/{len(CITIES)}] Generating summary for {city}")
        
        try:
            # Load data related to the city
            city_data = load_city_data(city)
            logger.info(f"Loaded data for {city}: {len(city_data['arrests'])} arrests, {len(city_data['articles'])} articles, {len(city_data['incidents'])} incidents")
            
            # Generate summary using Deepseek
            result = generate_summary_with_deepseek(city, city_data)
            
            if "summary" in result and not result.get("error"):
                all_summaries[city] = {
                    "summary": result["summary"],
                    "generated": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                logger.info(f"✓ Successfully generated summary for {city}")
            else:
                error_msg = result.get("error", "Unknown error")
                logger.warning(f"✗ Failed to generate summary for {city}: {error_msg}")
                all_summaries[city] = {
                    "summary": f"No immigration activity summary available for {city}.",
                    "error": error_msg,
                    "generated": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            
            # Add a small delay to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error generating summary for {city}: {e}")
            all_summaries[city] = {
                "summary": f"No immigration activity summary available for {city}.",
                "error": str(e),
                "generated": time.strftime("%Y-%m-%d %H:%M:%S")
            }
    
    # Ensure the output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save all summaries to a JSON file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_summaries, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(all_summaries)} city summaries to {OUTPUT_FILE}")
    
    return all_summaries

if __name__ == "__main__":
    generate_all_city_summaries()
