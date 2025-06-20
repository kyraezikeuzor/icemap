#!/bin/bash
# Start the city summaries API service

# Ensure we're in the correct directory
cd "$(dirname "$0")"
cd ..

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Start the Flask app
python backend/api/city_summaries.py
