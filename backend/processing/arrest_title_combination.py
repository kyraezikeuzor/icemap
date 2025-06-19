import pandas as pd
import os

def combine_arrests_with_titles():
    """
    Script to combine arrests.csv with titles from articles.csv based on matching IDs.
    Then merges dates from mediacloud_articles.csv based on matching titles.
    Creates a new arrests.csv file with the title and date columns added.
    """
    
    # Define file paths
    data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'distilled_data')
    arrests_file = os.path.join(data_dir, 'arrests.csv')
    articles_file = os.path.join(data_dir, 'articles.csv')
    mediacloud_file = os.path.join(data_dir, '..', 'mediacloud_articles.csv')
    output_file = os.path.join(data_dir, 'arrests_with_titles.csv')
    
    print(f"Reading arrests data from: {arrests_file}")
    print(f"Reading articles data from: {articles_file}")
    print(f"Reading mediacloud articles data from: {mediacloud_file}")
    
    try:
        # Read the CSV files
        arrests_df = pd.read_csv(arrests_file)
        articles_df = pd.read_csv(articles_file)
        mediacloud_df = pd.read_csv(mediacloud_file)
        
        print(f"Loaded {len(arrests_df)} arrest records")
        print(f"Loaded {len(articles_df)} article records")
        print(f"Loaded {len(mediacloud_df)} mediacloud article records")
        
        # Create mapping of id to title from articles
        id_to_title = dict(zip(articles_df['id'], articles_df['title']))
        
        # Add title column to arrests dataframe
        arrests_df['title'] = arrests_df['id'].map(id_to_title)
        
        # Count how many matches were found from articles
        matches_found = arrests_df['title'].notna().sum()
        print(f"Found titles for {matches_found} out of {len(arrests_df)} arrest records from articles.csv")
        
        # Create mapping of title to date from mediacloud articles
        title_to_mediacloud_date = dict(zip(mediacloud_df['title'], mediacloud_df['date']))
        
        # Add date column and populate from mediacloud articles where titles match
        arrests_df['date'] = None
        mediacloud_matches = 0
        for idx, row in arrests_df.iterrows():
            if pd.notna(row['title']) and row['title'] in title_to_mediacloud_date:
                arrests_df.at[idx, 'date'] = title_to_mediacloud_date[row['title']]
                mediacloud_matches += 1
        
        print(f"Found dates for {mediacloud_matches} records from mediacloud_articles.csv")
        
        # Save the combined data
        arrests_df.to_csv(output_file, index=False)
        print(f"Combined data saved to: {output_file}")
        
        # Show some statistics
        print(f"\nSummary:")
        print(f"- Total arrest records: {len(arrests_df)}")
        print(f"- Records with titles: {matches_found}")
        print(f"- Records without titles: {len(arrests_df) - matches_found}")
        print(f"- Records with dates from mediacloud: {mediacloud_matches}")
        
        # Show a few sample records with titles
        print(f"\nSample records with titles:")
        sample_records = arrests_df[arrests_df['title'].notna()].head(3)
        for idx, row in sample_records.iterrows():
            print(f"ID: {row['id']}")
            print(f"Title: {row['title']}")
            print(f"Date: {row['date']}")
            print(f"Location: {row['location']}")
            print("-" * 50)
            
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
    except Exception as e:
        print(f"Error processing files: {e}")

if __name__ == "__main__":
    combine_arrests_with_titles()
