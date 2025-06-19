#!/usr/bin/env python3
"""
Script to process ICE arrest articles and extract geographic locations.
Uses DeepSeek API to analyze article content and Google Places API for location details.
Outputs arrests.csv with location information.
"""

import csv
import json
import time
import uuid
import requests
from typing import Dict, List, Optional, Tuple
import os
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm
import re
from urllib.parse import urlparse
import logging

# Load environment variables from .env file
load_dotenv()

# API configuration
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

# File paths
INPUT_FILE = "data/distilled_data/newsroom_reports_categorization.csv"
OUTPUT_FILE = "data/distilled_data/newsroom_incidents.csv"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_article_content(url: str) -> str:
    """Fetch and parse article content from URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Basic HTML parsing to extract text content
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract text from common content areas
        content_selectors = [
            'article', '.article-content', '.story-content', '.post-content',
            '.entry-content', '.content', 'main', '.main-content'
        ]
        
        content = ""
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                content = ' '.join([elem.get_text(strip=True) for elem in elements])
                break
        
        # If no specific content area found, get all text
        if not content:
            content = soup.get_text(strip=True)
        
        # Clean up the content
        content = re.sub(r'\s+', ' ', content)  # Replace multiple whitespace with single space
        content = content[:5000]  # Limit to first 5000 characters to save tokens
        
        return content
        
    except Exception as e:
        logger.warning(f"Failed to fetch content from {url}: {e}")
        return ""

def extract_location_with_deepseek(title: str, content: str) -> Dict:
    """Use DeepSeek API to extract location information from article."""
    
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY environment variable is required")
    
    prompt = f"""
You are a geographic location extraction expert. Analyze the following article about an ICE incident and extract the PRIMARY location where the incident most likely occurred, along with the number of people affected.

Article Title: {title}
Article Content: {content}

Extract the following information about the PRIMARY location (where the incident actually happened):
- location: The specific location name (e.g., "Downtown Los Angeles", "Port Washington Bagel Store")
- latitude: Approximate latitude coordinate (decimal degrees)
- longitude: Approximate longitude coordinate (decimal degrees) 
- city: City name
- state: State name or abbreviation
- county: County name
- zip: ZIP code (if mentioned)
- street: Street address (if mentioned)
- reported_count: Number of people arrested, detained, or otherwise affected by the incident. Use "N/A" if not applicable or not mentioned.

If any information is not available in the article, use "Unknown" for that field.

Respond with a JSON object in this exact format:
{{
  "location": "location_name",
  "latitude": "latitude_value",
  "longitude": "longitude_value", 
  "city": "city_name",
  "state": "state_name",
  "county": "county_name",
  "zip": "zip_code",
  "street": "street_address",
  "reported_count": "number_or_N/A"
}}

Focus on the PRIMARY location where the incident event occurred, not secondary locations mentioned in the article.
"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Parse JSON response
        try:
            # Extract JSON content
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                raise ValueError("Could not find valid JSON object markers")
            
            json_content = content[start_idx:end_idx + 1]
            location_data = json.loads(json_content)
            
            # Ensure all required fields are present
            required_fields = ["location", "latitude", "longitude", "city", "state", "county", "zip", "street", "reported_count"]
            for field in required_fields:
                if field not in location_data:
                    location_data[field] = "Unknown"
            
            return location_data
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Invalid JSON response from DeepSeek: {e}")
            return {
                "location": "Unknown", "latitude": "Unknown", "longitude": "Unknown",
                "city": "Unknown", "state": "Unknown", "county": "Unknown", 
                "zip": "Unknown", "street": "Unknown", "reported_count": "N/A"
            }
        
    except Exception as e:
        logger.error(f"Error calling DeepSeek API: {e}")
        return {
            "location": "Unknown", "latitude": "Unknown", "longitude": "Unknown",
            "city": "Unknown", "state": "Unknown", "county": "Unknown", 
            "zip": "Unknown", "street": "Unknown", "reported_count": "N/A"
        }

