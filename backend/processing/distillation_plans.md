## Distillation

#### Purpose

We need to:

- convert the wealth of news articles we currently have into structured data (location data, article type, sort into "types of incidents")

Current formatting idea. along the top are the fields, inside of the rows is a full list of examples:

### articles.csv

| id | title | publisher | scrape_date | category  | url |
| -- | ----- | --------- | ----------- | --------- | --- |
|    |       |           | 6/18/2025   | raid      |     |
|    |       |           |             | arrest    |     |
|    |       |           |             | detention |     |
|    |       |           |             | protest   |     |
|    |       |           |             | policy    |     |
|    |       |           |             | opinion   |     |
|    |       |           |             | other     |     |

After preprocessing these articles and sorting by category, our first step will be to make use of the articles that are the most immediately interesting. These are arrests, followed by raids, followed by detentions. Here's what we'll work on first, which will be what the first iteration of the website exclusively shows. We'll task deepseek (after providing the article's text to the fullest extent possible) with finding location, addresses, etc, which we will then plug into google places to find lattitude and longitude.

### arrests.csv

| id | location | latitude | city | state | county | zip | street | reported_count | url |
| -- | -------- | -------- | ---- | ----- | ------ | --- | ------ | -------------- | --- |
|    |          |          |      |       |        |     |        |                |     |
|    |          |          |      |       |        |     |        |                |     |
