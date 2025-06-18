# Article Categorization Script

This script uses the DeepSeek API to categorize medicloud articles into specific categories and outputs them in the required CSV format.

## Setup

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Set up DeepSeek API key:**

   ```bash
   export DEEPSEEK_API_KEY="your-deepseek-api-key-here"
   ```
   
   You can get a DeepSeek API key from: https://platform.deepseek.com/

## Usage

Run the script from the project root directory:

```bash
python icemap/backend/processing/categorization.py
```

## Input/Output

- **Input:** `icemap/data/mediacloud_articles.csv`
- **Output:** `icemap/data/articles.csv`

## Categories

The script categorizes articles into these specific categories:

- **raid**: Articles about ICE raids, workplace raids, immigration enforcement operations
- **arrest**: Articles about arrests, detentions, or apprehensions by law enforcement
- **detention**: Articles about detention centers, holding facilities, or prolonged custody
- **protest**: Articles about protests, demonstrations, marches, or civil unrest
- **policy**: Articles about immigration policies, laws, regulations, or government decisions
- **opinion**: Articles that are clearly opinion pieces, editorials, or commentary
- **other**: Articles that don't fit into the above categories

## Publisher Handling

The script uses a two-tier approach for publisher identification:

### Mainstream Publishers
For recognized mainstream publishers (NYTimes, FoxNews, CNN, etc.), the script:
- Extracts publisher name from the URL domain
- Uses simple category-only API calls for efficiency
- Returns just the category name

### Non-Mainstream Publishers
For unknown or non-mainstream publishers, the script:
- Makes JSON-formatted API calls to DeepSeek
- Requests both category and proper publisher label
- DeepSeek provides a proper, recognizable publisher name
- Returns both category and publisher in JSON format

**Example API responses:**
- Mainstream: `"raid"`
- Non-mainstream: `{"category": "raid", "publisher": "Local Community News"}`

## Output Format

The output CSV will have the following columns:

- `id`: Unique identifier for each article
- `title`: Article title
- `publisher`: Extracted from URL or provided by DeepSeek
- `scrape_date`: Set to "6/18/2025" for all articles
- `category`: One of the seven categories listed above
- `url`: Original article URL

## Features

- **Smart Publisher Detection**: Automatically identifies mainstream vs non-mainstream publishers
- **DeepSeek Publisher Labeling**: AI-generated proper publisher names for unknown sources
- **Rate limiting**: 1 second delay between API calls to avoid rate limits
- **Error handling**: Invalid categories default to "other"
- **Progress tracking**: Shows categorization progress and final distribution
- **Validation**: Ensures all categories are from the approved list
- **JSON Response Handling**: Properly parses both simple and JSON API responses

## Mainstream Publishers Recognized

The script recognizes major news outlets including:
- National: NYTimes, WashingtonPost, USAToday, FoxNews, CNN, NBCNews, CBSNews, ABCNews
- International: Reuters, Bloomberg, Forbes, Time, Newsweek, BBC, Guardian
- Regional: LATimes, ChicagoTribune, BostonGlobe, DenverPost, BaltimoreSun
- And many more...

## Notes

- The script processes all articles in the input CSV file
- Each article is categorized using the DeepSeek API
- The scrape_date is set to "6/18/2025" for all articles as requested
- Publisher names are either extracted from URLs or provided by DeepSeek
- Non-mainstream publishers get more detailed API calls for better publisher identification
