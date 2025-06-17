import requests
import csv
from bs4 import BeautifulSoup
import time
from tqdm import tqdm

def has_next_page(soup):
    """Check if there is a next page available by looking for the Next button."""
    next_page = soup.find('a', class_='usa-pagination__next-page')
    return next_page is not None

def fetch_foia_library_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    base_url = "https://www.ice.gov/foia/library"
    current_page = 0
    all_entries = []
    
    # Create progress bar with initial description
    pbar = tqdm(desc="Scraping FOIA library pages", unit="page")
    
    while True:
        # Construct URL with page parameter
        url = f"{base_url}?page={current_page}" if current_page > 0 else base_url
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            entries = soup.find_all('li', class_='usa-collection__item')
            
            if not entries:  # If no entries found, we've reached the end
                break
                
            for entry in entries:
                try:
                    # Get date
                    date_div = entry.find('time')
                    date = date_div.text.strip() if date_div else 'N/A'
                    
                    # Get title and link
                    title_div = entry.find('h4', class_='usa-collection__heading')
                    if not title_div:
                        continue
                        
                    article = title_div.find('a')
                    if not article:
                        continue
                        
                    title = article.text.strip()
                    link = article['href'] if article['href'].startswith('http') else f"https://www.ice.gov{article['href']}"
                    
                    # Get category (the text after the | symbol)
                    category = 'N/A'
                    if '|' in title:
                        title, category = [part.strip() for part in title.split('|', 1)]
                    
                    all_entries.append({
                        'title': title,
                        'link': link,
                        'date': date,
                        'category': category
                    })
                except Exception as e:
                    print(f"Error processing entry: {e}")
                    continue
            
            # Update progress bar with current page and items count
            pbar.set_postfix({'items': len(all_entries)})
            pbar.update(1)
            
            # Check if there's a next page
            if not has_next_page(soup):
                break
                
            current_page += 1
            # Add a small delay to be respectful to the server
            time.sleep(1)
            
        except Exception as e:
            print(f"Error fetching page {current_page}: {e}")
            break
    
    pbar.close()
    return all_entries

def save_to_csv(entries, filename='foia_library_entries.csv'):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['title', 'link', 'date', 'category'])
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry)

if __name__ == "__main__":
    entries = fetch_foia_library_data()
    save_to_csv(entries)
