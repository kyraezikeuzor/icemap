import pandas as pd
import requests
import time
import re
from typing import Optional, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CityCoordinateProcessor:
    def __init__(self):
        self.geocoding_cache = {}
        # Hardcoded coordinates for major US cities
        self.city_coordinates = {
            'New York City': (40.7128, -74.0060),
            'Los Angeles': (34.0522, -118.2437),
            'Chicago': (41.8781, -87.6298),
            'Houston': (29.7604, -95.3698),
            'Phoenix': (33.4484, -112.0740),
            'Philadelphia': (39.9526, -75.1652),
            'San Antonio': (29.4241, -98.4936),
            'San Diego': (32.7157, -117.1611),
            'Dallas': (32.7767, -96.7970),
            'San Jose': (37.3382, -121.8863),
            'Austin': (30.2672, -97.7431),
            'Jacksonville': (30.3322, -81.6557),
            'Fort Worth': (32.7555, -97.3308),
            'Columbus': (39.9612, -82.9988),
            'Charlotte': (35.2271, -80.8431),
            'San Francisco': (37.7749, -122.4194),
            'Indianapolis': (39.7684, -86.1581),
            'Seattle': (47.6062, -122.3321),
            'Denver': (39.7392, -104.9903),
            'Washington': (38.9072, -77.0369),
            'Boston': (42.3601, -71.0589),
            'El Paso': (31.7619, -106.4850),
            'Nashville': (36.1627, -86.7816),
            'Detroit': (42.3314, -83.0458),
            'Oklahoma City': (35.4676, -97.5164),
            'Portland': (45.5152, -122.6784),
            'Las Vegas': (36.1699, -115.1398),
            'Memphis': (35.1495, -90.0490),
            'Louisville': (38.2527, -85.7585),
            'Baltimore': (39.2904, -76.6122),
            'Milwaukee': (43.0389, -87.9065),
            'Albuquerque': (35.0844, -106.6504),
            'Tucson': (32.2226, -110.9747),
            'Fresno': (36.7378, -119.7871),
            'Sacramento': (38.5816, -121.4944),
            'Atlanta': (33.7490, -84.3880),
            'Kansas City': (39.0997, -94.5786),
            'Miami': (25.7617, -80.1918),
            'Raleigh': (35.7796, -78.6382),
            'Omaha': (41.2565, -95.9345),
            'Minneapolis': (44.9778, -93.2650),
            'Cleveland': (41.4993, -81.6944),
            'Tulsa': (36.1540, -95.9928),
            'Arlington': (32.7357, -97.1081),
            'New Orleans': (29.9511, -90.0715),
            'Wichita': (37.6872, -97.3301),
            'Bakersfield': (35.3733, -119.0187),
            'Tampa': (27.9506, -82.4572),
            'Aurora': (39.7294, -104.8319),
            'Honolulu': (21.3099, -157.8581),
            'Anaheim': (33.8366, -117.9143),
            'Santa Ana': (33.7455, -117.8677),
            'Corpus Christi': (27.8006, -97.3964),
            'Riverside': (33.9533, -117.3962),
            'Lexington': (38.0406, -84.5037),
            'Stockton': (37.9577, -121.2908),
            'Henderson': (36.0395, -114.9817),
            'Saint Paul': (44.9537, -93.0900),
            'St. Louis': (38.6270, -90.1994),
            'Fort Wayne': (41.0793, -85.1394),
            'Jersey City': (40.7178, -74.0431),
            'Chula Vista': (32.6401, -117.0842),
            'Orlando': (28.5383, -81.3792),
            'Laredo': (27.5064, -99.5075),
            'Chandler': (33.3062, -111.8413),
            'Madison': (43.0731, -89.4012),
            'Lubbock': (33.5779, -101.8552),
            'Scottsdale': (33.4942, -111.9261),
            'Reno': (39.5296, -119.8138),
            'Buffalo': (42.8864, -78.8784),
            'Gilbert': (33.3528, -111.7890),
            'Glendale': (33.5387, -112.1860),
            'North Las Vegas': (36.1989, -115.1175),
            'Winston-Salem': (36.0999, -80.2442),
            'Chesapeake': (36.7682, -76.2875),
            'Norfolk': (36.8508, -76.2859),
            'Fremont': (37.5485, -121.9886),
            'Garland': (32.9126, -96.6389),
            'Irving': (32.8140, -96.9489),
            'Hialeah': (25.8576, -80.2781),
            'Richmond': (37.5407, -77.4360),
            'Boise': (43.6150, -116.2023),
            'Spokane': (47.6588, -117.4260),
            'Baton Rouge': (30.4515, -91.1871),
            'Tacoma': (47.2529, -122.4443),
            'San Bernardino': (34.1083, -117.2898),
            'Grand Rapids': (42.9634, -85.6681),
            'Huntsville': (34.7304, -86.5861),
            'Salt Lake City': (40.7608, -111.8910),
            'Frisco': (33.1507, -96.8236),
            'Yonkers': (40.9312, -73.8987),
            'Amarillo': (35.2220, -101.8313),
            'Glendale': (34.1425, -118.2551),
            'McKinney': (33.1972, -96.6397),
            'Rochester': (43.1566, -77.6088),
            'Tucson': (32.2226, -110.9747),
            'Newark': (40.7357, -74.1724),
            'St. Petersburg': (27.7731, -82.6400),
            'Durham': (35.9940, -78.8986),
            'Chandler': (33.3062, -111.8413),
            'Plano': (33.0198, -96.6989),
            'Irvine': (33.6846, -117.8265),
            'Laredo': (27.5064, -99.5075),
            'Lubbock': (33.5779, -101.8552),
            'Reno': (39.5296, -119.8138),
            'Anchorage': (61.2181, -149.9003),
            'Pasadena': (34.1478, -118.1445),
            'Pico Rivera': (33.9831, -118.0967),
            'Dublin': (37.7021, -121.9358),
            'Anaheim': (33.8366, -117.9143),
            'Omaha': (41.2565, -95.9345),
            'Bellevue': (47.6101, -122.2015),
            'Bronx': (40.8448, -73.8648),
            'Napa': (38.2975, -122.2869),
            'Columbia': (34.0007, -81.0348),
            'Memphis': (35.1495, -90.0490),
            'Fayetteville': (36.0822, -94.1719),
            'Altadena': (34.1897, -118.1312),
            'Downey': (33.9401, -118.1332),
            'New York': (40.7128, -74.0060),
            'California': (36.7783, -119.4179),
            'Texas': (31.9686, -99.9018),
            'Florida': (27.6648, -81.5158),
            'Illinois': (40.6331, -89.3985),
            'Pennsylvania': (40.5908, -77.2098),
            'Ohio': (40.4173, -82.9071),
            'Georgia': (32.1656, -82.9001),
            'North Carolina': (35.7596, -79.0193),
            'Michigan': (44.3148, -85.6024),
            'New Jersey': (40.0583, -74.4057),
            'Virginia': (37.7693, -78.1700),
            'Washington': (47.4009, -121.4905),
            'Arizona': (33.7298, -111.4312),
            'Massachusetts': (42.2304, -71.5301),
            'Tennessee': (35.7478, -86.6923),
            'Indiana': (39.8494, -86.2583),
            'Missouri': (38.4561, -92.2884),
            'Maryland': (39.0639, -76.8021),
            'Colorado': (39.5501, -105.7821),
            'Minnesota': (46.7296, -94.6859),
            'Wisconsin': (44.2685, -89.6165),
            'Alabama': (32.3182, -86.9023),
            'South Carolina': (33.8569, -80.9450),
            'Louisiana': (31.1695, -91.8678),
            'Kentucky': (37.6681, -84.6701),
            'Oregon': (44.5720, -122.0709),
            'Oklahoma': (35.0078, -97.0929),
            'Connecticut': (41.6032, -73.0877),
            'Utah': (39.3210, -111.0937),
            'Iowa': (42.0329, -93.6238),
            'Nevada': (38.8026, -116.4194),
            'Arkansas': (34.9697, -92.3731),
            'Mississippi': (32.7416, -89.6787),
            'Kansas': (38.5111, -96.8005),
            'Nebraska': (41.4925, -99.9018),
            'Idaho': (44.2405, -114.4788),
            'West Virginia': (38.5976, -80.4549),
            'Hawaii': (19.8968, -155.5828),
            'New Hampshire': (43.1939, -71.5724),
            'Maine': (44.6939, -69.3819),
            'Rhode Island': (41.6809, -71.5118),
            'Montana': (46.8797, -110.3626),
            'Delaware': (38.9108, -75.5277),
            'South Dakota': (44.2998, -99.4388),
            'North Dakota': (47.5515, -101.0020),
            'Alaska': (63.5887, -154.4931),
            'Vermont': (44.0459, -72.7107),
            'Wyoming': (42.7475, -107.2085),
            'Puerto Rico': (18.2208, -66.5901),
            'NYC': (40.7128, -74.0060),
            'LA': (34.0522, -118.2437),
            'PR': (18.2208, -66.5901)
        }
        
    def get_city_coordinates(self, city: str, state: str = None) -> Optional[Tuple[float, float]]:
        """
        Get coordinates for a city using hardcoded database.
        """
        if not city or city.strip() == "":
            return None
            
        # Create cache key
        cache_key = f"{city},{state}" if state else city
        
        # Check cache first
        if cache_key in self.geocoding_cache:
            return self.geocoding_cache[cache_key]
        
        # Try to find in our hardcoded database
        if city in self.city_coordinates:
            coords = self.city_coordinates[city]
            self.geocoding_cache[cache_key] = coords
            logger.info(f"Found coordinates for {city}: {coords[0]}, {coords[1]}")
            return coords
        
        # If not found, return None
        logger.warning(f"No coordinates found for {city}")
        return None
    
    def clean_location_data(self, row: pd.Series) -> dict:
        """
        Clean and standardize location data from a row.
        """
        # Extract and clean city and state
        city = str(row.get('city', '')).strip() if pd.notna(row.get('city')) else ''
        state = str(row.get('state', '')).strip() if pd.notna(row.get('state')) else ''
        
        # Clean up common variations
        if city.lower() in ['nyc', 'new york city']:
            city = 'New York City'
        elif city.lower() in ['la', 'los angeles']:
            city = 'Los Angeles'
        elif city.lower() in ['chicago']:
            city = 'Chicago'
        elif city.lower() in ['atlanta']:
            city = 'Atlanta'
        elif city.lower() in ['detroit']:
            city = 'Detroit'
        elif city.lower() in ['boston']:
            city = 'Boston'
        elif city.lower() in ['seattle']:
            city = 'Seattle'
        elif city.lower() in ['denver']:
            city = 'Denver'
        elif city.lower() in ['salt lake city']:
            city = 'Salt Lake City'
        elif city.lower() in ['pasadena']:
            city = 'Pasadena'
        elif city.lower() in ['pico rivera']:
            city = 'Pico Rivera'
        elif city.lower() in ['dublin']:
            city = 'Dublin'
        elif city.lower() in ['anaheim']:
            city = 'Anaheim'
        elif city.lower() in ['omaha']:
            city = 'Omaha'
        elif city.lower() in ['bellevue']:
            city = 'Bellevue'
        elif city.lower() in ['bronx']:
            city = 'Bronx'
        elif city.lower() in ['napa']:
            city = 'Napa'
        elif city.lower() in ['columbia']:
            city = 'Columbia'
        elif city.lower() in ['newark']:
            city = 'Newark'
        elif city.lower() in ['memphis']:
            city = 'Memphis'
        elif city.lower() in ['fayetteville']:
            city = 'Fayetteville'
        elif city.lower() in ['san diego']:
            city = 'San Diego'
        elif city.lower() in ['altadena']:
            city = 'Altadena'
        elif city.lower() in ['downey']:
            city = 'Downey'
        
        # Clean state abbreviations
        state_mapping = {
            'CA': 'California',
            'NY': 'New York',
            'TX': 'Texas',
            'FL': 'Florida',
            'IL': 'Illinois',
            'PA': 'Pennsylvania',
            'OH': 'Ohio',
            'GA': 'Georgia',
            'NC': 'North Carolina',
            'MI': 'Michigan',
            'NJ': 'New Jersey',
            'VA': 'Virginia',
            'WA': 'Washington',
            'AZ': 'Arizona',
            'MA': 'Massachusetts',
            'TN': 'Tennessee',
            'IN': 'Indiana',
            'MO': 'Missouri',
            'MD': 'Maryland',
            'CO': 'Colorado',
            'MN': 'Minnesota',
            'WI': 'Wisconsin',
            'AL': 'Alabama',
            'SC': 'South Carolina',
            'LA': 'Louisiana',
            'KY': 'Kentucky',
            'OR': 'Oregon',
            'OK': 'Oklahoma',
            'CT': 'Connecticut',
            'UT': 'Utah',
            'IA': 'Iowa',
            'NV': 'Nevada',
            'AR': 'Arkansas',
            'MS': 'Mississippi',
            'KS': 'Kansas',
            'NE': 'Nebraska',
            'ID': 'Idaho',
            'WV': 'West Virginia',
            'HI': 'Hawaii',
            'NH': 'New Hampshire',
            'ME': 'Maine',
            'RI': 'Rhode Island',
            'MT': 'Montana',
            'DE': 'Delaware',
            'SD': 'South Dakota',
            'ND': 'North Dakota',
            'AK': 'Alaska',
            'VT': 'Vermont',
            'WY': 'Wyoming',
            'PR': 'Puerto Rico'
        }
        
        if state in state_mapping:
            state = state_mapping[state]
        
        return {
            'city': city,
            'state': state
        }
    
    def process_row(self, row: pd.Series) -> Optional[dict]:
        """
        Process a single row and return the processed data or None if should be omitted.
        """
        # Check if we already have coordinates
        existing_lat = row.get('latitude')
        existing_lon = row.get('longitude')
        
        if pd.notna(existing_lat) and pd.notna(existing_lon):
            # Already has coordinates, keep the entry
            return {
                'id': row.get('id', ''),
                'location': row.get('address', ''),
                'latitude': float(existing_lat),
                'longitude': float(existing_lon),
                'city': str(row.get('city', '')) if pd.notna(row.get('city')) else '',
                'state': str(row.get('state', '')) if pd.notna(row.get('state')) else '',
                'county': 'Unknown',
                'zip': str(row.get('zip', '')) if pd.notna(row.get('zip')) else '',
                'street': row.get('address', ''),
                'reported_count': 1,
                'url': row.get('url', ''),
                'title': row.get('title', ''),
                'date': row.get('scrape_date', '')
            }
        
        # Clean location data
        location_data = self.clean_location_data(row)
        city = location_data['city']
        state = location_data['state']
        
        # If no city information, omit the entry
        if not city:
            return None
        
        # Try to get coordinates for the city
        coordinates = self.get_city_coordinates(city, state)
        
        if coordinates:
            lat, lon = coordinates
            return {
                'id': row.get('id', ''),
                'location': row.get('address', ''),
                'latitude': lat,
                'longitude': lon,
                'city': city,
                'state': state,
                'county': 'Unknown',
                'zip': str(row.get('zip', '')) if pd.notna(row.get('zip')) else '',
                'street': row.get('address', ''),
                'reported_count': 1,
                'url': row.get('url', ''),
                'title': row.get('title', ''),
                'date': row.get('scrape_date', '')
            }
        else:
            # Could not get coordinates, omit the entry
            return None
    
    def process_csv(self, input_file: str, output_file: str):
        """
        Process the CSV file and export to the specified format.
        """
        logger.info(f"Reading CSV file: {input_file}")
        
        # Read the CSV file
        df = pd.read_csv(input_file)
        logger.info(f"Loaded {len(df)} rows from CSV")
        
        # Process each row
        processed_rows = []
        
        for index, row in df.iterrows():
            if index % 100 == 0:
                logger.info(f"Processing row {index + 1}/{len(df)}")
            
            processed_row = self.process_row(row)
            if processed_row:
                processed_rows.append(processed_row)
        
        # Create output DataFrame
        output_df = pd.DataFrame(processed_rows)
        
        # Ensure all required columns are present
        required_columns = ['id', 'location', 'latitude', 'longitude', 'city', 'state', 
                          'county', 'zip', 'street', 'reported_count', 'url', 'title', 'date']
        
        for col in required_columns:
            if col not in output_df.columns:
                output_df[col] = ''
        
        # Reorder columns to match the required format
        output_df = output_df[required_columns]
        
        # Export to CSV
        logger.info(f"Exporting {len(output_df)} processed rows to {output_file}")
        output_df.to_csv(output_file, index=False)
        
        logger.info(f"Processing complete. Exported {len(output_df)} rows to {output_file}")
        
        return output_df

