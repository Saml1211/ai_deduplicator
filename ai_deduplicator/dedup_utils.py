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
from multiprocessing import Pool, cpu_count

# Rich library for progress bars
try:
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

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

# File Discovery
def get_files_recursively(root_dir: str) -> List[str]:
    """
    Recursively get all files in a directory, skipping common patterns.
    Returns a list of file paths.
    """
    skip_patterns = {'.DS_Store', '.git', '__pycache__', 'node_modules', 'venv', '.idea', '.vscode'}
    skip_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe'}

    files = []
    for root, dirs, filenames in os.walk(root_dir):
        # Skip directories that match skip patterns
        dirs[:] = [d for d in dirs if d not in skip_patterns and not d.startswith('.')]

        for filename in filenames:
            # Skip hidden files and common skip patterns/extensions
            if filename.startswith('.') or any(pattern in filename for pattern in skip_patterns):
                continue
            if os.path.splitext(filename)[1].lower() in skip_extensions:
                continue

            filepath = os.path.join(root, filename)
            if os.path.isfile(filepath):
                files.append(filepath)

    return files

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

def _hash_file_worker(filepath: str) -> Tuple[str, Optional[str]]:
    """
    Worker function for parallel hashing.
    Returns tuple of (filepath, file_hash).
    """
    file_hash = calculate_file_hash(filepath)
    return (filepath, file_hash)

def parallel_hash_files(files: List[str], workers: Optional[int] = None) -> Dict[str, Optional[str]]:
    """
    Hash multiple files in parallel using multiprocessing.
    Returns a dictionary mapping filepath to hash.
    """
    if workers is None:
        workers = min(cpu_count(), 8)  # Cap at 8 to avoid too many processes

    result_dict = {}

    # Use multiprocessing for parallel hashing
    with Pool(processes=workers) as pool:
        results = pool.map(_hash_file_worker, files)

    for filepath, file_hash in results:
        result_dict[filepath] = file_hash

    return result_dict

# Directory Scanning with progress bars and parallel hashing
def scan_directory(root_dir: str, analyze_content: bool = False, parallel: bool = True, workers: Optional[int] = None) -> Tuple[Dict[str, List[str]], List[Dict[str, Any]]]:
    """
    Scan the directory to find duplicates and optionally analyze content.
    Returns a tuple of:
    1. Dictionary mapping file hash to list of file paths (duplicates)
    2. List of file analysis results (if analyze_content is True)

    Args:
        root_dir: Directory to scan
        analyze_content: Whether to analyze file content (slower)
        parallel: Use parallel hashing for better performance (default: True)
        workers: Number of worker processes for parallel hashing (default: auto)
    """
    file_hashes = defaultdict(list)
    duplicate_files = defaultdict(list)
    file_analyses = []

    logging.info(f"Discovering files in {os.path.abspath(root_dir)}...")

    # Get all files first
    files = get_files_recursively(root_dir)
    total_files = len(files)

    if total_files == 0:
        logging.warning("No files found to process.")
        return duplicate_files, file_analyses

    logging.info(f"Found {total_files} files to process...")

    # Hash files (parallel or sequential)
    if parallel and total_files > 10:  # Only use parallel for 10+ files
        logging.info(f"Using parallel hashing with {workers or min(cpu_count(), 8)} workers...")

        # Use parallel hashing with progress tracking
        hash_results = {}

        if RICH_AVAILABLE:
            # We can't easily track progress with multiprocessing.Pool.map,
            # so we'll show an indeterminate progress spinner
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
            ) as progress:
                task = progress.add_task("[cyan]Hashing files in parallel...", total=None)
                hash_results = parallel_hash_files(files, workers=workers)
                progress.update(task, completed=True)
        else:
            logging.info("Hashing files in parallel...")
            hash_results = parallel_hash_files(files, workers=workers)

        # Group by hash
        for filepath, file_hash in hash_results.items():
            if file_hash:
                file_hashes[file_hash].append(filepath)

        logging.info(f"Parallel hashing complete for {total_files} files.")

    else:
        # Sequential hashing with detailed progress
        logging.info("Using sequential hashing...")

        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
            ) as progress:
                task = progress.add_task("[cyan]Hashing files...", total=total_files)

                for filepath in files:
                    file_hash = calculate_file_hash(filepath)
                    if file_hash:
                        file_hashes[file_hash].append(filepath)
                    progress.update(task, advance=1)
        else:
            for i, filepath in enumerate(files, 1):
                file_hash = calculate_file_hash(filepath)
                if file_hash:
                    file_hashes[file_hash].append(filepath)

                if i % 100 == 0 or i == total_files:
                    percentage = (i / total_files * 100)
                    logging.info(f"Processed {i}/{total_files} files ({percentage:.1f}%)")

    # Analyze file content if requested (sequential only)
    if analyze_content:
        logging.info("Analyzing file content...")

        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                task = progress.add_task("[magenta]Analyzing content...", total=total_files)

                for filepath in files:
                    try:
                        analysis = {
                            'path': filepath,
                            'size': os.path.getsize(filepath),
                            'extension': os.path.splitext(filepath)[1].lower(),
                            'last_modified': datetime.fromtimestamp(os.path.getmtime(filepath)),
                        }
                        file_analyses.append(analysis)
                    except Exception as e:
                        logging.warning(f"Could not analyze {filepath}: {e}")
                    progress.update(task, advance=1)
        else:
            for filepath in files:
                try:
                    analysis = {
                        'path': filepath,
                        'size': os.path.getsize(filepath),
                        'extension': os.path.splitext(filepath)[1].lower(),
                        'last_modified': datetime.fromtimestamp(os.path.getmtime(filepath)),
                    }
                    file_analyses.append(analysis)
                except Exception as e:
                    logging.warning(f"Could not analyze {filepath}: {e}")

    # Identify duplicates (files with the same hash)
    for file_hash, filepaths in file_hashes.items():
        if len(filepaths) > 1:
            duplicate_files[file_hash] = filepaths

    logging.info(f"Scan complete. Found {len(duplicate_files)} unique files with duplicates.")
    return duplicate_files, file_analyses

