import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import json
import os
from tqdm import tqdm

def load_existing_posts():
    """Load existing posts from CSV if it exists"""
    if os.path.exists('lamigra_posts.csv'):
        return pd.read_csv('lamigra_posts.csv')
    return pd.DataFrame(columns=['title', 'description', 'date', 'link'])

def save_posts(posts_df, new_posts):
    """Save new posts to CSV"""
    if len(new_posts) > 0:
        new_df = pd.DataFrame(new_posts)
        combined_df = pd.concat([posts_df, new_df], ignore_index=True)
        # Remove duplicates based on link
        combined_df = combined_df.drop_duplicates(subset=['link'])
        combined_df.to_csv('lamigra_posts.csv', index=False)
        return combined_df
    return posts_df

def scrape_lamigra_posts():
    # Load existing posts
    posts_df = load_existing_posts()
    existing_links = set(posts_df['link'].tolist())
    
    # Initialize list to store new posts
    new_posts = []
    
    # Base URL for the subreddit
    base_url = 'https://www.reddit.com/r/LaMigra/search.json'
    
    # Headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Parameters for the search
    params = {
        'q': 'flair:"ICE Spotting"',
        'restrict_sr': 'on',
        'sort': 'new',
        't': 'all',
        'limit': 100
    }
    
    after = None
    consecutive_duplicates = 0
    max_consecutive_duplicates = 5  # Stop if we see too many duplicates in a row
    
    print("Starting to scrape posts...")
    
    while True:
        if after:
            params['after'] = after
            
        try:
            # Make the request
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            
            # Parse the JSON response
            data = response.json()
            
            # Check if we got any posts
            if not data['data']['children']:
                print("No more posts found.")
                break
            
            # Track if we found any new posts in this batch
            found_new = False
            
            # Extract posts
            for post in data['data']['children']:
                post_data = post['data']
                post_link = f'https://www.reddit.com{post_data["permalink"]}'
                
                # Skip if we've already seen this post
                if post_link in existing_links:
                    continue
                
                found_new = True
                consecutive_duplicates = 0
                
                # Convert timestamp to datetime
                post_date = datetime.fromtimestamp(post_data['created_utc'])
                
                # Append post data to list
                new_posts.append({
                    'title': post_data['title'],
                    'description': post_data['selftext'],
                    'date': post_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'link': post_link
                })
                
                existing_links.add(post_link)
            
            if not found_new:
                consecutive_duplicates += 1
                print(f"No new posts found in this batch. Consecutive duplicates: {consecutive_duplicates}")
                if consecutive_duplicates >= max_consecutive_duplicates:
                    print("Too many consecutive duplicates, stopping...")
                    break
            
            # Save progress every 100 posts
            if len(new_posts) >= 100:
                print(f"Saving {len(new_posts)} new posts...")
                posts_df = save_posts(posts_df, new_posts)
                new_posts = []
            
            # Get the 'after' parameter for pagination
            after = data['data']['after']
            
            # If there are no more posts, break the loop
            if not after:
                print("Reached the end of available posts.")
                break
                
            # Be nice to Reddit's servers
            time.sleep(2)
            
        except Exception as e:
            print(f"Error occurred: {e}")
            # Save any posts we've collected so far
            if new_posts:
                posts_df = save_posts(posts_df, new_posts)
            break
    
    # Save any remaining posts
    if new_posts:
        posts_df = save_posts(posts_df, new_posts)
    
    print(f"Scraping complete. Total posts collected: {len(posts_df)}")

if __name__ == '__main__':
    scrape_lamigra_posts()
