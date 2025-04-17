import os
import sys
import hashlib
import shutil
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import json
from typing import Dict, List, Tuple, Any, Optional

# Configure logging
def setup_logging(log_file: str, verbose: bool):
    """Set up logging to both console and file."""
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger()
    
    # Clear existing handlers if any (to avoid duplicate logs)
    if logger.hasHandlers():
        logger.handlers.clear()
        
    log_level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(log_level)
    
    # File handler
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)
    
    return logger

# File Hashing
def calculate_file_hash(filepath: str) -> Optional[str]:
    """Calculate SHA-256 hash of a file."""
    try:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            # Read the file in chunks to handle large files efficiently
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except (PermissionError, FileNotFoundError, OSError) as e:
        logging.warning(f"Could not hash file {filepath}: {e}")
        return None

# Directory Scanning (using the more comprehensive version from AI script)
def scan_directory(root_dir: str, analyze_content: bool = False) -> Tuple[Dict[str, List[str]], List[Dict[str, Any]]]:
    """
    Scan the directory to find duplicates and optionally analyze content.
    Returns a tuple of:
    1. Dictionary mapping file hash to list of file paths (duplicates)
    2. List of file analysis results (if analyze_content is True)
    """
    file_hashes = defaultdict(list)
    duplicate_files = defaultdict(list)
    file_analyses = []
    
    # Skip these files/directories
    # Consider making these configurable later
    skip_patterns = {'.DS_Store', '.git', '__pycache__', 'node_modules', 'venv', '.idea', '.vscode'}
    skip_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe'}
    
    total_files = 0
    processed_files = 0
    
    logging.info(f"Counting files in {os.path.abspath(root_dir)}...")
    # First, get a count of total files for progress reporting
    for root, dirs, files in os.walk(root_dir):
        # Skip directories that match skip patterns
        dirs[:] = [d for d in dirs if d not in skip_patterns and not d.startswith('.')]
        
        for filename in files:
            # Skip hidden files and common skip patterns/extensions
            if filename.startswith('.') or any(pattern in filename for pattern in skip_patterns):
                continue
            if os.path.splitext(filename)[1].lower() in skip_extensions:
                continue
                
            filepath = os.path.join(root, filename)
            if os.path.isfile(filepath): # Ensure it's a file
                total_files += 1
    
    logging.info(f"Scanning and processing {total_files} files...")
    
    # Now process each file
    for root, dirs, files in os.walk(root_dir):
        # Skip directories that match skip patterns
        dirs[:] = [d for d in dirs if d not in skip_patterns and not d.startswith('.')]
        
        for filename in files:
             # Skip hidden files and common skip patterns/extensions
            if filename.startswith('.') or any(pattern in filename for pattern in skip_patterns):
                continue
            if os.path.splitext(filename)[1].lower() in skip_extensions:
                continue

            filepath = os.path.join(root, filename)
            if not os.path.isfile(filepath):
                continue # Skip directories or other non-files

            # Calculate file hash
            file_hash = calculate_file_hash(filepath)
            if file_hash:
                file_hashes[file_hash].append(filepath)
            
            # Analyze file content if requested (only needed for AI script currently)
            if analyze_content:
                try:
                    # Basic analysis here, can be expanded
                    analysis = {
                        'path': filepath,
                        'size': os.path.getsize(filepath),
                        'extension': os.path.splitext(filepath)[1].lower(),
                        'last_modified': datetime.fromtimestamp(os.path.getmtime(filepath)),
                    }
                    file_analyses.append(analysis)
                except Exception as e:
                    logging.warning(f"Could not analyze {filepath}: {e}")
            
            processed_files += 1
            if processed_files % 100 == 0 or processed_files == total_files:
                # Avoid division by zero if total_files is 0
                percentage = (processed_files / total_files * 100) if total_files > 0 else 100
                logging.info(f"Processed {processed_files}/{total_files} files ({percentage:.1f}%)")
    
    # Identify duplicates (files with the same hash)
    for file_hash, filepaths in file_hashes.items():
        if len(filepaths) > 1:
            duplicate_files[file_hash] = filepaths
    
    logging.info(f"Scan complete. Found {len(duplicate_files)} unique files with duplicates.")
    return duplicate_files, file_analyses

# File Operations
def execute_operations(operations: List[Dict[str, Any]], dry_run: bool = True) -> Dict[str, int]:
    """Execute the move/remove operations in the plan."""
    stats = {'moved': 0, 'removed': 0, 'errors': 0}
    
    if not operations:
        logging.info("No operations to execute.")
        return stats

    logging.info(f"Executing {len(operations)} operations... ({'DRY RUN' if dry_run else 'LIVE'})" )

    for op in operations:
        try:
            if op['action'] == 'move':
                source = op['file']
                dest = op['destination']
                logging.info(f"{'[DRY RUN] ' if dry_run else ''}Moving {source} -> {dest}")
                
                if not dry_run:
                    if not os.path.exists(source):
                         logging.warning(f"Source file not found, skipping move: {source}")
                         stats['errors'] += 1
                         continue
                    # Create the target directory if it doesn't exist
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.move(source, dest)
                stats['moved'] += 1
                
            elif op['action'] == 'remove':
                filepath = op['file']
                reason = op.get('reason', 'duplicate') # Default reason
                logging.info(f"{'[DRY RUN] ' if dry_run else ''}Removing {filepath} ({reason})")
                
                if not dry_run:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    else:
                        logging.warning(f"File not found, skipping removal: {filepath}")
                        stats['errors'] += 1 # Count as error if file meant to be removed is gone
                stats['removed'] += 1
                
        except (PermissionError, FileNotFoundError, OSError, Exception) as e:
            logging.error(f"Error processing operation {op}: {e}")
            stats['errors'] += 1
    
    logging.info(f"Operation execution finished. Moved: {stats['moved']}, Removed: {stats['removed']}, Errors: {stats['errors']}")
    return stats

# Reporting
def generate_report(duplicates: Dict[str, List[str]], operations: List[Dict[str, Any]], stats: Dict[str, int], strategy: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Generate a detailed report of duplicates and operations."""
    total_duplicates = sum(len(files) for files in duplicates.values()) - len(duplicates)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'statistics': {
            'total_unique_files_with_duplicates': len(duplicates),
            'total_duplicate_instances_found': total_duplicates,
            'operations_planned': len(operations),
            'operations_executed': stats
        },
        'duplicates_found': {},
        'operations_executed_details': operations # Include the planned/executed ops
    }

    if strategy is not None:
        report['organization_strategy'] = strategy
    
    # Format duplicates for the report
    for file_hash, filepaths in duplicates.items():
        report['duplicates_found'][file_hash] = [str(path) for path in filepaths]
    
    return report

def save_report(report: Dict[str, Any], filename: str) -> None:
    """Save the deduplication report to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        logging.info(f"Report saved to {filename}")
    except IOError as e:
        logging.error(f"Failed to save report to {filename}: {e}") 