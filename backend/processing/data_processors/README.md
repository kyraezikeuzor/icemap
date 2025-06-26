# Missing Facilities Processor

This script processes detention center data to find facilities with low confidence levels and uses the Google Places API to get their coordinates.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Google Places API key:
   - Get a Google Places API key from the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a `.env` file in the same directory as the script
   - Add your API key to the `.env` file:
   ```
   GOOGLE_PLACES_API_KEY=your_api_key_here
   ```

## Usage

Run the script:
```bash
python missing_facilities.py
```

The script will:
1. Load the JSONL file with detention center data
2. Filter records with similarity scores below 0.9
3. Use Google Places API to find coordinates for each low-confidence facility
4. Save results to `low_confidence_facilities_results.json`
5. Display a summary of findings

## Output

The script generates:
- Console output showing progress and results
- A JSON file with detailed results including:
  - Original record data
  - Google Places API results (if found)
  - Status (found/not found)

## Configuration

You can modify the script to:
- Change the similarity score threshold (currently 0.9)
- Adjust the output file name
- Modify the data file path
- Add additional search parameters

## API Rate Limits

The script includes a small delay between API calls to avoid hitting rate limits. If you encounter rate limit issues, you can increase the delay in the `time.sleep(0.1)` call. 