# File Operations with progress bars
def execute_operations(operations: List[Dict[str, Any]], dry_run: bool = True, create_log: bool = True, log_file: str = '.dedup_transaction.json') -> Dict[str, int]:
    """
    Execute the move/remove operations in the plan with progress tracking.

    Args:
        operations: List of operations to execute
        dry_run: If True, only simulate operations
        create_log: If True, create transaction log for rollback (default: True)
        log_file: Path to transaction log file

    Returns:
        Dictionary with execution statistics
    """
    stats = {'moved': 0, 'removed': 0, 'errors': 0}

    if not operations:
        logging.info("No operations to execute.")
        return stats

    total_ops = len(operations)
    logging.info(f"Executing {total_ops} operations... ({'DRY RUN' if dry_run else 'LIVE'})")

    # Create transaction log before executing (only for non-dry-run)
    if not dry_run and create_log:
        if not create_transaction_log(operations, log_file):
            logging.warning("Failed to create transaction log. Continuing without rollback capability.")
            create_log = False

    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task(
                f"[yellow]{'[DRY RUN] ' if dry_run else ''}Executing operations...",
                total=total_ops
            )

            for op in operations:
                try:
                    if op['action'] == 'move':
                        source = op['file']
                        dest = op['destination']

                        if not dry_run:
                            if not os.path.exists(source):
                                logging.warning(f"Source file not found, skipping move: {source}")
                                stats['errors'] += 1
                                progress.update(task, advance=1)
                                continue
                            # Create the target directory if it doesn't exist
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            shutil.move(source, dest)
                        stats['moved'] += 1

                    elif op['action'] == 'remove':
                        filepath = op['file']

                        if not dry_run:
                            if os.path.exists(filepath):
                                os.remove(filepath)
                            else:
                                logging.warning(f"File not found, skipping removal: {filepath}")
                                stats['errors'] += 1
                                progress.update(task, advance=1)
                                continue
                        stats['removed'] += 1

                except (PermissionError, FileNotFoundError, OSError, Exception) as e:
                    logging.error(f"Error processing operation {op}: {e}")
                    stats['errors'] += 1

                progress.update(task, advance=1)
    else:
        # Fallback without progress bar
        for i, op in enumerate(operations, 1):
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
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        shutil.move(source, dest)
                    stats['moved'] += 1

                elif op['action'] == 'remove':
                    filepath = op['file']
                    reason = op.get('reason', 'duplicate')
                    logging.info(f"{'[DRY RUN] ' if dry_run else ''}Removing {filepath} ({reason})")

                    if not dry_run:
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        else:
                            logging.warning(f"File not found, skipping removal: {filepath}")
                            stats['errors'] += 1
                    stats['removed'] += 1

            except (PermissionError, FileNotFoundError, OSError, Exception) as e:
                logging.error(f"Error processing operation {op}: {e}")
                stats['errors'] += 1

            if i % 10 == 0 or i == total_ops:
                percentage = (i / total_ops * 100)
                logging.info(f"Progress: {i}/{total_ops} operations ({percentage:.1f}%)")

    logging.info(f"Operation execution finished. Moved: {stats['moved']}, Removed: {stats['removed']}, Errors: {stats['errors']}")

    # Mark transaction as complete
    if not dry_run and create_log:
        mark_transaction_complete(log_file)
        logging.info(f"Transaction log updated. Use '--undo' to rollback changes if needed.")

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