def enhance_location_with_google_places(location_data: Dict) -> Dict:
    """Use Google Places API to enhance location data with more accurate coordinates and details."""
    
    if not GOOGLE_PLACES_API_KEY:
        logger.warning("GOOGLE_PLACES_API_KEY not found, skipping Google Places enhancement")
        return location_data
    
    # Try to find the location using Google Places API
    search_query = f"{location_data['location']}, {location_data['city']}, {location_data['state']}"
    
    try:
        # Search for the place
        search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': search_query,
            'key': GOOGLE_PLACES_API_KEY
        }
        
        response = requests.get(search_url, params=params, timeout=30)
        response.raise_for_status()
        
        results = response.json()
        
        if results.get('results') and len(results['results']) > 0:
            place = results['results'][0]
            
            # Update location data with Google Places information
            if place.get('geometry', {}).get('location'):
                location_data['latitude'] = str(place['geometry']['location']['lat'])
                location_data['longitude'] = str(place['geometry']['location']['lng'])
            
            # Extract address components
            if place.get('formatted_address'):
                address_parts = place['formatted_address'].split(', ')
                
                # Try to extract city, state, zip from formatted address
                if len(address_parts) >= 2:
                    # Last part is usually state and zip
                    state_zip = address_parts[-1]
                    if ' ' in state_zip:
                        state_part, zip_part = state_zip.rsplit(' ', 1)
                        if len(zip_part) == 5 and zip_part.isdigit():
                            location_data['zip'] = zip_part
                            location_data['state'] = state_part
                        else:
                            location_data['state'] = state_zip
                    else:
                        location_data['state'] = state_zip
                    
                    # Second to last part is usually city
                    if len(address_parts) >= 3:
                        location_data['city'] = address_parts[-2]
            
            # Extract street address if available
            if place.get('formatted_address'):
                location_data['street'] = place['formatted_address']
        
    except Exception as e:
        logger.warning(f"Error calling Google Places API: {e}")
    
    return location_data

def process_arrest_articles():
    """Main function to process all articles and generate newsroom_incidents.csv."""
    
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY environment variable is required")
    
    # Read all articles from input file
    all_articles = []
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_articles.append(row)
    except FileNotFoundError:
        logger.error(f"Input file {INPUT_FILE} not found")
        return
    except Exception as e:
        logger.error(f"Error reading input file: {e}")
        return
    
    logger.info(f"Found {len(all_articles)} articles to process")
    
    # Process each article
    processed_articles = []
    
    with tqdm(total=len(all_articles), desc="Processing articles", unit="article") as pbar:
        for article in all_articles:
            try:
                # Fetch article content
                content = fetch_article_content(article['url'])
                
                # Extract location using DeepSeek
                location_data = extract_location_with_deepseek(article['title'], content)
                
                # Enhance with Google Places if available
                enhanced_location = enhance_location_with_google_places(location_data)
                
                # Create article record with all original fields plus location data
                article_record = {
                    # Original fields
                    'id': article['id'],
                    'title': article['title'],
                    'summary': article['summary'],
                    'date': article['date'],
                    'publisher': article['publisher'],
                    'scrape_date': article['scrape_date'],
                    'category': article['category'],
                    'url': article['url'],
                    # Location fields
                    'location': enhanced_location['location'],
                    'latitude': enhanced_location['latitude'],
                    'longitude': enhanced_location['longitude'],
                    'city': enhanced_location['city'],
                    'state': enhanced_location['state'],
                    'county': enhanced_location['county'],
                    'zip': enhanced_location['zip'],
                    'street': enhanced_location['street'],
                    'reported_count': enhanced_location['reported_count']
                }
                
                processed_articles.append(article_record)
                
                
            except Exception as e:
                logger.error(f"Error processing article {article.get('id', 'unknown')}: {e}")
                # Create a record with unknown values for location fields, preserving original fields
                article_record = {
                    # Original fields
                    'id': article.get('id', str(uuid.uuid4())),
                    'title': article.get('title', ''),
                    'summary': article.get('summary', ''),
                    'date': article.get('date', ''),
                    'publisher': article.get('publisher', ''),
                    'scrape_date': article.get('scrape_date', ''),
                    'category': article.get('category', ''),
                    'url': article.get('url', ''),
                    # Location fields with unknown values
                    'location': 'Unknown',
                    'latitude': 'Unknown',
                    'longitude': 'Unknown',
                    'city': 'Unknown',
                    'state': 'Unknown',
                    'county': 'Unknown',
                    'zip': 'Unknown',
                    'street': 'Unknown',
                    'reported_count': 'N/A'
                }
                processed_articles.append(article_record)
            
            pbar.update(1)
    
    # Write output CSV with all fields
    fieldnames = ['id', 'title', 'summary', 'date', 'publisher', 'scrape_date', 'category', 'url', 
                  'location', 'latitude', 'longitude', 'city', 'state', 'county', 'zip', 'street', 'reported_count']
    
    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(processed_articles)
        
        logger.info(f"Successfully processed {len(processed_articles)} articles")
        logger.info(f"Output written to {OUTPUT_FILE}")
        
    except Exception as e:
        logger.error(f"Error writing output file: {e}")

def main():
    """Main entry point."""
    logger.info("Starting article processing...")
    process_arrest_articles()
    logger.info("Article processing completed.")

if __name__ == "__main__":
    main()
