# Article Categorization Solution

This solution provides a complete system for categorizing medicloud articles using the DeepSeek API and outputting them in the required CSV format.

## Overview

The system processes articles from `icemap/data/mediacloud_articles.csv` and categorizes each article into one of seven specific categories:
- **raid**: ICE raids, workplace raids, immigration enforcement operations
- **arrest**: Arrests, detentions, or apprehensions by law enforcement
- **detention**: Detention centers, holding facilities, or prolonged custody
- **protest**: Protests, demonstrations, marches, or civil unrest
- **policy**: Immigration policies, laws, regulations, or government decisions
- **opinion**: Opinion pieces, editorials, or commentary
- **other**: Articles that don't fit into the above categories

## Smart Publisher Handling

The solution implements intelligent publisher identification with two approaches:

### Mainstream Publishers
For recognized major news outlets (NYTimes, FoxNews, CNN, etc.):
- **Simple API calls**: Only request category classification
- **URL extraction**: Publisher name extracted from domain
- **Efficient processing**: Faster and cheaper API usage

### Non-Mainstream Publishers
For unknown or smaller publishers:
- **JSON API calls**: Request both category and publisher label
- **AI-generated labels**: DeepSeek provides proper publisher names
- **Better identification**: More accurate publisher labeling

**API Response Examples:**
- Mainstream: `"raid"`
- Non-mainstream: `{"category": "raid", "publisher": "Local Community News"}`

## Files Created

### Core Scripts
- **`categorization.py`**: Main categorization script with smart publisher handling
- **`batch_categorization.py`**: Advanced batch processing with resume capability
- **`test_categorization.py`**: Test script for verification

### Support Files
- **`requirements.txt`**: Python dependencies
- **`run_categorization.sh`**: Easy-to-use shell script
- **`README.md`**: Detailed usage instructions
- **`SOLUTION_SUMMARY.md`**: This summary document

## Quick Start

1. **Set up your DeepSeek API key:**
   ```bash
   export DEEPSEEK_API_KEY="your-api-key-here"
   ```

2. **Navigate to the processing directory:**
   ```bash
   cd icemap/backend/processing
   ```

3. **Run the categorization:**
   ```bash
   ./run_categorization.sh
   ```

## Detailed Usage

### Option 1: Standard Processing
```bash
python3 categorization.py
```
- Processes all articles sequentially
- Smart publisher detection and handling
- Good for smaller datasets

### Option 2: Batch Processing (Recommended)
```bash
python3 batch_categorization.py
```
- Processes articles in batches of 10
- Resume capability if interrupted
- Better error handling and progress tracking
- Estimated time remaining
- Checkpoint saving

### Option 3: Test Mode
```bash
python3 test_categorization.py
```
- Tests with sample articles
- Verifies API connectivity
- Tests publisher extraction and classification
- Tests CSV output format

## Output Format

The script creates `icemap/data/articles.csv` with the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| `id` | Unique identifier | `550e8400-e29b-41d4-a716-446655440000` |
| `title` | Article title | `"ICE agents raid Los Angeles restaurant"` |
| `publisher` | Extracted or AI-generated | `"Latimes"` or `"Local Community News"` |
| `scrape_date` | Fixed date | `"6/18/2025"` |
| `category` | One of 7 categories | `"raid"` |
| `url` | Original article URL | `"https://www.latimes.com/..."` |

## Features

### Smart Publisher Detection
- Automatically identifies mainstream vs non-mainstream publishers
- Comprehensive list of recognized major news outlets
- Efficient API usage based on publisher type

### DeepSeek Publisher Labeling
- AI-generated proper publisher names for unknown sources
- JSON response parsing for non-mainstream publishers
- Fallback handling for malformed responses

### Rate Limiting
- 1-second delay between API calls
- Prevents hitting API rate limits
- Configurable in the code

### Error Handling
- Invalid categories default to "other"
- Failed articles are logged
- API errors are caught and handled gracefully
- JSON parsing errors are handled

### Progress Tracking
- Real-time progress updates
- Estimated time remaining
- Category distribution statistics
- Publisher distribution statistics

### Resume Capability (Batch Mode)
- Saves progress to checkpoint file
- Can resume from where it left off
- Handles interruptions gracefully

## API Configuration

The script uses the DeepSeek API with optimized settings:
- **Model**: `deepseek-chat`
- **Temperature**: 0.1 (for consistent categorization)
- **Max tokens**: 10 (mainstream) or 50 (non-mainstream)
- **Timeout**: 30 seconds per request

## Mainstream Publishers Recognized

The system recognizes major news outlets including:
- **National**: NYTimes, WashingtonPost, USAToday, FoxNews, CNN, NBCNews, CBSNews, ABCNews
- **International**: Reuters, Bloomberg, Forbes, Time, Newsweek, BBC, Guardian, Independent
- **Regional**: LATimes, ChicagoTribune, BostonGlobe, DenverPost, BaltimoreSun
- **Local**: Various state and city newspapers
- **And many more**...

## Sample Output

```
Starting article categorization...
Input file: icemap/data/mediacloud_articles.csv
Output file: icemap/data/articles.csv
Categories: raid, arrest, detention, protest, policy, opinion, other

Categorizing: NYC mayoral candidate Brad Lander arrested at immigration court...
  ✓ Category: arrest, Publisher: Newsday (MAINSTREAM)

Categorizing: Local blog reports on ICE activity in community...
  ✓ Category: raid, Publisher: Community Immigration Watch (NON-MAINSTREAM)

...

Processed 3001 articles. Output saved to icemap/data/articles.csv

Category distribution:
  raid: 245
  arrest: 567
  detention: 189
  protest: 423
  policy: 312
  opinion: 156
  other: 1109
```

## Troubleshooting

### Common Issues

1. **API Key Not Set**
   ```
   Error: DEEPSEEK_API_KEY environment variable is not set.
   ```
   Solution: Set your API key with `export DEEPSEEK_API_KEY="your-key"`

2. **Input File Not Found**
   ```
   Error: Input file icemap/data/mediacloud_articles.csv not found.
   ```
   Solution: Ensure the CSV file exists in the correct location

3. **API Rate Limits**
   ```
   Error: 429 Too Many Requests
   ```
   Solution: The script includes rate limiting, but you may need to increase delays

4. **JSON Parsing Errors**
   ```
   Warning: Invalid JSON response for article...
   ```
   Solution: The script handles this automatically by defaulting to "other"

### Performance Tips

- Use batch processing for large datasets
- The script can be interrupted and resumed
- Monitor the checkpoint file for progress
- Consider running during off-peak hours

## Data Quality

The script ensures data quality through:
- Input validation (title and URL required)
- Category validation (only approved categories)
- Smart publisher identification and labeling
- Consistent date formatting
- Unique ID generation
- JSON response validation

## Extensibility

The solution is designed to be easily extensible:
- Add new categories by modifying the `CATEGORIES` list
- Add new mainstream publishers to `MAINSTREAM_PUBLISHERS`
- Adjust rate limiting by changing the `time.sleep()` delay
- Modify publisher extraction logic for new domains
- Add new output formats by extending the CSV writer

## Cost Considerations

- DeepSeek API charges per request
- Mainstream publishers use fewer tokens (cheaper)
- Non-mainstream publishers use more tokens (more expensive)
- Each article requires one API call
- With 3000+ articles, expect significant API usage
- Monitor your API usage and costs

## Security

- API key is stored as environment variable
- No hardcoded credentials
- HTTPS requests to DeepSeek API
- Input validation prevents injection attacks
- JSON response validation prevents parsing attacks 