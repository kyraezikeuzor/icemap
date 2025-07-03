# ice_agent/app.py
"""
ICEAgent – Model-Context-Protocol (MCP) server
=============================================
Processes a continuous CSV-like stream of news-article metadata,
enriches each record with geotags / categories / publisher info,
and publishes a canonical JSON article to downstream storage
*only* if the entry is (1) relevant and (2) sufficient.

Exposed as a FastAPI service that speaks the MCP wire format.

Author: Jack Vu  •  Date: 2025-06-25
"""

from __future__ import annotations

import csv
import io
import json
import os
import requests
import time
from datetime import datetime
from typing import Callable, Iterable, Optional, Literal
from newspaper import Article
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------------------------------------------------------------------------
# ───────────────────────────  CONFIG  ───────────────────────────────────────
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ICEAgent (MCP)",
    version="0.0.1-skeleton",
    description="Autonomous agent for ICE-related news ingestion",
)

# MCP constants (adapt as your org's spec evolves)
MCP_TYPE = "application/vnd.mcp.v1+json"
MCP_CTX  = "https://example.org/mcp"

# DeepSeek API configuration
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

ARTICLES_API = os.getenv("ARTICLES_API")        # e.g. https://abcd1234.execute-api.us-east-1.amazonaws.com/prod/article
ARTICLES_API_KEY = os.getenv("ARTICLES_API_KEY")  # API key for the articles endpoint

# New API endpoints for getting unprocessed articles and marking as processed
ARTICLES_GET_API = os.getenv("ARTICLES_GET_API")  # API to get unprocessed articles
ARTICLES_PROCESS_MARK_API = os.getenv("ARTICLES_PROCESS_MARK_API")  # API to mark articles as processed

# Google Places API configuration
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

# CSV file path
CSV_FILE_PATH = "/Users/jackvu/Desktop/latex_projects/icemap/data/mediacloud_report.csv"

# ---------------------------------------------------------------------------
# ────────────────────────────  TOOL STUBS  ─────────────────────────────────-
# ---------------------------------------------------------------------------

# Type aliases make dependency-injection tidy
ToolFunc        = Callable[..., object]
ArticlePayload  = dict[str, object]

# Each real tool can be swapped in via DI / import-string look-up later.
def parseAddressInfo(payload: ArticlePayload) -> ArticlePayload:
    """Extract address and location information from article text."""
    if "text" not in payload or not payload["text"]:
        return payload
        
    if not DEEPSEEK_API_KEY:
        return payload
        
    prompt = """Extract location information from this article text. Return a JSON object with these fields:
- city: city name
- state: state/province name  
- country: country name
- address: full address if mentioned
- location_details: any other location details mentioned

Article text: {text}

Return only valid JSON:"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": prompt.format(text=payload["text"][:1500])  # Limit text length
            }
        ],
        "temperature": 0.1,
        "max_tokens": 200
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Try to parse JSON response
        try:
            location_data = json.loads(content)
            
            # Add extracted location info to payload
            payload["parsed_location"] = {
                "city": location_data.get("city", ""),
                "state": location_data.get("state", ""),
                "country": location_data.get("country", ""),
                "address": location_data.get("address", ""),
                "location_details": location_data.get("location_details", "")
            }
            
        except json.JSONDecodeError:
            # If JSON parsing fails, add empty location info
            payload["parsed_location"] = {
                "city": "",
                "state": "",
                "country": "",
                "address": "",
                "location_details": ""
            }
            
    except Exception:
        # If API call fails, add empty location info
        payload["parsed_location"] = {
            "city": "",
            "state": "",
            "country": "",
            "address": "",
            "location_details": ""
        }
    
    return payload

def addPublisher(url: str) -> str:
    """Return canonical publisher string using DeepSeek."""
    if not DEEPSEEK_API_KEY:
        return "Unknown Publisher"
        
    prompt = "Extract publisher name from URL. Return ONLY the publisher name, no other text: {url}"
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": prompt.format(url=url)
            }
        ],
        "temperature": 0.1,
        "max_tokens": 15
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        publisher = result["choices"][0]["message"]["content"].strip()
        
        return publisher if publisher else "Unknown Publisher"
        
    except Exception:
        return "Unknown Publisher"

def categorize(text: str) -> str:
    """Return article category label using DeepSeek classification."""
    if not DEEPSEEK_API_KEY:
        # If no API key, fail safe by returning unknown
        return "unknown"
        
    prompt = """You are a helpful assistant that categorizes news articles related to ICE (Immigration and Customs Enforcement) activity.

    Analyze the following article text and classify it into exactly one of these categories:

    - "raid": Articles about ICE conducting raids, workplace raids, or surprise enforcement operations
    - "arrest": Articles about individual arrests, detentions, or apprehensions by ICE
    - "detention": Articles about detention centers, conditions, releases, or detention policies
    - "protest": Articles about protests, demonstrations, or public opposition to ICE actions
    - "policy": Articles about ICE policies, regulations, legal changes, or administrative decisions
    - "opinion": Opinion pieces, editorials, or commentary about ICE
    - "unknown": Articles that don't clearly fit into the above categories

    Article text: {text}

    Respond with ONLY the category name (raid, arrest, detention, protest, policy, opinion, or unknown):"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": prompt.format(text=text[:2000])  # Limit text length to avoid token limits
            }
        ],
        "temperature": 0.1,
        "max_tokens": 20
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip().lower()
        
        # Validate the response is one of our expected categories
        valid_categories = {"raid", "arrest", "detention", "protest", "policy", "opinion", "unknown"}
        
        # Clean up the response and check if it's valid
        category = content.strip()
        if category in valid_categories:
            return category
        else:
            # If response isn't a valid category, return unknown
            return "unknown"
            
    except Exception:
        # On any error, fail safe by returning unknown
        return "unknown"

