# City Immigration Activity Summaries

This component shows immigration activity summaries for major US cities when users click on city markers on the map.

## How It Works

1. **Pre-generated Summaries**  
   Instead of generating summaries dynamically when users click on cities (which was too slow), we now pre-generate summaries for all cities and save them to a JSON file.

2. **Summary Generation**  
   The `/backend/scripts/generate_city_summaries.py` script:
   - Uses the DeepSeek API to generate concise summaries for each city
   - Analyzes arrests, incidents, and news articles data
   - Saves all summaries to `/frontend/public/city_summaries.json`
   - Includes timestamps of when each summary was generated

3. **Frontend Integration**  
   The `CityMarkers.js` component:
   - Loads the pre-generated summaries from `city_summaries.json` on component mount
   - Displays city markers on the map when zoomed in enough (zoom level 6+)
   - Shows a tooltip with city name and state on hover
   - When a marker is clicked, instantly displays the pre-generated summary in a popup

## Refreshing Summaries

To update the summaries with the latest data:

```bash
# Make sure you have the DeepSeek API key in your .env file
source .venv/bin/activate
python backend/scripts/generate_city_summaries.py
```

This will regenerate all city summaries and update the JSON file. The next time users visit the site, they'll see the updated summaries.

## Customization

- To add more cities, update the `CITIES` array in `generate_city_summaries.py` and the `cities` array in `CityMarkers.js`
- To change the appearance of city markers or popups, modify `CityMarkers.css`
- To customize the summary format, edit the prompt in `generate_summary_with_deepseek()` function in `city_summaries.py`
