#!/usr/bin/env python3
"""
File Deduplication Script for Financials Directory

This script identifies duplicate files based on content (SHA-256 hash)
and consolidates them according to a preferred directory structure.

Features:
- Identifies duplicate files with identical content
- Provides detailed reporting of duplicates
- Supports dry-run mode for safe testing
- Maintains a preferred directory structure
- Logs all operations to a file
- Handles edge cases (permissions, etc.)

Usage:
    python deduplicate_files.py [--dry-run] [--verbose]
"""

import os
import sys
import hashlib
import shutil
import argparse
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import re
import json

# Import common utilities
import dedup_utils

# Configure logging - Handled by dedup_utils.setup_logging
# def setup_logging(log_file='deduplication.log'):
#     """Set up logging to both console and file."""
#     log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
#     logger = logging.getLogger()
#     logger.setLevel(logging.INFO)
#     
#     # File handler
#     file_handler = logging.FileHandler(log_file, mode='w')
#     file_handler.setFormatter(log_formatter)
#     logger.addHandler(file_handler)
#     
#     # Console handler
#     console_handler = logging.StreamHandler(sys.stdout)
#     console_handler.setFormatter(log_formatter)
#     logger.addHandler(console_handler)
#     
#     return logger

# Define preferred directory structure
# The key is a regex pattern to match file paths, the value is the preferred location
PREFERRED_STRUCTURE = {
    # Bank statements
    r'.*bank_statements.*\.pdf$': './income/history/bank_statements/',
    
    # Car documents
    r'.*car_documents.*\.pdf$': './insurance/car/documents/',
    r'.*car_documents.*\.jpg$': './insurance/car/documents/identification/',
    r'.*car_documents.*quotes.*\.pdf$': './insurance/car/documents/quotes/',
    r'.*car_documents.*salary_packaging.*': './insurance/car/documents/salary_packaging/',
    r'.*car_documents.*contracts.*': './insurance/car/documents/contracts/',
    
    # Spreadsheets
    r'.*spreadsheets.*\.numbers$': './expenses/analysis/spreadsheets/',
    r'.*spreadsheets.*\.csv$': './expenses/analysis/spreadsheets/',
    
    # ADHD tools and budget files
    r'.*adhd_friendly_budget\.md$': './budget/current/',
    r'.*adhd_friendly_tools\.md$': './tools/adhd/',
    r'.*adhd_friendly_payment_tracker\.md$': './expenses/fixed/',
    
    # Assistance programs
    r'.*qld_assistance_programs\.md$': './recovery/assistance/',
    
    # Income ideas
    r'.*income_boost_ideas\.md$': './income/opportunities/',
    
    # Financial summaries
    r'.*financial_summary\.md$': './income/summaries/',
    r'.*key_financial_insights\.md$': './income/summaries/',
    
    # Sell categories
    r'.*quick_sell_guide\.md$': './assets/sell/',
    r'.*sellable_items\.csv$': './assets/sell/',
    
    # Default pattern (keep in financial_recovery if no match)
    r'.*': './financial_recovery/'
}

# File extensions to skip (binary files, temp files, etc.)
SKIP_EXTENSIONS = {'.DS_Store', '.git', '.gitignore', '.gitattributes'}

def calculate_file_hash(filepath):
    """Calculate SHA-256 hash of a file."""
    # Use the utility function, which includes error handling and logging
    return dedup_utils.calculate_file_hash(filepath)

def get_preferred_location(filepath):
    """Determine the preferred location for a file based on its path."""
    for pattern, location in PREFERRED_STRUCTURE.items():
        if re.match(pattern, str(filepath)):
            return location
    return PREFERRED_STRUCTURE[r'.*']  # Default location

# Find duplicates - Handled by dedup_utils.scan_directory
# def find_duplicates(root_dir):
#     """
#     Scan the directory tree and find duplicate files.
#     Returns a dictionary mapping file hash to a list of file paths.
#     """
#     file_hashes = defaultdict(list)
#     duplicate_files = defaultdict(list)
#     total_files = 0
#     processed_files = 0
#     
#     # First, get a count of total files for progress reporting
#     for root, _, files in os.walk(root_dir):
#         for filename in files:
#             filepath = os.path.join(root, filename)
#             if os.path.isfile(filepath) and not any(ext in filepath for ext in SKIP_EXTENSIONS):
#                 total_files += 1
#     
#     logging.info(f"Scanning {total_files} files for duplicates...")
#     
#     # Now process each file
#     for root, _, files in os.walk(root_dir):
#         for filename in files:
#             filepath = os.path.join(root, filename)
#             if os.path.isfile(filepath) and not any(ext in filepath for ext in SKIP_EXTENSIONS):
#                 file_hash = calculate_file_hash(filepath)
#                 if file_hash:
#                     file_hashes[file_hash].append(filepath)
#                 
#                 processed_files += 1
#                 if processed_files % 100 == 0 or processed_files == total_files:
#                     logging.info(f"Processed {processed_files}/{total_files} files ({processed_files/total_files*100:.1f}%)")
#     
#     # Identify duplicates (files with the same hash)
#     for file_hash, filepaths in file_hashes.items():
#         if len(filepaths) > 1:
#             duplicate_files[file_hash] = filepaths
#     
#     return duplicate_files