def merge_with_arrests_data():
    """
    Merge the new articles data with the arrests data and export to arrests_with_titles2.csv
    """
    # Read both CSV files
    new_articles_file = "/Users/jackvu/Desktop/latex_projects/icemap/data/new_articles.csv"
    arrests_file = "/Users/jackvu/Desktop/latex_projects/icemap/data/distilled_data/arrests_with_titles.csv"
    output_file = "/Users/jackvu/Desktop/latex_projects/icemap/data/distilled_data/arrests_with_titles2.csv"
    
    logger.info(f"Reading new articles file: {new_articles_file}")
    new_articles_df = pd.read_csv(new_articles_file)
    
    logger.info(f"Reading arrests file: {arrests_file}")
    arrests_df = pd.read_csv(arrests_file)
    
    logger.info(f"New articles rows: {len(new_articles_df)}")
    logger.info(f"Arrests rows: {len(arrests_df)}")
    
    # Combine the dataframes
    combined_df = pd.concat([arrests_df, new_articles_df], ignore_index=True)
    
    # Remove duplicates based on id
    combined_df = combined_df.drop_duplicates(subset=['id'], keep='first')
    
    logger.info(f"Combined rows (after removing duplicates): {len(combined_df)}")
    
    # Export to CSV
    logger.info(f"Exporting combined data to {output_file}")
    combined_df.to_csv(output_file, index=False)
    
    logger.info(f"Merge complete. Exported {len(combined_df)} rows to {output_file}")
    
    return combined_df

def main():
    """
    Main function to run the processing script.
    """
    input_file = "/Users/jackvu/Desktop/latex_projects/icemap/data/mediacloud_report_processed.csv"
    output_file = "/Users/jackvu/Desktop/latex_projects/icemap/data/new_articles.csv"
    
    processor = CityCoordinateProcessor()
    result_df = processor.process_csv(input_file, output_file)
    
    print(f"Processing complete!")
    print(f"Input rows: {len(pd.read_csv(input_file))}")
    print(f"Output rows: {len(result_df)}")
    print(f"Output saved to: {output_file}")
    
    # Now merge with arrests data
    print("\nMerging with arrests data...")
    merged_df = merge_with_arrests_data()
    print(f"Merged data saved to: /Users/jackvu/Desktop/latex_projects/icemap/data/distilled_data/arrests_with_titles2.csv")
    print(f"Total merged rows: {len(merged_df)}")

if __name__ == "__main__":
    main()
