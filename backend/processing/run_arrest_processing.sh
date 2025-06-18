#!/bin/bash

# Script to run arrest processing
# This script processes ICE arrest articles and extracts geographic locations

set -e  # Exit on any error

echo "Starting ICE arrest processing..."

# Check if we're in the right directory
if [ ! -f "arrest_processing.py" ]; then
    echo "Error: arrest_processing.py not found in current directory"
    echo "Please run this script from the processing directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found"
    echo "Please create a .env file with the following variables:"
    echo "DEEPSEEK_API_KEY=your_deepseek_api_key"
    echo "GOOGLE_PLACES_API_KEY=your_google_places_api_key (optional)"
    echo ""
    echo "You can still run the script, but Google Places enhancement will be skipped."
fi

# Install dependencies if needed
echo "Installing dependencies..."
pip install -r requirements.txt

# Run the arrest processing script
echo "Running arrest processing..."
python arrest_processing.py

echo "Arrest processing completed!"
echo "Check data/distilled_data/arrests.csv for the output." 