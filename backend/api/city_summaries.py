#!/usr/bin/env python3
"""
API endpoint to generate immigration activity summaries for major cities using Deepseek
"""

import os
import sys
import csv
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API configuration
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Add the project root to the path so we can import modules
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# Set up Flask app
app = Flask(__name__)
# Allow cross-origin requests with explicit origins
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://localhost:3001"]}}, supports_credentials=True)

# Data paths
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
ARRESTS_FILE = DATA_DIR / "distilled_data" / "arrests.csv"
ARTICLES_FILE = DATA_DIR / "distilled_data" / "articles.csv"
MEDIACLOUD_ARTICLES_FILE = DATA_DIR / "mediacloud_articles.csv"
INCIDENTS_FILE = DATA_DIR / "distilled_data" / "aggregated_incidents.csv"

# Cache for city summaries (city_name -> {"summary": text, "timestamp": datetime})
SUMMARY_CACHE = {}
CACHE_EXPIRY = timedelta(hours=24)  # Refresh summaries every 24 hours

def load_city_data(city_name):
    """
    Load recent immigration data related to the specified city
    """
    city_data = {
        "arrests": [],
        "articles": [],
        "incidents": []
    }
    
    city_name_lower = city_name.lower()
    
    # Load arrests data with city mentions
    if ARRESTS_FILE.exists():
        try:
            with open(ARRESTS_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    location = row.get('location', '').lower()
                    description = row.get('description', '').lower()
                    if city_name_lower in location or city_name_lower in description:
                        city_data["arrests"].append(row)
        except Exception as e:
            logger.error(f"Error loading arrests data: {e}")
    
    # Load articles data with city mentions
    if ARTICLES_FILE.exists():
        try:
            with open(ARTICLES_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    title = row.get('title', '').lower()
                    description = row.get('description', '').lower()
                    if city_name_lower in title or city_name_lower in description:
                        city_data["articles"].append(row)
        except Exception as e:
            logger.error(f"Error loading articles data: {e}")
    
    # If we don't have articles from the distilled data, try mediacloud articles
    if not city_data["articles"] and MEDIACLOUD_ARTICLES_FILE.exists():
        try:
            with open(MEDIACLOUD_ARTICLES_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    title = row.get('title', '').lower()
                    description = row.get('description', '').lower()
                    if city_name_lower in title or city_name_lower in description:
                        city_data["articles"].append(row)
        except Exception as e:
            logger.error(f"Error loading mediacloud articles data: {e}")
    
    # Load incidents data with city mentions
    if INCIDENTS_FILE.exists():
        try:
            with open(INCIDENTS_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    location = row.get('location', '').lower()
                    title = row.get('title', '').lower()
                    if city_name_lower in location or city_name_lower in title:
                        city_data["incidents"].append(row)
        except Exception as e:
            logger.error(f"Error loading incidents data: {e}")
    
    return city_data

def generate_summary_with_deepseek(city_name, city_data):
    """
    Generate a summary of immigration activity for a city using Deepseek API
    """
    if not DEEPSEEK_API_KEY:
        logger.error("DEEPSEEK_API_KEY environment variable is required")
        return {
            "error": "Deepseek API key is missing"
        }
    
    # Check if we have data to summarize
    total_items = len(city_data["arrests"]) + len(city_data["articles"]) + len(city_data["incidents"])
    
    if total_items == 0:
        return {
            "summary": f"No recent immigration activity data found for {city_name}."
        }
    
    # Build the prompt with relevant data
    prompt = f"""
    Generate a concise summary of recent immigration enforcement activity in {city_name}. 

    Available data:
    - {len(city_data["arrests"])} arrest records
    - {len(city_data["articles"])} news articles
    - {len(city_data["incidents"])} reported incidents

    Some recent data points:
    """
    
    # Add some sample details from each data type
    for data_type in ["arrests", "articles", "incidents"]:
        items = city_data[data_type][:3]  # Take up to 3 items of each type
        for item in items:
            if data_type == "arrests":
                date = item.get("date", "unknown date")
                details = item.get("description", "")
                prompt += f"- Arrest ({date}): {details}\n"
            elif data_type == "articles":
                date = item.get("date", "unknown date")
                title = item.get("title", "")
                prompt += f"- News ({date}): {title}\n"
            elif data_type == "incidents":
                date = item.get("date", "unknown date")
                title = item.get("title", "")
                prompt += f"- Incident ({date}): {title}\n"
    
    prompt += "\nProvide a concise (3-4 sentences) summary of immigration enforcement trends and activities in this city. If there is minimal data, explain that there is limited information available."
    
    try:
        # Prepare the API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 300
        }
        
        # Call the Deepseek API
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        response_data = response.json()
        
        # Extract the generated summary
        if "choices" in response_data and len(response_data["choices"]) > 0:
            summary = response_data["choices"][0]["message"]["content"].strip()
            return {
                "summary": summary
            }
        else:
            logger.warning(f"Unexpected response format from Deepseek API: {response_data}")
            return {
                "error": "Failed to generate summary: unexpected API response format"
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Deepseek API: {e}")
        return {
            "error": f"Failed to generate summary: API request error"
        }
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return {
            "error": f"Failed to generate summary: {str(e)}"
        }

@app.route('/api/city_summary/<city_name>', methods=['GET'])
def get_city_summary(city_name):
    """
    API endpoint to get a summary of immigration activity for a specific city
    """
    try:
        logger.info(f"Received request for city summary: {city_name}")
        
        # Normalize city name to ensure consistent caching and matching
        normalized_city_name = city_name.strip()
        
        # Check cache first
        now = datetime.now()
        if normalized_city_name in SUMMARY_CACHE:
            cache_entry = SUMMARY_CACHE[normalized_city_name]
            # If the cache entry is still valid, return it
            if now - cache_entry["timestamp"] < CACHE_EXPIRY:
                logger.info(f"Returning cached summary for {normalized_city_name}")
                return jsonify({"city": normalized_city_name, "summary": cache_entry["summary"]})
        
        # Load data related to the city
        city_data = load_city_data(normalized_city_name)
        logger.info(f"Loaded data for {normalized_city_name}: {len(city_data['arrests'])} arrests, {len(city_data['articles'])} articles, {len(city_data['incidents'])} incidents")
        
        # Generate summary using Deepseek
        result = generate_summary_with_deepseek(normalized_city_name, city_data)
        
        # Cache the result if successful
        if "summary" in result and not result.get("error"):
            SUMMARY_CACHE[normalized_city_name] = {
                "summary": result["summary"],
                "timestamp": now
            }
            logger.info(f"Generated and cached new summary for {normalized_city_name}")
        
        # Return the result, ensuring city name is consistent
        return jsonify({"city": normalized_city_name, **result})
        
    except Exception as e:
        logger.error(f"Error processing request for {city_name}: {e}")
        return jsonify({
            "city": city_name,
            "error": f"Failed to process request: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001)
