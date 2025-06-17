import pandas as pd
import googlemaps
import time
from typing import Tuple, Optional
import os
from dotenv import load_dotenv

def geocode_facility(facility_name: str, city: str, state: str, gmaps_client) -> Tuple[Optional[float], Optional[float]]:
    """
    Geocode a facility using Google Places API.
    Returns (latitude, longitude) or (None, None) if geocoding fails.
    """
    # Construct the search query
    query = f"{facility_name}, {city}, {state}, USA"
    
    try:
        # Add delay to respect rate limits
        time.sleep(0.2)  # Google's rate limit is more generous than Nominatim
        
        # First try to find the place using Places API
        places_result = gmaps_client.places(query)
        
        if places_result['status'] == 'OK' and places_result['results']:
            location = places_result['results'][0]['geometry']['location']
            return location['lat'], location['lng']
            
        # If Places API doesn't find it, try Geocoding API as fallback
        geocode_result = gmaps_client.geocode(query)
        
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return location['lat'], location['lng']
            
        return None, None
        
    except Exception as e:
        print(f"Error geocoding {query}: {str(e)}")
        return None, None

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize Google Maps client
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("Error: GOOGLE_PLACES_API_KEY not found in .env file")
        return
        
    gmaps = googlemaps.Client(key=api_key)
    
    # Read the CSV file
    input_file = "data/ice_facilities.csv"
    output_file = "data/ice_facilities_with_coordinates.csv"
    
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}")
        return
    
    # Add new columns for coordinates
    df['Latitude'] = None
    df['Longitude'] = None
    
    # Process each facility
    total = len(df)
    for idx, row in df.iterrows():
        print(f"Processing {idx + 1}/{total}: {row['Facility Name']}")
        
        lat, lon = geocode_facility(
            row['Facility Name'],
            row['City'],
            row['State'],
            gmaps
        )
        
        df.at[idx, 'Latitude'] = lat
        df.at[idx, 'Longitude'] = lon
    
    # Save the results
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")
    
    # Print summary
    successful = df['Latitude'].notna().sum()
    print(f"\nSummary:")
    print(f"Total facilities processed: {total}")
    print(f"Successfully geocoded: {successful}")
    print(f"Failed to geocode: {total - successful}")

if __name__ == "__main__":
    main()
