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


# Custom Exceptions
class TransactionLogError(Exception):
    """Raised when transaction log creation fails."""
    pass


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
def get_files_recursively(root_dir: str, skip_patterns: Optional[set] = None, skip_extensions: Optional[set] = None, use_defaults: bool = True) -> List[str]:
    """
    Recursively get all files in a directory, skipping specified patterns.

    Args:
        root_dir: Root directory to scan
        skip_patterns: Set of directory/file patterns to skip (e.g., {'.git', 'node_modules'})
        skip_extensions: Set of file extensions to skip (e.g., {'.pyc', '.pyo'})
        use_defaults: If True, merge custom patterns with defaults. If False, use only custom patterns.

    Returns:
        List of file paths

    Examples:
        # Use defaults only (default behavior)
        files = get_files_recursively('/path/to/dir')

        # Add custom patterns to defaults
        custom_skip = {'.custom_dir', 'temp_files'}
        files = get_files_recursively('/path/to/dir', skip_patterns=custom_skip)

        # Replace defaults entirely
        custom_skip = {'.DS_Store'}
        files = get_files_recursively('/path/to/dir', skip_patterns=custom_skip, use_defaults=False)
    """
    # Default skip patterns
    default_skip_patterns = {'.DS_Store', '.git', '__pycache__', 'node_modules', 'venv', '.idea', '.vscode'}
    default_skip_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe'}

    # Merge or replace defaults
    if skip_patterns is None:
        final_skip_patterns = default_skip_patterns
    elif use_defaults:
        final_skip_patterns = default_skip_patterns | skip_patterns
    else:
        final_skip_patterns = skip_patterns

    if skip_extensions is None:
        final_skip_extensions = default_skip_extensions
    elif use_defaults:
        final_skip_extensions = default_skip_extensions | skip_extensions
    else:
        final_skip_extensions = skip_extensions

    files = []
    for root, dirs, filenames in os.walk(root_dir):
        # Skip directories that match skip patterns
        dirs[:] = [d for d in dirs if d not in final_skip_patterns and not d.startswith('.')]

        for filename in filenames:
            # Skip hidden files and common skip patterns/extensions
            if filename.startswith('.') or any(pattern in filename for pattern in final_skip_patterns):
                continue
            if os.path.splitext(filename)[1].lower() in final_skip_extensions:
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
def scan_directory(root_dir: str, analyze_content: bool = False, parallel: bool = True, workers: Optional[int] = None, skip_patterns: Optional[set] = None, skip_extensions: Optional[set] = None, use_default_skips: bool = True) -> Tuple[Dict[str, List[str]], List[Dict[str, Any]]]:
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
        skip_patterns: Custom directory/file patterns to skip
        skip_extensions: Custom file extensions to skip
        use_default_skips: If True, merge custom patterns with defaults. If False, use only custom patterns.
    """
    file_hashes = defaultdict(list)
    duplicate_files = defaultdict(list)
    file_analyses = []

    logging.info(f"Discovering files in {os.path.abspath(root_dir)}...")

    # Get all files first
    files = get_files_recursively(root_dir, skip_patterns=skip_patterns, skip_extensions=skip_extensions, use_defaults=use_default_skips)
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

# File Archiving Helpers
def _archive_file(filepath: str, archive_dir: str = '.dedup-deleted') -> Optional[str]:
    """
    Archive a file to the archive directory instead of permanently deleting it.
    Preserves original directory structure and adds timestamp to prevent collisions.

    SECURITY CONSIDERATIONS:
    - Archived files may contain sensitive data identical to original files
    - Archive directory should have restrictive permissions (700 - owner access only)
    - Consider the sensitivity of files being archived
    - Securely delete archive directory when recovery is no longer needed
    - Archive paths reveal file organization structure - protect access accordingly

    RECOMMENDED PRACTICES:
    - Regularly audit the archive directory: ls -la .dedup-deleted
    - Set permissions: chmod 700 .dedup-deleted
    - Delete archive after confirmed success: rm -rf .dedup-deleted
    - For sensitive data: use secure deletion for archive directory

    Args:
        filepath: Path to the file to archive
        archive_dir: Directory to archive files to (default: '.dedup-deleted')

    Returns:
        Archive path if successful, None otherwise
    """
    try:
        # Get the absolute path to work with
        abs_filepath = os.path.abspath(filepath)

        # Create archive directory if it doesn't exist
        os.makedirs(archive_dir, exist_ok=True)

        # SECURITY: Set restrictive permissions on archive directory
        # This prevents other users from accessing archived (deduplicated) files
        try:
            os.chmod(archive_dir, 0o700)  # rwx------ (owner access only)
        except OSError as perm_error:
            logging.warning(f"Could not set restrictive permissions on {archive_dir}: {perm_error}")
            logging.warning("Please manually run: chmod 700 " + archive_dir)

        # Preserve directory structure in archive
        # For /path/to/file.txt, create .dedup-deleted/path/to/file.txt
        if abs_filepath.startswith('/'):
            relative_path = abs_filepath.lstrip('/')
        else:
            relative_path = abs_filepath

        archive_path = os.path.join(archive_dir, relative_path)

        # Add timestamp to prevent collisions
        base, ext = os.path.splitext(archive_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
        archive_path_with_timestamp = f"{base}_{timestamp}{ext}"

        # Create the directory structure in archive
        archive_file_dir = os.path.dirname(archive_path_with_timestamp)
        os.makedirs(archive_file_dir, exist_ok=True)

        # Move the file to archive
        shutil.move(abs_filepath, archive_path_with_timestamp)

        return archive_path_with_timestamp
    except Exception as e:
        logging.error(f"Failed to archive file {filepath}: {e}")
        return None

def _restore_from_archive(original_filepath: str, archive_dir: str = '.dedup-deleted') -> bool:
    """
    Restore a file from the archive directory.
    Finds the most recent archived version and restores it to the original location.

    Args:
        original_filepath: Original path of the file to restore
        archive_dir: Directory containing archived files (default: '.dedup-deleted')

    Returns:
        True if restore successful, False otherwise
    """
    try:
        abs_original = os.path.abspath(original_filepath)

        # Construct the expected archive path (without timestamp)
        if abs_original.startswith('/'):
            relative_path = abs_original.lstrip('/')
        else:
            relative_path = abs_original

        archive_base = os.path.join(archive_dir, relative_path)
        base, ext = os.path.splitext(archive_base)

        # Find all archived versions of this file
        archive_dir_path = os.path.dirname(archive_base)
        if not os.path.exists(archive_dir_path):
            logging.warning(f"Archive directory not found: {archive_dir_path}")
            return False

        # List all files in the archive directory
        archived_files = []
        for filename in os.listdir(archive_dir_path):
            full_path = os.path.join(archive_dir_path, filename)
            # Check if this is an archived version of our file
            if filename.startswith(os.path.basename(base) + '_') and filename.endswith(ext):
                archived_files.append(full_path)

        if not archived_files:
            logging.warning(f"No archived versions found for: {original_filepath}")
            return False

        # Sort by modification time and get the most recent
        archived_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        most_recent = archived_files[0]

        # Restore the file to its original location
        os.makedirs(os.path.dirname(abs_original), exist_ok=True)
        shutil.move(most_recent, abs_original)

        # Clean up any other archived versions
        for other_archive in archived_files[1:]:
            try:
                os.remove(other_archive)
                logging.debug(f"Cleaned up old archive: {other_archive}")
            except Exception as e:
                logging.warning(f"Could not remove old archive {other_archive}: {e}")

        return True
    except Exception as e:
        logging.error(f"Failed to restore file from archive {original_filepath}: {e}")
        return False

# File Operations with progress bars
def execute_operations(operations: List[Dict[str, Any]], dry_run: bool = True, create_log: bool = True, log_file: str = '.dedup_transaction.json', archive_dir: str = '.dedup-deleted', force_continue: bool = False, skip_confirmation: bool = False, interactive: bool = False) -> Dict[str, int]:
    """
    Execute the move/remove operations in the plan with progress tracking.
    Files marked for removal are archived to '.dedup-deleted/' instead of being permanently deleted,
    making undo/rollback fully reversible.

    Args:
        operations: List of operations to execute
        dry_run: If True, only simulate operations
        create_log: If True, create transaction log for rollback (default: True)
        log_file: Path to transaction log file
        archive_dir: Directory to archive removed files (default: '.dedup-deleted')
        force_continue: If True, bypass transaction log safety checks (use with caution)
        skip_confirmation: If True, skip confirmation prompt (--yes flag)
        interactive: If True, force confirmation prompt even with skip_confirmation (--interactive flag)

    Returns:
        Dictionary with execution statistics
    """
    stats = {'moved': 0, 'archived': 0, 'errors': 0}

    if not operations:
        logging.info("No operations to execute.")
        return stats

    total_ops = len(operations)
    logging.info(f"Executing {total_ops} operations... ({'DRY RUN' if dry_run else 'LIVE'})")

    # Count operations by type
    move_ops = sum(1 for op in operations if op['action'] == 'move')
    archive_ops = sum(1 for op in operations if op['action'] == 'remove')

    # Show confirmation prompt before executing (but not in dry-run mode)
    if not dry_run and (interactive or not skip_confirmation):
        logging.info("\n" + "="*70)
        logging.info("OPERATION SUMMARY (LIVE MODE - CHANGES WILL BE PERMANENT)")
        logging.info("="*70)
        logging.info(f"Files to move:    {move_ops}")
        logging.info(f"Files to archive: {archive_ops}")
        logging.info(f"Total operations: {total_ops}")
        logging.info("="*70 + "\n")

        # Prompt for confirmation
        user_input = input("Continue with these operations? (yes/no): ").strip().lower()
        if user_input not in ('yes', 'y'):
            logging.info("Operation cancelled by user.")
            return stats

    # Warning if force_continue is used
    if force_continue and not dry_run:
        logging.warning("=" * 80)
        logging.warning("WARNING: --force-continue flag is set. Executing operations WITHOUT transaction log.")
        logging.warning("         This means rollback capability is DISABLED for this operation.")
        logging.warning("         If something goes wrong, you will NOT be able to undo these changes.")
        logging.warning("=" * 80)

    # Create transaction log before executing (only for non-dry-run and not force_continue)
    # SECURITY NOTE: Transaction log contains file paths and operational details.
    # The create_transaction_log function automatically sets restrictive permissions (600).
    # Ensure this log file is protected from unauthorized access, especially on multi-user systems.
    if not dry_run and create_log and not force_continue:
        if not create_transaction_log(operations, log_file):
            error_msg = (
                f"Failed to create transaction log at {log_file}. "
                "Cannot proceed with file operations without rollback capability. "
                "Please check file permissions and disk space, then retry. "
                "Use --force-continue to bypass this check (not recommended)."
            )
            logging.error(error_msg)
            raise TransactionLogError(error_msg)

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
                        reason = op.get('reason', 'duplicate')

                        if not dry_run:
                            if os.path.exists(filepath):
                                # Archive the file instead of permanently deleting it
                                archive_path = _archive_file(filepath, archive_dir)
                                if archive_path:
                                    logging.info(f"Archived {filepath} to {archive_path} ({reason})")
                                    stats['archived'] += 1
                                else:
                                    logging.error(f"Failed to archive file: {filepath}")
                                    stats['errors'] += 1
                            else:
                                logging.warning(f"File not found, skipping archive: {filepath}")
                                stats['errors'] += 1
                                progress.update(task, advance=1)
                                continue
                        else:
                            stats['archived'] += 1

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
                    logging.info(f"{'[DRY RUN] ' if dry_run else ''}Archiving {filepath} ({reason})")

                    if not dry_run:
                        if os.path.exists(filepath):
                            # Archive the file instead of permanently deleting it
                            archive_path = _archive_file(filepath, archive_dir)
                            if archive_path:
                                logging.info(f"Successfully archived to {archive_path}")
                                stats['archived'] += 1
                            else:
                                logging.error(f"Failed to archive file: {filepath}")
                                stats['errors'] += 1
                        else:
                            logging.warning(f"File not found, skipping archive: {filepath}")
                            stats['errors'] += 1
                    else:
                        stats['archived'] += 1

            except (PermissionError, FileNotFoundError, OSError, Exception) as e:
                logging.error(f"Error processing operation {op}: {e}")
                stats['errors'] += 1

            if i % 10 == 0 or i == total_ops:
                percentage = (i / total_ops * 100)
                logging.info(f"Progress: {i}/{total_ops} operations ({percentage:.1f}%)")

    logging.info(f"Operation execution finished. Moved: {stats['moved']}, Archived: {stats['archived']}, Errors: {stats['errors']}")

    # Mark transaction as complete
    if not dry_run and create_log:
        mark_transaction_complete(log_file)
        logging.info(f"Transaction log updated. Use '--undo' to rollback changes if needed.")

    return stats

# Reporting
def generate_report(duplicates: Dict[str, List[str]], operations: List[Dict[str, Any]], stats: Dict[str, int], strategy: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Generate a detailed report of duplicates and operations."""
    total_duplicates = sum(len(files) for files in duplicates.values()) - len(duplicates)

    def _size(path: str) -> int:
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    # Every copy beyond the first in each identical-content group is
    # recoverable space once the duplicates are consolidated.
    bytes_recoverable = sum(
        sum(sorted((_size(p) for p in paths), reverse=True)[1:])
        for paths in duplicates.values()
    )

    report = {
        'timestamp': datetime.now().isoformat(),
        'statistics': {
            'total_unique_files_with_duplicates': len(duplicates),
            'total_duplicate_instances_found': total_duplicates,
            'bytes_recoverable': bytes_recoverable,
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

    SECURITY CONSIDERATIONS:

    This function creates a JSON file containing full file paths from your system.
    The transaction log will include:
    - Source and destination paths for move operations
    - File paths marked for removal/archival
    - Directory structure information

    PROTECTION REQUIREMENTS:
    - The transaction log file should have restrictive permissions (600 - read/write for owner only)
    - Parent directories should have appropriate permissions (700 or 750)
    - Transaction logs should NOT be committed to version control (.gitignore)
    - Securely delete old transaction logs when operations are verified complete

    PATH DISCLOSURE RISKS:
    - Full paths reveal system structure, usernames, and project organization
    - Multi-user systems: other users could read paths if permissions are not set
    - Archive paths in logs show directory hierarchy used during deduplication

    RECOMMENDED POST-OPERATION ACTIONS:
    1. Review the transaction log to verify operations are correct
    2. Delete or securely archive the log after confirming success
    3. For sensitive data: use 'shred' or similar tools for secure deletion
    4. Verify permissions: ls -la .dedup_transaction.json should show 600

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

        # IMPORTANT: Set restrictive permissions on transaction log file
        # This prevents other users from reading sensitive path information
        try:
            os.chmod(log_file, 0o600)  # rw------- (read/write for owner only)
        except OSError as perm_error:
            logging.warning(f"Could not set restrictive permissions on {log_file}: {perm_error}")
            logging.warning("Please manually run: chmod 600 " + log_file)

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

def rollback_operations(log_file: str = '.dedup_transaction.json', dry_run: bool = True, archive_dir: str = '.dedup-deleted') -> Dict[str, int]:
    """
    Rollback operations from a transaction log.
    Reverses move and remove operations. Restores archived files from '.dedup-deleted/'.

    Args:
        log_file: Path to transaction log file
        dry_run: If True, only simulate rollback
        archive_dir: Directory containing archived files (default: '.dedup-deleted')

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
                        # Restore archived files
                        original_filepath = op['file']

                        if not dry_run:
                            # Find and restore the most recent archived version
                            restored = _restore_from_archive(original_filepath, archive_dir)
                            if restored:
                                logging.info(f"Restored {original_filepath} from archive")
                                stats['restored'] += 1
                            else:
                                logging.warning(f"Could not restore archived file: {original_filepath}")
                                stats['skipped'] += 1
                        else:
                            stats['restored'] += 1

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
                    # Restore archived files
                    original_filepath = op['file']

                    if not dry_run:
                        # Find and restore the most recent archived version
                        restored = _restore_from_archive(original_filepath, archive_dir)
                        if restored:
                            logging.info(f"Restored {original_filepath} from archive")
                            stats['restored'] += 1
                        else:
                            logging.warning(f"Could not restore archived file: {original_filepath}")
                            stats['skipped'] += 1
                    else:
                        stats['restored'] += 1

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