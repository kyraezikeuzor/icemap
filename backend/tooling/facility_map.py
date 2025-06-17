import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap

def plot_facilities_on_map():
    # Load the data
    input_file = "data/ice_facilities_with_coordinates.csv"
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}")
        return

    # Count total facilities
    total_facilities = len(df)
    
    # Filter out rows without coordinates
    df = df.dropna(subset=['Latitude', 'Longitude'])
    
    # Count facilities with valid coordinates
    valid_facilities = len(df)
    print(f"Total facilities: {total_facilities}")
    print(f"Facilities with valid coordinates: {valid_facilities}")
    print(f"Facilities without coordinates (ignored): {total_facilities - valid_facilities}")

    # Set up the map
    plt.figure(figsize=(12, 8))
    m = Basemap(projection='lcc', resolution='h',
                lat_0=41.5, lon_0=-98,  # Centered on Nebraska
                width=4E6, height=3E6)  # Adjusted width and height for better US coverage

    m.shadedrelief()
    m.drawcoastlines(color='gray')
    m.drawcountries(color='gray')
    m.drawstates(color='gray')

    # Plot each facility
    for idx, row in df.iterrows():
        x, y = m(row['Longitude'], row['Latitude'])
        m.plot(x, y, 'ro', markersize=5)

    # Add title
    plt.title("72-hour ICE Detention Facilities", fontsize=15)

    # Show the plot
    plt.show()

if __name__ == "__main__":
    plot_facilities_on_map()
