import pandas as pd
import re

def process_facilities_excel(input_file, output_file):
    # Read the Excel file
    df = pd.read_excel(input_file, header=None)
    
    # Initialize lists to store the processed data
    facilities = []
    current_aor = None
    
    # Process each row
    for index, row in df.iterrows():
        # Convert row to string and strip whitespace
        row_str = str(row[0]).strip()
        
        # Skip empty rows and headers
        if pd.isna(row_str) or row_str == 'nan' or 'Facility Name' in row_str:
            continue
            
        # Check if this is an AOR header
        if row_str.endswith('AOR'):
            current_aor = row_str
            continue
            
        # If we have a valid row with facility data
        if current_aor and len(row) >= 4:
            facility_name = str(row[0]).strip()
            city = str(row[1]).strip()
            state = str(row[2]).strip()
            facility_type = str(row[3]).strip()
            
            # Skip if any of the required fields are empty or 'nan'
            if any(x == 'nan' or not x for x in [facility_name, city, state, facility_type]):
                continue
                
            facilities.append({
                'Facility Name': facility_name,
                'City': city,
                'State': state,
                'Facility Type': facility_type,
                'AOR': current_aor
            })
    
    # Create DataFrame and save to CSV
    result_df = pd.DataFrame(facilities)
    result_df.to_csv(output_file, index=False)
    print(f"Processed {len(facilities)} facilities. Output saved to {output_file}")

if __name__ == "__main__":
    input_file = "data/Over72HourFacilities.xlsx"  # Update this with your input file name
    output_file = "data/ice_facilities.csv"  # Update this with your desired output file name
    process_facilities_excel(input_file, output_file)
