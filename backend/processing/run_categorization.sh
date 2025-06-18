#!/bin/bash

# Article Categorization Runner Script
# This script sets up the environment and runs the categorization process

set -e  # Exit on any error

echo "=========================================="
echo "Article Categorization Script"
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "categorization.py" ]; then
    echo "Error: Please run this script from the processing directory"
    echo "Current directory: $(pwd)"
    echo "Expected files: categorization.py, batch_categorization.py"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if required packages are installed
echo "Checking dependencies..."
python3 -c "import requests" 2>/dev/null || {
    echo "Installing required packages..."
    pip3 install -r requirements.txt
}

# Check if API key is set
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "Error: DEEPSEEK_API_KEY environment variable is not set"
    echo ""
    echo "Please set your DeepSeek API key:"
    echo "export DEEPSEEK_API_KEY='your-api-key-here'"
    echo ""
    echo "You can get a DeepSeek API key from: https://platform.deepseek.com/"
    exit 1
fi

# Check if input file exists
INPUT_FILE="../../data/mediacloud_articles.csv"
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file not found: $INPUT_FILE"
    echo "Please ensure the medicloud_articles.csv file exists in the data directory"
    exit 1
fi

echo "Setup complete!"
echo "Input file: $INPUT_FILE"
echo "Output file: ../../data/articles.csv"
echo ""

# Ask user which script to run
echo "Choose processing method:"
echo "1. Standard processing (categorization.py)"
echo "2. Batch processing with resume capability (batch_categorization.py)"
echo "3. Test mode (test_categorization.py)"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo "Running standard categorization..."
        python3 categorization.py
        ;;
    2)
        echo "Running batch categorization..."
        python3 batch_categorization.py
        ;;
    3)
        echo "Running test mode..."
        python3 test_categorization.py
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Processing completed!"
echo "=========================================="

# Check if output file was created
OUTPUT_FILE="../../data/articles.csv"
if [ -f "$OUTPUT_FILE" ]; then
    echo "Output file created: $OUTPUT_FILE"
    echo "Number of articles processed: $(wc -l < "$OUTPUT_FILE" | awk '{print $1-1}')"
else
    echo "Warning: Output file was not created"
fi 