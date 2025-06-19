import requests
import csv
from bs4 import BeautifulSoup
import time
from tqdm import tqdm

def has_next_page(soup):
    """Check if there is a next page available by looking for the Next button text."""
    next_page = soup.find('span', class_='usa-pagination__link-text', string=' Next ')
    return next_page is not None

def fetch_newsroom_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    base_url = "https://www.ice.gov/newsroom"
    current_page = 0
    all_reports = []
    
    # Create progress bar with initial description
    pbar = tqdm(desc="Scraping pages", unit="page")
    
    while True:
        # Construct URL with page parameter
        url = f"{base_url}?page={current_page}" if current_page > 0 else base_url
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            news_items = soup.find_all('div', class_='views-row')
            
            if not news_items:  # If no news items found, we've reached the end
                break
                
            for item in news_items:
                try:
                    # Find the news wrapper div
                    news_wrapper = item.find('div', class_='news-wrapper')
                    if not news_wrapper:
                        continue

                    # Get title and link from news-title
                    title_div = news_wrapper.find('div', class_='news-title')
                    if not title_div:
                        continue
                        
                    article = title_div.find('a')
                    if not article:
                        continue
                        
                    title = article.text.strip()
                    link = "https://www.ice.gov" + article['href'] if article['href'].startswith('/') else article['href']
                    
                    # Get date from news-date
                    date_div = news_wrapper.find('div', class_='news-date')
                    date = date_div.text.strip() if date_div else 'N/A'
                    
                    # Get summary from news-body
                    summary_div = news_wrapper.find('div', class_='news-body')
                    summary = summary_div.text.strip() if summary_div else 'N/A'
                    
                    all_reports.append({
                        'title': title,
                        'link': link,
                        'summary': summary,
                        'date': date
                    })
                except Exception as e:
                    print(f"Error processing item: {e}")
                    continue
            
            # Update progress bar with current page and items count
            pbar.set_postfix({'items': len(all_reports)})
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
    return all_reports

def save_to_csv(reports, filename='newsroom_reports.csv'):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['title', 'link', 'summary', 'date'])
        writer.writeheader()
        for report in reports:
            writer.writerow(report)

if __name__ == "__main__":
    reports = fetch_newsroom_data()
    save_to_csv(reports)
