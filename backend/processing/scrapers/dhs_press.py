import requests
import csv
from bs4 import BeautifulSoup
import time
from tqdm import tqdm

def has_next_page(soup):
    """Check if there is a next page available by looking for the Next button."""
    next_page = soup.find('a', class_='usa-pagination__next-page')
    return next_page is not None

def fetch_dhs_press_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    base_url = "https://www.dhs.gov/all-news-updates"
    params = {
        'combine': 'ice',
        'created': '',
        'field_news_type_target_id': 'All',
        'field_taxonomy_topics_target_id': 'All',
        'items_per_page': '50'
    }
    current_page = 0
    all_reports = []
    
    # Create progress bar with initial description
    pbar = tqdm(desc="Scraping DHS press pages", unit="page")
    
    while True:
        # Construct URL with page parameter
        if current_page > 0:
            params['page'] = current_page
        
        try:
            response = requests.get(base_url, params=params, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            news_items = soup.find_all('div', class_='news-updates')
            
            if not news_items:  # If no news items found, we've reached the end
                break
                
            for item in news_items:
                try:
                    # Get date and type
                    date_type_div = item.find('div', class_='news-updates-date-type')
                    date = 'N/A'
                    news_type = 'N/A'
                    
                    if date_type_div:
                        date_span = date_type_div.find('time')
                        if date_span:
                            date = date_span.text.strip()
                        
                        type_span = date_type_div.find('span', class_='news-type')
                        if type_span:
                            news_type = type_span.text.strip()
                    
                    # Get title and link
                    title_div = item.find('h3', class_='news-updates-title')
                    title = 'N/A'
                    link = 'N/A'
                    
                    if title_div:
                        article = title_div.find('a')
                        if article:
                            title = article.text.strip()
                            link = "https://www.dhs.gov" + article['href'] if article['href'].startswith('/') else article['href']
                    
                    all_reports.append({
                        'title': title,
                        'link': link,
                        'date': date,
                        'type': news_type
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

def save_to_csv(reports, filename='dhs_press_reports.csv'):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['title', 'link', 'date', 'type'])
        writer.writeheader()
        for report in reports:
            writer.writerow(report)

if __name__ == "__main__":
    reports = fetch_dhs_press_data()
    save_to_csv(reports)
