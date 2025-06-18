#!/usr/bin/env python3
"""
Script to categorize medicloud articles using DeepSeek API.
Categorizes articles into: raid, arrest, detention, protest, policy, opinion, other
"""

import csv
import json
import time
import uuid
from urllib.parse import urlparse
import requests
from typing import Dict, List, Optional, Tuple
import os
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables from .env file
load_dotenv()

# DeepSeek API configuration
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Categories as specified
CATEGORIES = ["raid", "arrest", "detention", "protest", "policy", "opinion", "other"]

# Batch size for processing
BATCH_SIZE = 20

def categorize_articles_batch(articles_batch: List[Dict]) -> List[Dict]:
    """Use DeepSeek API to categorize a batch of articles and provide publisher labels."""
    
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY environment variable is required")
    
    # Prepare the articles list for the prompt
    articles_text = ""
    for i, article in enumerate(articles_batch, 1):
        articles_text += f"""
Article {i}:
Title: {article['title']}
Description: {article['description']}
URL: {article['url']}
"""
    
    prompt = f"""
You are a content categorization expert. Analyze the following {len(articles_batch)} articles and categorize each one.

For each article, provide:
1. The category (must be one of: raid, arrest, detention, protest, policy, opinion, other)
2. The publisher name (extract from the URL or provide a proper publication name)

Categories:
- raid: Articles about ICE raids, workplace raids, immigration enforcement operations
- arrest: Articles about arrests, detentions, or apprehensions by law enforcement
- detention: Articles about detention centers, holding facilities, or prolonged custody
- protest: Articles about protests, demonstrations, marches, or civil unrest
- policy: Articles about immigration policies, laws, regulations, or government decisions
- opinion: Articles that are clearly opinion pieces, editorials, or commentary
- other: Articles that don't fit into the above categories

Articles to categorize:
{articles_text}

Respond with a JSON array where each element contains the category and publisher for the corresponding article. Format:
[
  {{"category": "category_name", "publisher": "publisher_name"}},
  {{"category": "category_name", "publisher": "publisher_name"}},
  ...
]

Ensure the array has exactly {len(articles_batch)} elements, one for each article in order.
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
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Parse JSON response
        try:
            # Extract JSON content from between first '[' and last ']'
            start_idx = content.find('[')
            end_idx = content.rfind(']')
            
            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                raise ValueError("Could not find valid JSON array markers '[' and ']'")
            
            json_content = content[start_idx:end_idx + 1]
            print(f"DeepSeek JSON response: {json_content}")
            json_response = json.loads(json_content)
            
            # Validate response structure
            if not isinstance(json_response, list) or len(json_response) != len(articles_batch):
                raise ValueError(f"Expected {len(articles_batch)} results, got {len(json_response) if isinstance(json_response, list) else 'non-list'}")
            
            # Process each result
            processed_results = []
            for i, result_item in enumerate(json_response):
                if not isinstance(result_item, dict):
                    print(f"Warning: Invalid result format for article {i+1}. Defaulting to 'other' category.")
                    processed_results.append({"category": "other", "publisher": "Unknown"})
                    continue
                
                category = result_item.get("category", "").lower()
                publisher = result_item.get("publisher", "Unknown")
                
                # Validate category
                if category not in CATEGORIES:
                    print(f"Warning: Invalid category '{category}' for article {i+1}. Defaulting to 'other'.")
                    category = "other"
                
                processed_results.append({"category": category, "publisher": publisher})
            
            return processed_results
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Invalid JSON response '{content}'. Error: {e}")
            # Return default results for all articles
            return [{"category": "other", "publisher": "Unknown"} for _ in articles_batch]
        
    except Exception as e:
        print(f"Error categorizing batch: {e}")
        # Return default results for all articles
        return [{"category": "other", "publisher": "Unknown"} for _ in articles_batch]

def process_articles(input_file: str, output_file: str, scrape_date: str = "6/18/2025"):
    """Process articles from input CSV and create categorized output CSV."""
    
    articles = []
    
    # Read input CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Filter out rows without title or URL
    valid_rows = []
    for row in rows:
        title = row.get('title', '').strip()
        url = row.get('url', '').strip()
        if title and url:
            valid_rows.append(row)
    
    # Process articles in batches with progress tracking
    total_batches = (len(valid_rows) + BATCH_SIZE - 1) // BATCH_SIZE
    
    with tqdm(total=len(valid_rows), desc="Categorizing articles", unit="article") as pbar:
        for i in range(0, len(valid_rows), BATCH_SIZE):
            batch = valid_rows[i:i + BATCH_SIZE]
            
            # Prepare batch for API call
            batch_data = []
            for row in batch:
                batch_data.append({
                    'title': row.get('title', '').strip(),
                    'description': row.get('description', '').strip(),
                    'url': row.get('url', '').strip()
                })
            
            # Categorize batch
            batch_results = categorize_articles_batch(batch_data)
            
            # Create article entries
            for j, (row, result) in enumerate(zip(batch, batch_results)):
                article = {
                    'id': str(uuid.uuid4()),
                    'title': row.get('title', '').strip(),
                    'publisher': result['publisher'],
                    'scrape_date': scrape_date,
                    'category': result['category'],
                    'url': row.get('url', '').strip()
                }
                
                articles.append(article)
                pbar.update(1)
            
            # Rate limiting - wait between batches
            time.sleep(2)
    
    # Write output CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'title', 'publisher', 'scrape_date', 'category', 'url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for article in articles:
            writer.writerow(article)
    
    print(f"Processed {len(articles)} articles. Output saved to {output_file}")
    
    # Print category distribution
    category_counts = {}
    for article in articles:
        category = article['category']
        category_counts[category] = category_counts.get(category, 0) + 1
    
    print("\nCategory distribution:")
    for category in CATEGORIES:
        count = category_counts.get(category, 0)
        print(f"  {category}: {count}")

def main():
    """Main function to run the categorization script."""
    
    # File paths
    input_file = "data/mediacloud_articles.csv"
    output_file = "data/articles.csv"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found.")
        return
    
    # Check if API key is set
    if not DEEPSEEK_API_KEY:
        print("Error: DEEPSEEK_API_KEY environment variable is not set.")
        print("Please set it with: export DEEPSEEK_API_KEY='your-api-key-here'")
        return
    
    print("Starting article categorization...")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Categories: {', '.join(CATEGORIES)}")
    print()
    
    try:
        process_articles(input_file, output_file)
        print("\nCategorization completed successfully!")
        
    except Exception as e:
        print(f"Error during processing: {e}")

if __name__ == "__main__":
    main()
