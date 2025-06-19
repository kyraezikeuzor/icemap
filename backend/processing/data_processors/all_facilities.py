#!/usr/bin/env python3
"""
Scrape ICE detention facility information from ice.gov and save to CSV.
"""
import csv
from pathlib import Path
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ice.gov/detention-facilities"
OUTPUT_CSV = Path("data/all_facilities.csv") 
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_page(url: str) -> Optional[BeautifulSoup]:
    """Fetch and parse a page, with error handling and rate limiting."""
    try:
        time.sleep(1)  # Be nice to the server
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_facility(facility_element) -> Dict[str, str]:
    """Extract facility information from a grid element."""
    facility = {}
    
    # Get facility name
    name_elem = facility_element.select_one(".views-field-title .field-content")
    facility["name"] = name_elem.text.strip() if name_elem else ""
    
    # Get field office name
    field_office_elem = facility_element.select_one(".views-field-field-field-office-name .field-content")
    facility["field_office"] = field_office_elem.text.strip() if field_office_elem else ""
    
    # Get address components
    address_elem = facility_element.select_one(".address")
    if address_elem:
        street = address_elem.select_one(".address-line1")
        city = address_elem.select_one(".locality")
        state = address_elem.select_one(".administrative-area")
        zipcode = address_elem.select_one(".postal-code")
        
        facility["street"] = street.text.strip() if street else ""
        facility["city"] = city.text.strip() if city else ""
        facility["state"] = state.text.strip() if state else ""
        facility["zipcode"] = zipcode.text.strip() if zipcode else ""
        
    return facility

def scrape_facilities() -> List[Dict[str, str]]:
    """Scrape all facilities from all pages."""
    facilities = []
    current_url = BASE_URL
    page_num = 0
    
    while True:
        print(f"Scraping page {page_num}...")
        soup = get_page(current_url)
        if not soup:
            break
            
        # Find all facility grid items
        for facility_elem in soup.select("li.grid"):
            facility_data = parse_facility(facility_elem)
            if facility_data:
                facilities.append(facility_data)
                
        # Look for next page link
        next_link = soup.select_one("a.usa-pagination__next-page")
        if not next_link:
            break
            
        # Update URL for next page
        next_page = next_link.get("href", "")
        if not next_page:
            break
        current_url = urljoin(BASE_URL, next_page)
        page_num += 1
        
    return facilities

def save_facilities(facilities: List[Dict[str, str]]) -> None:
    """Save facilities data to CSV file."""
    if not facilities:
        print("No facilities found to save")
        return
        
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = ["name", "field_office", "street", "city", "state", "zipcode"]
    
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(facilities)
        
    print(f"Saved {len(facilities)} facilities to {OUTPUT_CSV}")

def main() -> None:
    facilities = scrape_facilities()
    save_facilities(facilities)

if __name__ == "__main__":
    main()
