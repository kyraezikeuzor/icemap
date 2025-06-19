#!/usr/bin/env python3
"""
Batch processing script for categorizing large numbers of articles.
Includes resume capability and better error handling for large datasets.
"""

import csv
import json
import time
import uuid
import os
import sys
from urllib.parse import urlparse
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pickle

# Import functions from main categorization script
from categorization import categorize_article_with_deepseek, extract_publisher_from_url, CATEGORIES

class BatchProcessor:
    def __init__(self, input_file: str, output_file: str, checkpoint_file: str = None):
        self.input_file = input_file
        self.output_file = output_file
        self.checkpoint_file = checkpoint_file or f"{output_file}.checkpoint"
        self.processed_articles = []
        self.failed_articles = []
        self.start_time = None
        
    def load_checkpoint(self):
        """Load progress from checkpoint file if it exists."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'rb') as f:
                    checkpoint_data = pickle.load(f)
                    self.processed_articles = checkpoint_data.get('processed', [])
                    self.failed_articles = checkpoint_data.get('failed', [])
                    print(f"Loaded checkpoint: {len(self.processed_articles)} articles processed, {len(self.failed_articles)} failed")
                    return True
            except Exception as e:
                print(f"Error loading checkpoint: {e}")
        return False
    
    def save_checkpoint(self):
        """Save current progress to checkpoint file."""
        checkpoint_data = {
            'processed': self.processed_articles,
            'failed': self.failed_articles,
            'timestamp': datetime.now().isoformat()
        }
        try:
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint_data, f)
        except Exception as e:
            print(f"Error saving checkpoint: {e}")
    
    def process_articles_batch(self, batch_size: int = 10, scrape_date: str = "6/18/2025"):
        """Process articles in batches with checkpointing."""
        
        # Load existing progress
        self.load_checkpoint()
        
        # Read all articles from input file
        all_articles = []
        with open(self.input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get('title', '').strip()
                description = row.get('description', '').strip()
                url = row.get('url', '').strip()
                
                if title and url:
                    all_articles.append({
                        'title': title,
                        'description': description,
                        'url': url
                    })
        
        # Filter out already processed articles
        processed_urls = {article['url'] for article in self.processed_articles}
        remaining_articles = [article for article in all_articles if article['url'] not in processed_urls]
        
        print(f"Total articles: {len(all_articles)}")
        print(f"Already processed: {len(self.processed_articles)}")
        print(f"Remaining to process: {len(remaining_articles)}")
        print()
        
        if not remaining_articles:
            print("All articles already processed!")
            return
        
        self.start_time = time.time()
        
        # Process in batches
        for i in range(0, len(remaining_articles), batch_size):
            batch = remaining_articles[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(remaining_articles) + batch_size - 1) // batch_size
            
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} articles)")
            
            for j, article in enumerate(batch):
                article_num = i + j + 1
                total_articles = len(remaining_articles)
                
                print(f"  [{article_num}/{total_articles}] Categorizing: {article['title'][:60]}...")
                
                try:
                    # Extract publisher from URL and check if mainstream
                    extracted_publisher, is_mainstream = extract_publisher_from_url(article['url'])
                    
                    # Categorize article
                    category, deepseek_publisher = categorize_article_with_deepseek(
                        article['title'], 
                        article['description'], 
                        article['url'],
                        is_mainstream
                    )
                    
                    # Use DeepSeek publisher if provided, otherwise use extracted publisher
                    final_publisher = deepseek_publisher if deepseek_publisher else extracted_publisher
                    
                    # Create article entry
                    processed_article = {
                        'id': str(uuid.uuid4()),
                        'title': article['title'],
                        'publisher': final_publisher,
                        'scrape_date': scrape_date,
                        'category': category,
                        'url': article['url']
                    }
                    
                    self.processed_articles.append(processed_article)
                    print(f"    ✓ Category: {category}, Publisher: {final_publisher}")
                    
                except Exception as e:
                    print(f"    ✗ Error: {e}")
                    self.failed_articles.append({
                        'title': article['title'],
                        'url': article['url'],
                        'error': str(e)
                    })
                
                # Rate limiting
                time.sleep(1)
            
            # Save checkpoint after each batch
            self.save_checkpoint()
            
            # Print progress
            elapsed_time = time.time() - self.start_time
            processed_count = len(self.processed_articles)
            remaining_count = len(remaining_articles) - (i + len(batch))
            
            if remaining_count > 0:
                avg_time_per_article = elapsed_time / processed_count
                estimated_remaining_time = remaining_count * avg_time_per_article
                print(f"  Progress: {processed_count}/{len(all_articles)} articles processed")
                print(f"  Estimated time remaining: {estimated_remaining_time/60:.1f} minutes")
            
            print()
        
        # Write final output
        self.write_output()
        
        # Print final statistics
        self.print_statistics()
    
    def write_output(self):
        """Write processed articles to output CSV file."""
        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['id', 'title', 'publisher', 'scrape_date', 'category', 'url']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for article in self.processed_articles:
                writer.writerow(article)
        
        print(f"Output saved to: {self.output_file}")
    
    def print_statistics(self):
        """Print final processing statistics."""
        print("\n" + "="*50)
        print("PROCESSING COMPLETED")
        print("="*50)
        
        total_processed = len(self.processed_articles)
        total_failed = len(self.failed_articles)
        
        print(f"Total articles processed: {total_processed}")
        print(f"Failed articles: {total_failed}")
        
        if self.start_time:
            total_time = time.time() - self.start_time
            print(f"Total processing time: {total_time/60:.1f} minutes")
            if total_processed > 0:
                avg_time = total_time / total_processed
                print(f"Average time per article: {avg_time:.1f} seconds")
        
        # Category distribution
        category_counts = {}
        for article in self.processed_articles:
            category = article['category']
            category_counts[category] = category_counts.get(category, 0) + 1
        
        print("\nCategory distribution:")
        for category in CATEGORIES:
            count = category_counts.get(category, 0)
            percentage = (count / total_processed * 100) if total_processed > 0 else 0
            print(f"  {category}: {count} ({percentage:.1f}%)")
        
        # Publisher distribution (top 10)
        publisher_counts = {}
        for article in self.processed_articles:
            publisher = article['publisher']
            publisher_counts[publisher] = publisher_counts.get(publisher, 0) + 1
        
        print("\nTop 10 publishers:")
        sorted_publishers = sorted(publisher_counts.items(), key=lambda x: x[1], reverse=True)
        for publisher, count in sorted_publishers[:10]:
            print(f"  {publisher}: {count}")
        
        if total_failed > 0:
            print(f"\nFailed articles saved to checkpoint file: {self.checkpoint_file}")

def main():
    """Main function to run the batch processor."""
    
    # File paths
    input_file = "icemap/data/mediacloud_articles.csv"
    output_file = "icemap/data/articles.csv"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found.")
        return
    
    # Check if API key is set
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("Error: DEEPSEEK_API_KEY environment variable is not set.")
        print("Please set it with: export DEEPSEEK_API_KEY='your-api-key-here'")
        return
    
    # Create batch processor
    processor = BatchProcessor(input_file, output_file)
    
    print("Starting batch article categorization...")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Checkpoint file: {processor.checkpoint_file}")
    print(f"Categories: {', '.join(CATEGORIES)}")
    print()
    
    try:
        # Process articles in batches of 10
        processor.process_articles_batch(batch_size=10)
        print("\nBatch categorization completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user. Progress saved to checkpoint.")
        processor.save_checkpoint()
        
    except Exception as e:
        print(f"\nError during processing: {e}")
        processor.save_checkpoint()

if __name__ == "__main__":
    main() 