def extractAddressFromText(text: str) -> Optional[str]:
    """Extract the most specific address/location from article text using DeepSeek."""
    if not DEEPSEEK_API_KEY:
        return None
        
    prompt = """Extract the most specific location mentioned in this text. Return only the location name (city, address, or landmark): {text}. Return ONLY The location information, no other text. If there is no specific location mentioned (like national policy news), return "None"."""
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": prompt.format(text=text[:1000])  # Limit text length
            }
        ],
        "temperature": 0.1,
        "max_tokens": 50
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        location_query = result["choices"][0]["message"]["content"].strip()
        
        # Check if DeepSeek returned "None" or similar
        if not location_query or location_query.lower() in ["none", "unknown", "not mentioned", "no location", "n/a"]:
            print("No specific location found and not national policy news")
            return None
            
        return location_query
            
    except Exception as e:
        print(f"Error extracting address: {e}")
        return None

def sanitize_address(address: str, article_text: str = "") -> str:
    """Clean and clarify address information using DeepSeek before geocoding."""
    if not DEEPSEEK_API_KEY:
        return address
        
    if not address:
        return address
        
    prompt = """You are a helpful assistant that clarifies and standardizes location names for geocoding.

Given a location name and optional article context, return a clear, specific address that would work well with Google Maps geocoding.

Examples:
- "Washington" → "Washington DC, USA" (if no state specified)
- "LA" → "Los Angeles, CA, USA"
- "NYC" → "New York City, NY, USA"
- "Texas" → "Texas, USA"
- "Downtown" → "Downtown, [city from context], USA"

Location: {address}
Article context: {context}

Return ONLY the clarified address, no other text. If the location is already clear and specific, return it as-is."""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": prompt.format(
                    address=address,
                    context=article_text[:500] if article_text else "No additional context"
                )
            }
        ],
        "temperature": 0.1,
        "max_tokens": 100
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        sanitized_address = result["choices"][0]["message"]["content"].strip()
        
        # Remove quotes if present
        sanitized_address = sanitized_address.strip('"\'')
        
        print(f"Address sanitization: '{address}' → '{sanitized_address}'")
        return sanitized_address
        
    except Exception as e:
        print(f"Error sanitizing address '{address}': {e}")
        return address

def geoTag(address: str) -> Optional[tuple[float, float]]:
    """Extract (lat, lon) from address string using Google Places API."""
    if not GOOGLE_PLACES_API_KEY:
        return None
        
    if not address:
        return None
        
    try:
        # Use Google Places API to get coordinates
        places_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        params = {
            "input": address,
            "inputtype": "textquery",
            "fields": "geometry/location,formatted_address",
            "key": GOOGLE_PLACES_API_KEY
        }
        
        places_response = requests.get(places_url, params=params, timeout=10)
        places_response.raise_for_status()
        
        places_data = places_response.json()
        
        if places_data.get("status") == "OK" and places_data.get("candidates"):
            candidate = places_data["candidates"][0]
            location = candidate["geometry"]["location"]
            returned_address = candidate.get("formatted_address", "")
            
            # Simple confidence check based on input length
            confidence = "high" if len(address) >= 5 else "low"
            print(f"Geocoding {confidence} confidence: input='{address}' -> returned='{returned_address}'")
            
            return (location["lat"], location["lng"])
            
    except Exception as e:
        print(f"Geocoding error for '{address}': {e}")
    
    return None

def getText(url: str) -> str:
    """Download & return raw article text for the URL."""
    article = Article(url)
    article.download()
    article.parse()
    return article.text