# Transaction Log and Rollback System
def create_transaction_log(operations: List[Dict[str, Any]], log_file: str = '.dedup_transaction.json') -> bool:
    """
    Create a transaction log before executing operations.
    This allows for rollback/undo functionality.

    Args:
        operations: List of operations to log
        log_file: Path to transaction log file

    Returns:
        True if log created successfully, False otherwise
    """
    try:
        transaction = {
            'timestamp': datetime.now().isoformat(),
            'operations': operations,
            'completed': False
        }

        with open(log_file, 'w') as f:
            json.dump(transaction, f, indent=2)

        logging.info(f"Transaction log created: {log_file}")
        return True
    except Exception as e:
        logging.error(f"Failed to create transaction log: {e}")
        return False

def mark_transaction_complete(log_file: str = '.dedup_transaction.json') -> bool:
    """Mark a transaction as completed in the log file."""
    try:
        with open(log_file, 'r') as f:
            transaction = json.load(f)

        transaction['completed'] = True
        transaction['completed_at'] = datetime.now().isoformat()

        with open(log_file, 'w') as f:
            json.dump(transaction, f, indent=2)

        return True
    except Exception as e:
        logging.error(f"Failed to mark transaction complete: {e}")
        return False

def read_transaction_log(log_file: str = '.dedup_transaction.json') -> Optional[Dict[str, Any]]:
    """Read transaction log file."""
    try:
        if not os.path.exists(log_file):
            logging.error(f"Transaction log not found: {log_file}")
            return None

        with open(log_file, 'r') as f:
            transaction = json.load(f)

        return transaction
    except Exception as e:
        logging.error(f"Failed to read transaction log: {e}")
        return None

def rollback_operations(log_file: str = '.dedup_transaction.json', dry_run: bool = True) -> Dict[str, int]:
    """
    Rollback operations from a transaction log.
    Reverses move and remove operations.

    Args:
        log_file: Path to transaction log file
        dry_run: If True, only simulate rollback

    Returns:
        Dictionary with rollback statistics
    """
    stats = {'restored': 0, 'unmoved': 0, 'errors': 0, 'skipped': 0}

    transaction = read_transaction_log(log_file)
    if not transaction:
        logging.error("No valid transaction log found. Cannot rollback.")
        return stats

    if not transaction.get('completed', False):
        logging.warning("Transaction was not marked as completed. Rollback may be incomplete.")

    operations = transaction.get('operations', [])
    if not operations:
        logging.info("No operations to rollback.")
        return stats

    logging.info(f"Rolling back {len(operations)} operations... ({'DRY RUN' if dry_run else 'LIVE'})")

    # Reverse the operations list to undo in reverse order
    reversed_ops = list(reversed(operations))

    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task(
                f"[red]{'[DRY RUN] ' if dry_run else ''}Rolling back operations...",
                total=len(reversed_ops)
            )

            for op in reversed_ops:
                try:
                    if op['action'] == 'move':
                        # Reverse: move destination back to source
                        source = op['file']  # Original location
                        dest = op['destination']  # Where it was moved to

                        if not dry_run:
                            if os.path.exists(dest):
                                # Move it back
                                os.makedirs(os.path.dirname(source), exist_ok=True)
                                shutil.move(dest, source)
                                stats['unmoved'] += 1
                            else:
                                logging.warning(f"Destination file not found, skipping: {dest}")
                                stats['skipped'] += 1
                        else:
                            stats['unmoved'] += 1

                    elif op['action'] == 'remove':
                        # Cannot restore deleted files
                        logging.warning(f"Cannot restore deleted file: {op['file']}")
                        stats['skipped'] += 1

                except Exception as e:
                    logging.error(f"Error during rollback of operation {op}: {e}")
                    stats['errors'] += 1

                progress.update(task, advance=1)
    else:
        # Fallback without progress bar
        for i, op in enumerate(reversed_ops, 1):
            try:
                if op['action'] == 'move':
                    source = op['file']
                    dest = op['destination']

                    if not dry_run:
                        if os.path.exists(dest):
                            os.makedirs(os.path.dirname(source), exist_ok=True)
                            shutil.move(dest, source)
                            stats['unmoved'] += 1
                        else:
                            logging.warning(f"Destination file not found, skipping: {dest}")
                            stats['skipped'] += 1
                    else:
                        stats['unmoved'] += 1

                elif op['action'] == 'remove':
                    logging.warning(f"Cannot restore deleted file: {op['file']}")
                    stats['skipped'] += 1

            except Exception as e:
                logging.error(f"Error during rollback of operation {op}: {e}")
                stats['errors'] += 1

            if i % 10 == 0 or i == len(reversed_ops):
                logging.info(f"Rollback progress: {i}/{len(reversed_ops)}")

    logging.info(f"Rollback complete. Unmoved: {stats['unmoved']}, Skipped: {stats['skipped']}, Errors: {stats['errors']}")

    # Archive the transaction log
    if not dry_run:
        archive_name = f"{log_file}.rolled_back_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            shutil.copy(log_file, archive_name)
            os.remove(log_file)
            logging.info(f"Transaction log archived to: {archive_name}")
        except Exception as e:
            logging.warning(f"Failed to archive transaction log: {e}")

    return stats 