# ICE Map Frontend

A minimalist React application that displays ICE arrest locations on an interactive map using Leaflet.

## Features

- Interactive map showing all arrest locations from the CSV data
- Click on markers to view detailed information about each arrest
- Responsive design that works on desktop and mobile
- Clean, minimalist interface

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

3. Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

## Data

The application reads arrest data from `public/arrests.csv`. The CSV file should contain the following columns:
- `latitude`: Latitude coordinate
- `longitude`: Longitude coordinate  
- `location`: Location name
- `city`: City name
- `state`: State name
- `county`: County name
- `street`: Street address
- `reported_count`: Number of arrests reported
- `url`: Source URL for the arrest information

## Technologies Used

- React 18
- Leaflet (via react-leaflet)
- OpenStreetMap tiles
- CSS3 for styling

## Build for Production

To create a production build:

```bash
npm run build
```

This creates an optimized build in the `build` folder. 