def judgeRelevance(text: str) -> bool:
    """True iff article is ICE-relevant."""
    if not DEEPSEEK_API_KEY:
        # If no API key, fail safe by returning false
        return False
        
    prompt = """You are a helpful assistant that determines if news articles are relevant to ICE (Immigration and Customs Enforcement) activity.

    Analyze the following article text and respond with ONLY "true" if it discusses ICE operations, policies, actions or news, or "false" if it is unrelated to ICE:

    Article text: {text}

    Response (true/false only):"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": prompt.format(text=text)
            }
        ],
        "temperature": 0.1,
        "max_tokens": 50
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Extract just true/false and handle case
        result = content.lower()
        if result == "true":
            return True
        elif result == "false": 
            return False
        else:
            # If response isn't clearly true/false, assume false
            return False
            
    except Exception:
        # On any error, fail safe by returning false
        return False

def judgeEntrySufficiency(payload: ArticlePayload) -> bool:
    """True iff payload contains all mandatory fields for addArticle."""
    required = {"title", "date", "url", "coordinates", "category", "publisher"}
    return required.issubset(payload.keys())

def getUnprocessedArticles() -> str:
    """Get unprocessed articles from the API as CSV string."""
    api_url = ARTICLES_GET_API
    
    if not api_url:
        raise RuntimeError("ARTICLES_GET_API environment variable is required")
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        # Parse JSON response and extract CSV from body field
        json_data = response.json()
        if json_data.get("statusCode") == 200:
            csv_data = json_data.get("body", "")
            print(f"API Response Status: {json_data.get('statusCode')}")
            print(f"API Response Headers: {json_data.get('headers', {})}")
            return csv_data
        else:
            raise RuntimeError(f"API returned status code: {json_data.get('statusCode')}")
            
    except Exception as e:
        raise RuntimeError(f"Failed to get unprocessed articles: {e}")

from urllib.parse import urlencode

# markArticleAsProcessed (client side)
def markArticleAsProcessed(url: str) -> None:
    resp = requests.post(
        ARTICLES_PROCESS_MARK_API,
        json={"url": url},                  # <-- body, not params
        headers={"x-api-key": ARTICLES_API_KEY},
        timeout=10,
    )
    resp.raise_for_status()                # HTTP layer
    payload = resp.json()
    if payload.get("statusCode", 200) != 200:
        raise RuntimeError(f"mark failed: {payload}")


def addArticle(payload: ArticlePayload) -> None:
    """POST article to the putArticle API Gateway endpoint."""
    # Get API key and URL from environment variables
    api_key = ARTICLES_API_KEY
    api_url = ARTICLES_API
    
    if not api_url:
        raise RuntimeError("ARTICLES_API environment variable is required")
    
    if not api_key:
        raise RuntimeError("ARTICLES_API_KEY environment variable is required")

    # Headers
    headers = {"Content-Type": "application/json"}
    headers["x-api-key"] = api_key

    resp = requests.post(api_url, headers=headers, json=payload, timeout=10)
    if not resp.ok:
        # log & raise so caller can decide to retry / DLQ
        raise RuntimeError(f"putArticle failed → {resp.status_code}: {resp.text}")

# ---------------------------------------------------------------------------
# ──────────────────────────  DATA MODELS  ──────────────────────────────────
# ---------------------------------------------------------------------------

class CSVRecord(BaseModel):
    """One row straight from the incoming CSV stream."""
    title: str
    description: str
    date: datetime
    url: str

class MCPEnvelope(BaseModel):
    """
    Generic MCP request envelope.

    The *body* here is assumed to be a CSV string with header:
    title,date,url
    """
    type: Literal[MCP_TYPE] = MCP_TYPE
    context: Literal[MCP_CTX] = MCP_CTX
    body: str

class MCPResponse(BaseModel):
    """Minimal MCP response with status and (optional) diagnostics."""
    type: Literal[MCP_TYPE] = MCP_TYPE
    context: Literal[MCP_CTX] = MCP_CTX
    status: str  # "ok" | "partial" | "error"
    accepted: int = 0
    ignored:  int = 0
    detail: Optional[str] = None

# ---------------------------------------------------------------------------
# ────────────────────────────  PIPELINE  ───────────────────────────────────
# ---------------------------------------------------------------------------

def read_csv_file(file_path: str, max_articles: int = 100) -> list[CSVRecord]:
    """Read the first N articles from the CSV file."""
    records = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for i, row in enumerate(reader):
                if i >= max_articles:
                    break
                    
                # Parse the date string to datetime
                try:
                    date_obj = datetime.strptime(row['date'], '%Y-%m-%d')
                except ValueError:
                    # If date parsing fails, use current date
                    date_obj = datetime.now()
                
                record = CSVRecord(
                    title=row['title'],
                    description=row.get('description', ''),
                    date=date_obj,
                    url=row['url']
                )
                records.append(record)
                
    except FileNotFoundError:
        print(f"❌ Error: CSV file not found at {file_path}")
        return []
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return []
    
    return records

def process_csv_articles(
    max_articles: int = 10,
    *,
    # Inject the tool chain so tests can monkey-patch
    fetch_text: ToolFunc = getText,
    relevance:  ToolFunc = judgeRelevance,
    extract_addr: ToolFunc = extractAddressFromText,
    sanitize_addr: ToolFunc = sanitize_address,
    tag_coords: ToolFunc = geoTag,
    classify:   ToolFunc = categorize,
    canonical_pub: ToolFunc = addPublisher,
    enrich_addr: ToolFunc = parseAddressInfo,
    sufficiency: ToolFunc = judgeEntrySufficiency,
    persist: ToolFunc = addArticle,
) -> tuple[int, int]:
    """Process articles from CSV file with live status reporting."""
    accepted = ignored = 0
    
    print(f"Starting ICE Agent - Processing first {max_articles} articles from CSV")
    print(f"Reading from: {CSV_FILE_PATH}")
    print("=" * 80)
    
    # Read articles from CSV
    records = read_csv_file(CSV_FILE_PATH, max_articles)
    
    if not records:
        print("No articles found in CSV file")
        return 0, 0
    
    print(f"Found {len(records)} articles to process")
    print("=" * 80)
    
    for i, rec in enumerate(records, 1):
        print(f"\n{'='*60}")
        print(f"Processing article {i}/{len(records)}")
        print(f"Title: {rec.title}")
        print(f"Date: {rec.date}")
        print(f"URL: {rec.url}")
        print(f"{'='*60}")
        
        try:
            # Step 1: Fetch article text
            print("Fetching article text...")
            text = fetch_text(rec.url)
            if not text:
                print("Failed to fetch article text")
                ignored += 1
                continue
            
            # Show first 200 characters of text
            text_preview = text[:200].replace('\n', ' ').strip()
            print(f"Article text preview: {text_preview}...")
            print(f"Text length: {len(text)} characters")
            
            # Step 2: Check relevance
            print("\nChecking relevance...")
            is_relevant = relevance(text)
            if not is_relevant:
                print("Article not relevant to ICE")
                ignored += 1
                continue
            print("Article is ICE-relevant")
            
            # Step 3: Extract address information
            print("\nExtracting address information...")
            address = extract_addr(text)
            if not address:
                print("Could not extract address information")
                ignored += 1
                continue
            print(f"Extracted address: {address}")
            
            # Step 4: Sanitize address
            print("\nSanitizing address...")
            sanitized_address = sanitize_addr(address, text)
            print(f"Sanitized address: {sanitized_address}")
            
            # Step 5: Get coordinates from address
            print(f"\nGetting coordinates for: {sanitized_address}")
            coords = tag_coords(sanitized_address)
            if not coords:
                print("Could not extract coordinates from address")
                ignored += 1
                continue
            print(f"Coordinates: {coords[0]:.6f}, {coords[1]:.6f}")
            
            # Step 6: Categorize
            print("\nCategorizing article...")
            category = classify(text)
            print(f"Category: {category}")
            
            # Step 7: Get publisher
            print("\nExtracting publisher...")
            publisher = canonical_pub(rec.url)
            print(f"Publisher: {publisher}")
            
            # Step 8: Build payload
            payload: ArticlePayload = {
                "title":      rec.title,
                "date":       rec.date.isoformat(),
                "url":        rec.url,
                "text":       text,
                "coordinates": {"lat": coords[0], "lon": coords[1]},
                "category":   category,
                "publisher":  publisher,
                "address":    sanitized_address,  # Store the sanitized address
            }

            # Enrich with parsed location information
            payload = enrich_addr(payload)

            # Show parsed location details
            if "parsed_location" in payload:
                loc = payload["parsed_location"]
                print(f"Parsed location details:")
                print(f"   City: {loc.get('city', 'N/A')}")
                print(f"   State: {loc.get('state', 'N/A')}")
                print(f"   Country: {loc.get('country', 'N/A')}")
                print(f"   Address: {loc.get('address', 'N/A')}")
                print(f"   Details: {loc.get('location_details', 'N/A')}")

            # Ensure the sanitized address persists as the primary address field
            # This takes precedence over parsed_location.address for consistency
            payload["address"] = sanitized_address
            
            print(f"Final address: {payload.get('address', 'N/A')}")
            
            # Step 9: Check sufficiency
            print("\nChecking payload sufficiency...")
            is_sufficient = sufficiency(payload)
            if not is_sufficient:
                print("Article payload insufficient")
                print(f"   Required fields: title, date, url, coordinates, category, publisher")
                print(f"   Available fields: {list(payload.keys())}")
                ignored += 1
                continue
            print("Payload is sufficient")
            
            # Step 10: Persist article
            print("\nPersisting article...")
            persist(payload)
            print("Article successfully added!")
            accepted += 1
            
            # Show final payload summary
            print(f"\nFinal payload summary:")
            print(f"   Title: {payload.get('title', 'N/A')[:50]}...")
            print(f"   Date: {payload.get('date', 'N/A')}")
            print(f"   Category: {payload.get('category', 'N/A')}")
            print(f"   Publisher: {payload.get('publisher', 'N/A')}")
            print(f"   Address: {payload.get('address', 'N/A')}")
            print(f"   Coordinates: {payload.get('coordinates', 'N/A')}")
            
        except Exception as e:
            print(f"Error processing article: {e}")
            import traceback
            print(f"Full error details:")
            traceback.print_exc()
            ignored += 1
            continue
        
        # Progress update
        print(f"\nProgress: {accepted} accepted, {ignored} ignored")

    
    print("\n" + "=" * 80)
    print(f"Processing complete!")
    print(f"Accepted: {accepted} articles")
    print(f"Ignored: {ignored} articles")
    print(f"Success rate: {accepted/(accepted+ignored)*100:.1f}%" if (accepted+ignored) > 0 else "No articles processed")
    
    return accepted, ignored

def process_api_articles(
    max_articles: int = 10,
    *,
    # Inject the tool chain so tests can monkey-patch
    fetch_text: ToolFunc = getText,
    relevance:  ToolFunc = judgeRelevance,
    extract_addr: ToolFunc = extractAddressFromText,
    sanitize_addr: ToolFunc = sanitize_address,
    tag_coords: ToolFunc = geoTag,
    classify:   ToolFunc = categorize,
    canonical_pub: ToolFunc = addPublisher,
    enrich_addr: ToolFunc = parseAddressInfo,
    sufficiency: ToolFunc = judgeEntrySufficiency,
    persist: ToolFunc = addArticle,
    mark_processed: ToolFunc = markArticleAsProcessed,
) -> tuple[int, int]:
    """Process articles from API with live status reporting."""
    accepted = ignored = 0
    
    print(f"Starting ICE Agent - Processing articles from API")
    print("=" * 80)
    
    # Get unprocessed articles from API
    try:
        csv_data = getUnprocessedArticles()
        print(f"Retrieved {len(csv_data)} characters of CSV data from API")
        
        # Normalize line endings and clean up the CSV data
        csv_data = csv_data.replace('\r\n', '\n').replace('\r', '\n')
        
        # Show full CSV content
        print("\n" + "="*80)
        print("RAW CSV DATA FROM API:")
        print("="*80)
        print(csv_data)
        print("="*80)
        
        # Show CSV structure for debugging
        lines = csv_data.strip().split('\n')
        if lines:
            print(f"CSV has {len(lines)} lines")
            if len(lines) > 1:
                print(f"First line (headers): {lines[0]}")
                print(f"Second line (sample): {lines[1]}")
    except Exception as e:
        print(f"Failed to get unprocessed articles: {e}")
        return 0, 0
    
    if not csv_data.strip():
        print("No unprocessed articles found")
        return 0, 0
    
    # Process the CSV data
    reader = csv.DictReader(io.StringIO(csv_data))
    records = []
    for row in reader:
        try:
            # Parse the date string to datetime
            try:
                date_obj = datetime.strptime(row['date'], '%Y-%m-%d')
            except ValueError:
                # If date parsing fails, use current date
                date_obj = datetime.now()
            
            record = CSVRecord(
                title=row['title'],
                description=row.get('description', ''),
                date=date_obj,
                url=row['url']
            )
            records.append(record)
        except Exception as e:
            print(f"Error parsing CSV row: {e}")
            continue
    
    if not records:
        print("No valid articles found in API response")
        return 0, 0
    
    # Show parsed records
    print(f"\nPARSED RECORDS:")
    print("="*80)
    for i, record in enumerate(records):
        print(f"Record {i+1}:")
        print(f"  Title: {record.title}")
        print(f"  URL: {record.url}")
        print(f"  Date: {record.date}")
        print(f"  Description: {record.description[:100]}..." if record.description else "  Description: (empty)")
        print()
    
    # Limit to max_articles
    records = records[:max_articles]
    print(f"Processing {len(records)} articles")
    print("=" * 80)
    
    for i, rec in enumerate(records, 1):
        print(f"\n{'='*60}")
        print(f"Processing article {i}/{len(records)}")
        print(f"Title: {rec.title}")
        print(f"Date: {rec.date}")
        print(f"URL: {rec.url}")
        print(f"{'='*60}")
        
        try:
            # Step 1: Fetch article text
            print("Fetching article text...")
            text = fetch_text(rec.url)
            if not text:
                print("Failed to fetch article text")
                ignored += 1
                continue
            
            # Show first 200 characters of text
            text_preview = text[:200].replace('\n', ' ').strip()
            print(f"Article text preview: {text_preview}...")
            print(f"Text length: {len(text)} characters")
            
            # Step 2: Check relevance
            print("\nChecking relevance...")
            is_relevant = relevance(text)
            if not is_relevant:
                print("Article not relevant to ICE")
                ignored += 1
                continue
            print("Article is ICE-relevant")
            
            # Step 3: Extract address information
            print("\nExtracting address information...")
            address = extract_addr(text)
            if not address:
                print("Could not extract address information")
                ignored += 1
                continue
            print(f"Extracted address: {address}")
            
            # Step 4: Sanitize address
            print("\nSanitizing address...")
            sanitized_address = sanitize_addr(address, text)
            print(f"Sanitized address: {sanitized_address}")
            
            # Step 5: Get coordinates from address
            print(f"\nGetting coordinates for: {sanitized_address}")
            coords = tag_coords(sanitized_address)
            if not coords:
                print("Could not extract coordinates from address")
                ignored += 1
                continue
            print(f"Coordinates: {coords[0]:.6f}, {coords[1]:.6f}")
            
            # Step 6: Categorize
            print("\nCategorizing article...")
            category = classify(text)
            print(f"Category: {category}")
            
            # Step 7: Get publisher
            print("\nExtracting publisher...")
            publisher = canonical_pub(rec.url)
            print(f"Publisher: {publisher}")
            
            # Step 8: Build payload
            payload: ArticlePayload = {
                "title":      rec.title,
                "date":       rec.date.isoformat(),
                "url":        rec.url,
                "text":       text,
                "coordinates": {"lat": coords[0], "lon": coords[1]},
                "category":   category,
                "publisher":  publisher,
                "address":    sanitized_address,  # Store the sanitized address
            }
            
            # Enrich with parsed location information
            payload = enrich_addr(payload)

            # Show parsed location details
            if "parsed_location" in payload:
                loc = payload["parsed_location"]
                print(f"Parsed location details:")
                print(f"   City: {loc.get('city', 'N/A')}")
                print(f"   State: {loc.get('state', 'N/A')}")
                print(f"   Country: {loc.get('country', 'N/A')}")
                print(f"   Address: {loc.get('address', 'N/A')}")
                print(f"   Details: {loc.get('location_details', 'N/A')}")

            # Ensure the sanitized address persists as the primary address field
            # This takes precedence over parsed_location.address for consistency
            payload["address"] = sanitized_address
            
            print(f"Final address: {payload.get('address', 'N/A')}")
            
            # Step 9: Check sufficiency
            print("\nChecking payload sufficiency...")
            is_sufficient = sufficiency(payload)
            if not is_sufficient:
                print("Article payload insufficient")
                print(f"   Required fields: title, date, url, coordinates, category, publisher")
                print(f"   Available fields: {list(payload.keys())}")
                ignored += 1
                continue
            print("Payload is sufficient")
            
            # Step 10: Persist article
            print("\nPersisting article...")
            try:
                persist(payload)
                print("Article successfully added!")
                accepted += 1
            except Exception as e:
                print(f"Failed to persist article: {e}")
            
            # Step 11: Mark as processed (regardless of success/failure)
            print("\nMarking article as processed...")
            mark_processed(rec.url)
            
            # Show final payload summary
            print(f"\nFinal payload summary:")
            print(f"   Title: {payload.get('title', 'N/A')[:50]}...")
            print(f"   Date: {payload.get('date', 'N/A')}")
            print(f"   Category: {payload.get('category', 'N/A')}")
            print(f"   Publisher: {payload.get('publisher', 'N/A')}")
            print(f"   Address: {payload.get('address', 'N/A')}")
            print(f"   Coordinates: {payload.get('coordinates', 'N/A')}")
            
        except Exception as e:
            print(f"Error processing article: {e}")
            import traceback
            print(f"Full error details:")
            traceback.print_exc()
            
            # Mark as processed even if there was an error
            try:
                print(f"\nMarking article as processed despite error...")
                mark_processed(rec.url)
            except Exception as mark_error:
                print(f"Failed to mark article as processed: {mark_error}")
            
            ignored += 1
            continue
        
        # Progress update
        print(f"\nProgress: {accepted} accepted, {ignored} ignored")
    
    print("\n" + "=" * 80)
    print(f"Processing complete!")
    print(f"Accepted: {accepted} articles")
    print(f"Ignored: {ignored} articles")
    print(f"Success rate: {accepted/(accepted+ignored)*100:.1f}%" if (accepted+ignored) > 0 else "No articles processed")
    
    return accepted, ignored

def run_continuous_processing(
    max_articles_per_batch: int = 25,
    wait_minutes: int = 5,
    *,
    # Inject the tool chain so tests can monkey-patch
    fetch_text: ToolFunc = getText,
    relevance:  ToolFunc = judgeRelevance,
    extract_addr: ToolFunc = extractAddressFromText,
    sanitize_addr: ToolFunc = sanitize_address,
    tag_coords: ToolFunc = geoTag,
    classify:   ToolFunc = categorize,
    canonical_pub: ToolFunc = addPublisher,
    enrich_addr: ToolFunc = parseAddressInfo,
    sufficiency: ToolFunc = judgeEntrySufficiency,
    persist: ToolFunc = addArticle,
    mark_processed: ToolFunc = markArticleAsProcessed,
    get_articles: ToolFunc = getUnprocessedArticles,
) -> None:
    """
    Run the ICE Agent continuously, processing articles in batches.
    
    When no articles are available, wait for the specified number of minutes
    before checking again. This function runs indefinitely until interrupted.
    """
    import time
    from datetime import datetime
    
    print("=" * 80)
    print("ICE Agent - Continuous Processing Mode")
    print("=" * 80)
    print(f"Max articles per batch: {max_articles_per_batch}")
    print(f"Wait time when no articles: {wait_minutes} minutes")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    batch_count = 0
    total_accepted = 0
    total_ignored = 0
    
    while True:
        batch_count += 1
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n{'='*80}")
        print(f"BATCH #{batch_count} - {current_time}")
        print(f"{'='*80}")
        
        try:
            # Check for unprocessed articles
            print("Checking for unprocessed articles...")
            csv_data = get_articles()
            
            if not csv_data.strip():
                print(f"No unprocessed articles found. Waiting {wait_minutes} minutes...")
                print(f"Next check at: {(datetime.now().timestamp() + wait_minutes * 60):.0f}")
                
                # Wait for specified minutes
                time.sleep(wait_minutes * 60)
                continue
            
            print(f"Found articles to process. Starting batch...")
            
            # Process the current batch
            accepted, ignored = process_api_articles(
                max_articles=max_articles_per_batch,
                fetch_text=fetch_text,
                relevance=relevance,
                extract_addr=extract_addr,
                sanitize_addr=sanitize_addr,
                tag_coords=tag_coords,
                classify=classify,
                canonical_pub=canonical_pub,
                enrich_addr=enrich_addr,
                sufficiency=sufficiency,
                persist=persist,
                mark_processed=mark_processed,
            )
            
            # Update totals
            total_accepted += accepted
            total_ignored += ignored
            
            # Show batch summary
            print(f"\n{'='*80}")
            print(f"BATCH #{batch_count} COMPLETE")
            print(f"{'='*80}")
            print(f"Batch results: {accepted} accepted, {ignored} ignored")
            print(f"Running totals: {total_accepted} accepted, {total_ignored} ignored")
            print(f"Total processed: {total_accepted + total_ignored}")
            if (total_accepted + total_ignored) > 0:
                print(f"Overall success rate: {total_accepted/(total_accepted+total_ignored)*100:.1f}%")
            print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Continue immediately to check for more articles
            print("Continuing immediately to check for more articles...")
            
        except KeyboardInterrupt:
            print(f"\n{'='*80}")
            print("INTERRUPTED BY USER")
            print(f"{'='*80}")
            print(f"Final totals: {total_accepted} accepted, {total_ignored} ignored")
            print(f"Total processed: {total_accepted + total_ignored}")
            if (total_accepted + total_ignored) > 0:
                print(f"Overall success rate: {total_accepted/(total_accepted+total_ignored)*100:.1f}%")
            print(f"Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            break
            
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"ERROR IN BATCH #{batch_count}")
            print(f"{'='*80}")
            print(f"Error: {e}")
            import traceback
            print(f"Full error details:")
            traceback.print_exc()
            print(f"Waiting {wait_minutes} minutes before retrying...")
            time.sleep(wait_minutes * 60)

def process_stream(
    csv_blob: str,
    *,
    # Inject the tool chain so tests can monkey-patch
    fetch_text: ToolFunc = getText,
    relevance:  ToolFunc = judgeRelevance,
    extract_addr: ToolFunc = extractAddressFromText,
    sanitize_addr: ToolFunc = sanitize_address,
    tag_coords: ToolFunc = geoTag,
    classify:   ToolFunc = categorize,
    canonical_pub: ToolFunc = addPublisher,
    enrich_addr: ToolFunc = parseAddressInfo,
    sufficiency: ToolFunc = judgeEntrySufficiency,
    persist: ToolFunc = addArticle,
) -> tuple[int, int]:
    """Core agent loop. Returns (#accepted, #ignored)."""
    accepted = ignored = 0

    reader = csv.DictReader(io.StringIO(csv_blob))
    for row in reader:
        try:
            # Parse the date string to datetime
            try:
                date_obj = datetime.strptime(row['date'], '%Y-%m-%d')
            except ValueError:
                # If date parsing fails, use current date
                date_obj = datetime.now()
            
            rec = CSVRecord(
                title=row['title'],
                description=row.get('description', ''),
                date=date_obj,
                url=row['url']
            )
        except Exception as e:
            print(f"Error parsing CSV row: {e}")
            ignored += 1
            continue
        
        print(f"\nProcessing: {rec.title[:60]}...")
        print(f"URL: {rec.url}")

        text = fetch_text(rec.url)
        if not text:
            print("Failed to fetch text")
            ignored += 1
            continue
            
        print(f"Text length: {len(text)} chars")
        
        if not relevance(text):
            print("Not ICE-relevant")
            ignored += 1
            continue
        print("ICE-relevant")

        # Extract address information first
        address = extract_addr(text)
        if not address:
            print("No address found")
            ignored += 1
            continue
        print(f"Address: {address}")

        # Sanitize address before geocoding
        sanitized_address = sanitize_addr(address, text)
        print(f"Sanitized address: {sanitized_address}")

        # Get coordinates from sanitized address
        coords = tag_coords(sanitized_address)
        if not coords:
            print("No coordinates found")
            ignored += 1
            continue
        print(f"Coords: {coords[0]:.4f}, {coords[1]:.4f}")

        payload: ArticlePayload = {
            "title":      rec.title,
            "date":       rec.date.isoformat(),
            "url":        rec.url,
            "text":       text,
            "coordinates": {"lat": coords[0], "lon": coords[1]},
            "category":   classify(text),
            "publisher":  canonical_pub(rec.url),
            "address":    sanitized_address,  # Store the sanitized address
        }

        payload = enrich_addr(payload)  # attach admin area, country, etc.

        # Ensure the sanitized address persists as the primary address field
        # This takes precedence over parsed_location.address for consistency
        payload["address"] = sanitized_address

        if not sufficiency(payload):
            print("Insufficient payload")
            ignored += 1
            continue

        try:
            persist(payload)
            print("Article persisted")
            accepted += 1
        except Exception as e:
            print(f"Failed to persist article: {e}")
            ignored += 1

    return accepted, ignored

# ---------------------------------------------------------------------------
# ───────────────────────────  API ROUTES  ─────────────────────────────────-
# ---------------------------------------------------------------------------

@app.post("/mcp/ingest", response_model=MCPResponse)
def ingest(envelope: MCPEnvelope):
    """
    MCP endpoint.

    Pass an envelope whose *body* is a raw CSV string (w/o header) where
    each line = "title,date,url".  
    ↳ The agent streams through, enriches, and persists qualifying articles.
    """
    try:
        accepted, ignored = process_stream(envelope.body)
        return MCPResponse(status="ok", accepted=accepted, ignored=ignored)
    except Exception as exc:  # noqa: BLE001
        # In production you'd log + capture tracebacks here
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/process-csv")
def process_csv_endpoint():
    """Process the first 100 articles from the CSV file."""
    try:
        accepted, ignored = process_csv_articles(100)
        return {
            "status": "ok",
            "accepted": accepted,
            "ignored": ignored,
            "total_processed": accepted + ignored
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/process-api")
def process_api_endpoint():
    """Process articles from the API."""
    try:
        accepted, ignored = process_api_articles(100)
        return {
            "status": "ok",
            "accepted": accepted,
            "ignored": ignored,
            "total_processed": accepted + ignored
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/process-continuous")
def process_continuous_endpoint():
    """Start continuous processing of articles from the API."""
    try:
        # Start continuous processing in a separate thread to avoid blocking the API
        import threading
        
        def run_continuous():
            run_continuous_processing(max_articles_per_batch=25, wait_minutes=5)
        
        thread = threading.Thread(target=run_continuous, daemon=True)
        thread.start()
        
        return {
            "status": "ok",
            "message": "Continuous processing started in background",
            "note": "Use Ctrl+C to stop the process"
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

# ---------------------------------------------------------------------------
# ────────────────────────────  RUNNER  ─────────────────────────────────────
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # ── Development entry-point ────────────────────────────────────────────
    # Run continuous processing of articles from API
    print("ICE Agent Starting in Continuous Mode...")
    print("Press Ctrl+C to stop the process")
    run_continuous_processing(max_articles_per_batch=25, wait_minutes=5)
    
    # ── Server mode ────────────────────────────────────────────────────────
    # uvicorn ice_agent.app:app --reload --host 0.0.0.0 --port 8000
    # import uvicorn
    # uvicorn.run("ice_agent.app:app", host="0.0.0.0", port=8000, reload=True)