def generate_deduplication_plan(duplicates):
    """
    Generate a plan for handling duplicates.
    Returns a list of operations to perform.
    """
    operations = []
    
    for file_hash, filepaths in duplicates.items():
        # Group files by their preferred location
        location_groups = defaultdict(list)
        for filepath in filepaths:
            preferred_location = get_preferred_location(filepath)
            location_groups[preferred_location].append(filepath)
        
        # For each preferred location, keep one file and mark others for removal
        for preferred_location, files in location_groups.items():
            if not files:
                continue
                
            # Choose the file to keep (the one already in the preferred location, or the first one)
            files_in_preferred_location = [f for f in files if preferred_location in f]
            if files_in_preferred_location:
                # Keep the file that's already in the preferred location
                keep_file = files_in_preferred_location[0]
                # If multiple files in preferred location, mark extras for removal
                for extra in files_in_preferred_location[1:]:
                    operations.append({
                        'action': 'remove',
                        'file': extra,
                        'reason': 'duplicate in preferred location'
                    })
            else:
                # No file in preferred location, move one there
                keep_file = files[0]
                filename = os.path.basename(keep_file)
                target_path = os.path.join(preferred_location, filename)
                
                # Check if target path already exists (with a different hash)
                # Use the utility function for hashing
                target_hash = dedup_utils.calculate_file_hash(target_path) if os.path.exists(target_path) else None
                if target_hash and target_hash != file_hash:
                    # Generate a unique name by adding a timestamp
                    name, ext = os.path.splitext(filename)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_filename = f"{name}_{timestamp}{ext}"
                    target_path = os.path.join(preferred_location, new_filename)
                
                operations.append({
                    'action': 'move',
                    'file': keep_file,
                    'destination': target_path,
                    'reason': 'moving to preferred location'
                })
            
            # Mark remaining duplicates for removal
            for duplicate in files:
                if duplicate != keep_file:
                    operations.append({
                        'action': 'remove',
                        'file': duplicate,
                        'reason': 'duplicate of ' + keep_file
                    })
    
    return operations

# Execute operations - Handled by dedup_utils.execute_operations
# def execute_operations(operations, dry_run=True):
#     """Execute the operations in the deduplication plan."""
#     stats = {'moved': 0, 'removed': 0, 'errors': 0}
#     
#     for op in operations:
#         try:
#             if op['action'] == 'move':
#                 source = op['file']
#                 dest = op['destination']
#                 logging.info(f"{'[DRY RUN] ' if dry_run else ''}Moving {source} -> {dest}")
#                 
#                 if not dry_run:
#                     # Create the target directory if it doesn't exist
#                     os.makedirs(os.path.dirname(dest), exist_ok=True)
#                     shutil.move(source, dest)
#                 stats['moved'] += 1
#                 
#             elif op['action'] == 'remove':
#                 filepath = op['file']
#                 logging.info(f"{'[DRY RUN] ' if dry_run else ''}Removing {filepath} ({op['reason']})")
#                 
#                 if not dry_run:
#                     os.remove(filepath)
#                 stats['removed'] += 1
#                 
#         except (PermissionError, FileNotFoundError, OSError) as e:
#             logging.error(f"Error processing {op['file']}: {e}")
#             stats['errors'] += 1
#     
#     return stats

# Generate report - Handled by dedup_utils.generate_report
# def generate_report(duplicates, operations, stats):
#     """Generate a detailed report of duplicates and operations."""
#     report = {
#         'timestamp': datetime.now().isoformat(),
#         'statistics': {
#             'total_unique_files': len(duplicates),
#             'total_duplicate_files': sum(len(files) for files in duplicates.values()) - len(duplicates),
#             'operations': stats
#         },
#         'duplicates': {},
#         'operations': operations
#     }
#     
#     # Format duplicates for the report
#     for file_hash, filepaths in duplicates.items():
#         report['duplicates'][file_hash] = [str(path) for path in filepaths]
#     
#     return report

# Save report - Handled by dedup_utils.save_report
# def save_report(report, filename='deduplication_report.json'):
#     """Save the deduplication report to a file."""
#     with open(filename, 'w') as f:
#         json.dump(report, f, indent=2)
#     logging.info(f"Report saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Deduplicate files based on content and preferred structure.') # Updated description
    parser.add_argument('--dry-run', action='store_true', help='Simulate operations without making changes')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--directory', '-d', default='.', help='Directory to analyze (default: current directory)') # Added directory arg consistency
    args = parser.parse_args()
    
    # Set up logging using the utility function
    logger = dedup_utils.setup_logging('deduplication.log', args.verbose)
    # logger.setLevel(log_level) # Level is set within setup_logging now
    
    # Start the deduplication process
    logging.info("Starting rule-based file deduplication process...") # Updated message
    logging.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logging.info(f"Target directory: {os.path.abspath(args.directory)}")
    
    # Find duplicates using the utility function
    # analyze_content=False as this script doesn't use detailed analysis
    duplicates, _ = dedup_utils.scan_directory(args.directory, analyze_content=False)
    # Logging info about findings is now inside scan_directory
    # logging.info(f"Found {len(duplicates)} unique files with duplicates")
    
    # Generate a plan for handling duplicates based on PREFERRED_STRUCTURE
    operations = generate_deduplication_plan(duplicates)
    logging.info(f"Generated plan with {len(operations)} operations based on preferred structure rules.")
    
    # Execute the operations using the utility function
    stats = dedup_utils.execute_operations(operations, dry_run=args.dry_run)
    
    # Generate and save the report using utility functions
    # Pass strategy=None as this script uses hardcoded rules
    report = dedup_utils.generate_report(duplicates, operations, stats, strategy=None)
    dedup_utils.save_report(report, filename='deduplication_report.json')
    
    # Print summary
    logging.info("Rule-based deduplication process complete!") # Updated message
    # Stats logging is now inside execute_operations
    # logging.info(f"Files moved: {stats['moved']}")
    # logging.info(f"Files removed: {stats['removed']}")
    # logging.info(f"Errors: {stats['errors']}")
    logging.info(f"{'No changes were made (dry run)' if args.dry_run else 'Changes have been applied based on the plan.'}")
    logging.info("See deduplication_report.json for details")

if __name__ == "__main__":
    main()