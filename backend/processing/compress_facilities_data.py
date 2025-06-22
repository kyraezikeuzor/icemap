#!/usr/bin/env python3
"""
Script to create a gzip compression of the facilities data JSONL file.
"""

import gzip
import os
import sys
from pathlib import Path

def compress_jsonl_file(input_path, output_path=None):
    """
    Compress a JSONL file using gzip compression.
    
    Args:
        input_path (str): Path to the input JSONL file
        output_path (str, optional): Path for the output gzip file. 
                                   If None, will use input_path + '.gz'
    """
    input_file = Path(input_path)
    
    # Check if input file exists
    if not input_file.exists():
        print(f"Error: Input file '{input_path}' does not exist.")
        return False
    
    # Set output path if not provided
    if output_path is None:
        output_path = str(input_file) + '.gz'
    
    output_file = Path(output_path)
    
    try:
        # Get original file size
        original_size = input_file.stat().st_size
        
        print(f"Compressing {input_path}...")
        print(f"Original file size: {original_size:,} bytes ({original_size / 1024 / 1024:.2f} MB)")
        
        # Compress the file
        with open(input_file, 'rb') as f_in:
            with gzip.open(output_file, 'wb', compresslevel=9) as f_out:
                f_out.writelines(f_in)
        
        # Get compressed file size
        compressed_size = output_file.stat().st_size
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        print(f"Compression complete!")
        print(f"Compressed file: {output_path}")
        print(f"Compressed size: {compressed_size:,} bytes ({compressed_size / 1024 / 1024:.2f} MB)")
        print(f"Compression ratio: {compression_ratio:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"Error during compression: {e}")
        return False

def main():
    """Main function to run the compression."""
    # Target file path
    input_file = "data/distilled_data/facilities_with_coordinates_results.jsonl"
    
    print("=== JSONL File Compression Script ===")
    print(f"Input file: {input_file}")
    print()
    
    # Perform compression
    success = compress_jsonl_file(input_file)
    
    if success:
        print("\n✅ Compression completed successfully!")
    else:
        print("\n❌ Compression failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 