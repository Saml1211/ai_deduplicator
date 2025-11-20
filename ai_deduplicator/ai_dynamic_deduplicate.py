#!/usr/bin/env python3
"""
AI-Driven Dynamic File Deduplication Script

This script uses AI to dynamically determine the optimal organization structure
for deduplicating files based on content analysis and file system patterns.

Features:
- Analyzes file content and metadata to understand the data domain
- Dynamically generates an organization strategy using AI (OpenAI API or LM Studio local server)
- Identifies duplicate files based on content hash
- Reorganizes files according to the AI-determined structure
- Provides detailed reporting and visualization of changes
- Displays AI reasoning and strategy in terminal output
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
import mimetypes
import tempfile
import requests
from typing import Dict, List, Tuple, Set, Any, Optional
import random  # For simulation purposes

# Import common utilities
from . import dedup_utils

# Optional imports for enhanced functionality
try:
    import openai  # For OpenAI API integration
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

# AI Configuration - Default settings for AI backends
AI_CONFIG = {
    'lm_studio': {
        'model': 'gemma-3-27b-it',
        'temperature': 0.7,
        'max_tokens': 2000,
        'system_prompt': 'You are a file system organization expert.',
        'url': 'http://127.0.0.1:1234/v1/chat/completions',
        'timeout': 300
    },
    'openai': {
        'model': 'gpt-4',
        'temperature': 0.7,
        'max_tokens': 2000,
        'system_prompt': 'You are a file system organization expert.',
        'timeout': 60
    }
}

# File content analysis functions
def analyze_file_content(filepath: str) -> Dict[str, Any]:
    """
    Analyze file content to extract metadata and content features.
    Returns a dictionary of analysis results.
    """
    analysis = {
        'path': filepath,
        'size': os.path.getsize(filepath),
        'extension': os.path.splitext(filepath)[1].lower(),
        'mime_type': mimetypes.guess_type(filepath)[0] or 'unknown',
        'last_modified': datetime.fromtimestamp(os.path.getmtime(filepath)),
        'is_binary': False,
        'text_sample': '',
        'keywords': set(),
    }
    
    # Determine if file is binary or text
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            sample = f.read(4096)  # Read first 4KB for analysis
            analysis['is_binary'] = False
            analysis['text_sample'] = sample
            
            # Extract potential keywords (simple approach)
            words = re.findall(r'\b[A-Za-z]{3,}\b', sample)
            analysis['keywords'] = set([w.lower() for w in words])
    except UnicodeDecodeError:
        analysis['is_binary'] = True
    
    return analysis

def validate_strategy(strategy: Dict[str, str]) -> bool:
    """
    Validate that a strategy dictionary has the expected structure and safe content.

    Performs comprehensive validation including:
    - Correct data types (dict with string keys and values)
    - Valid regex patterns (compiles without errors)
    - Path traversal prevention (no ../ or ..)
    - Path security (relative paths only, no absolute paths)
    - Character whitelisting (no suspicious/injection characters)
    - Null byte detection
    - Command injection prevention

    Returns True if valid, raises ValueError with detailed error messages if invalid.
    """
    # Type validation - strategy must be a dictionary
    if not isinstance(strategy, dict):
        error_msg = f"Strategy must be a dictionary, got {type(strategy).__name__}"
        logging.error(f"VALIDATION FAILED: {error_msg}")
        raise ValueError(error_msg)

    # Empty check
    if len(strategy) == 0:
        error_msg = "Strategy dictionary is empty"
        logging.error(f"VALIDATION FAILED: {error_msg}")
        raise ValueError(error_msg)

    # Validate each pattern-target pair in the strategy
    for pattern, target in strategy.items():
        # TYPE VALIDATION
        if not isinstance(pattern, str):
            error_msg = f"Strategy pattern must be string, got {type(pattern).__name__}: {pattern}"
            logging.error(f"VALIDATION FAILED: {error_msg}")
            raise ValueError(error_msg)
        if not isinstance(target, str):
            error_msg = f"Strategy target must be string, got {type(target).__name__}: {target}"
            logging.error(f"VALIDATION FAILED: {error_msg}")
            raise ValueError(error_msg)

        # EMPTY STRING VALIDATION
        if not pattern:
            error_msg = "Strategy pattern cannot be empty string"
            logging.error(f"VALIDATION FAILED: {error_msg}")
            raise ValueError(error_msg)
        if not target:
            error_msg = "Strategy target cannot be empty string"
            logging.error(f"VALIDATION FAILED: {error_msg}")
            raise ValueError(error_msg)

        # REGEX PATTERN VALIDATION - attempt to compile the pattern
        try:
            re.compile(pattern)
            logging.debug(f"Regex pattern validated: '{pattern}'")
        except re.error as e:
            error_msg = f"Invalid regex pattern '{pattern}': {str(e)}"
            logging.error(f"VALIDATION FAILED: {error_msg}")
            raise ValueError(error_msg)

        # PATH TRAVERSAL PREVENTION - check for directory traversal attempts
        if '../' in target or '..' in target:
            error_msg = f"Path traversal attempt detected in target '{target}': contains '..' or '../'"
            logging.error(f"SECURITY VIOLATION - VALIDATION FAILED: {error_msg}")
            raise ValueError(error_msg)

        # ABSOLUTE PATH PREVENTION - targets must be relative paths
        if os.path.isabs(target):
            error_msg = f"Absolute path detected in target '{target}': targets must be relative paths"
            logging.error(f"SECURITY VIOLATION - VALIDATION FAILED: {error_msg}")
            raise ValueError(error_msg)

        # NULL BYTE DETECTION - prevent null byte injection
        if '\x00' in pattern:
            error_msg = f"Null byte detected in pattern '{pattern}': null bytes not allowed"
            logging.error(f"SECURITY VIOLATION - VALIDATION FAILED: {error_msg}")
            raise ValueError(error_msg)
        if '\x00' in target:
            error_msg = f"Null byte detected in target '{target}': null bytes not allowed"
            logging.error(f"SECURITY VIOLATION - VALIDATION FAILED: {error_msg}")
            raise ValueError(error_msg)

        # COMMAND INJECTION PREVENTION - check for shell metacharacters in target
        shell_injection_patterns = ['$(', '`', ';&', '|', '>', '<']
        for injection_pattern in shell_injection_patterns:
            if injection_pattern in target:
                error_msg = f"Command injection attempt detected in target '{target}': contains '{injection_pattern}'"
                logging.error(f"SECURITY VIOLATION - VALIDATION FAILED: {error_msg}")
                raise ValueError(error_msg)

        # SUSPICIOUS CHARACTER WHITELIST - target path validation
        # Allow: alphanumeric, dots, slashes, underscores, hyphens, spaces
        suspicious_chars = re.findall(r'[^a-zA-Z0-9._\-/\s]', target)
        if suspicious_chars:
            unique_suspicious = set(suspicious_chars)
            error_msg = f"Suspicious characters detected in target '{target}': {unique_suspicious}"
            logging.error(f"SECURITY VIOLATION - VALIDATION FAILED: {error_msg}")
            raise ValueError(error_msg)

        # RELATIVE PATH CONVENTION - warn if target doesn't follow relative path convention
        if not (target.startswith('./') or target.startswith('.')):
            logging.debug(f"Target '{target}' does not follow './' relative path convention")

        logging.debug(f"Validated strategy entry: '{pattern}' -> '{target}'")

    # Log successful validation with summary
    logging.info(f"Strategy validation successful: {len(strategy)} pattern-target pairs validated")
    return True


# AI-driven organization strategy
def generate_ai_organization_strategy(file_analyses: List[Dict[str, Any]], duplicates: Dict[str, List[str]], args) -> Dict[str, str]:
    """
    Generate an organization strategy using AI analysis of file content and patterns.
    Returns a dictionary mapping regex patterns to target directories.
    
    This function can be implemented in multiple ways:
    1. Use OpenAI API if available
    2. Use LM Studio local server
    3. Use a local ML model if available
    4. Use a rule-based heuristic approach as fallback
    """
    logging.info("Generating AI-driven organization strategy...")
    
    # Get file extensions and their frequencies
    extension_counts = defaultdict(int)
    for analysis in file_analyses:
        extension_counts[analysis['extension']] += 1
    
    # Get directory structure patterns
    dir_patterns = set()
    for analysis in file_analyses:
        path_parts = Path(analysis['path']).parts
        if len(path_parts) > 1:
            dir_patterns.add(path_parts[-2])
    
    # Prepare data for AI prompt
    extensions = ", ".join([f"{ext} ({count})" for ext, count in sorted(extension_counts.items(), key=lambda x: x[1], reverse=True)[:10]])
    directories = ", ".join(list(dir_patterns)[:10])
    
    # Sample of file paths
    sample_paths = [analysis['path'] for analysis in file_analyses[:10]]
    path_sample = "\n".join(sample_paths)
    
    # Generate prompt
    prompt = f"""
    Analyze the following information about a file system and generate an optimal organization strategy:
    
    Top file extensions: {extensions}
    Common directory names: {directories}
    
    Sample file paths:
    {path_sample}
    
    Based on this information, generate a JSON structure mapping regex patterns to target directories.
    The regex patterns should match file paths, and the target directories should be relative paths.
    Focus on creating a logical organization that groups similar files and reduces duplication.
    """
    
    # Skip AI if --no-ai flag is set
    if args.no_ai:
        logging.info("Skipping AI processing and using heuristics only")
        return generate_heuristic_strategy(file_analyses, duplicates, extension_counts, dir_patterns)
    
    # Try LM Studio first (command line argument will determine this)
    if args.use_lm_studio:
        try:
            strategy, ai_response = generate_lm_studio_strategy(prompt, args)
            logging.info("AI Response from LM Studio:")
            logging.info("-----------------------------------")
            logging.info(ai_response)
            logging.info("-----------------------------------")
            return strategy
        except Exception as e:
            logging.warning(f"LM Studio strategy generation failed: {e}. Trying next method.")

    # Try OpenAI if available
    if OPENAI_AVAILABLE and os.environ.get('OPENAI_API_KEY'):
        try:
            strategy, ai_response = generate_openai_strategy(prompt, args)
            logging.info("AI Response from OpenAI:")
            logging.info("-----------------------------------")
            logging.info(ai_response)
            logging.info("-----------------------------------")
            return strategy
        except Exception as e:
            logging.warning(f"OpenAI strategy generation failed: {e}. Falling back to heuristic approach.")
    
    # Default: Use rule-based heuristic approach
    logging.info("Using heuristic-based organization strategy (no AI available)")
    return generate_heuristic_strategy(file_analyses, duplicates, extension_counts, dir_patterns)

def load_config_file():
    """Load configuration from a local .deduplication_config.json file if it exists."""
    config_path = os.path.join(os.getcwd(), '.deduplication_config.json')
    config = AI_CONFIG.copy()
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
            
            # Update LM Studio configuration if provided
            if 'lm_studio' in user_config:
                config['lm_studio'].update(user_config['lm_studio'])
            
            # Update OpenAI configuration if provided
            if 'openai' in user_config:
                config['openai'].update(user_config['openai'])
                
            logging.info(f"Loaded configuration from {config_path}")
        except json.JSONDecodeError:
            logging.warning(f"Failed to parse configuration file: {config_path}")
    
    return config

def generate_lm_studio_strategy(prompt, args):
    """Generate organization strategy using LM Studio local server."""
    config = load_config_file()
    lm_config = config['lm_studio']

    model = lm_config.get('model', 'gemma-3-27b-it')
    temperature = lm_config.get('temperature', 0.7)
    max_tokens = lm_config.get('max_tokens', 2000)
    system_prompt = lm_config.get('system_prompt', "You are a file system organization expert.")
    # Allow command-line override of timeout
    timeout = args.timeout if args.timeout else lm_config.get('timeout', 300)

    # Allow command-line override of URL
    url = args.lm_studio_url if args.lm_studio_url else lm_config.get('url', "http://127.0.0.1:1234/v1/chat/completions")
    
    logging.info(f"Generating organization strategy using LM Studio ({model})...")
    logging.info(f"Temperature: {temperature}, Max tokens: {max_tokens}")
    logging.info(f"System prompt: \"{system_prompt}\"")
    
    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=timeout  # Use timeout from config
        )
        
        response.raise_for_status()  # Raise exception for HTTP errors
        response_data = response.json()
        
        # Extract content from response
        content = response_data['choices'][0]['message']['content']
        
        # Find JSON in the response
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            # If no JSON found, try to extract patterns from text
            logging.warning("No JSON found in LM Studio response, attempting to parse text response")
            strategy = parse_text_response(content)
            if not strategy:
                raise ValueError("Could not extract organization strategy from LM Studio response")
        else:
            json_str = content[json_start:json_end]
            try:
                strategy = json.loads(json_str)
                # Convert to our expected format
                strategy = {pattern: target for pattern, target in strategy.items()}
            except json.JSONDecodeError:
                logging.error("Failed to parse LM Studio response as JSON")
                raise

        # Validate the strategy structure
        validate_strategy(strategy)

        return strategy, content
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error connecting to LM Studio server: {e}")
        raise
    except Exception as e:
        logging.error(f"Error processing LM Studio response: {e}")
        raise

def parse_text_response(text):
    """Parse organization strategy from text response when JSON is not available."""
    strategy = {}
    lines = text.split('\n')
    
    # Look for lines with patterns and directories
    for line in lines:
        if '->' in line or ':' in line or '=' in line:
            parts = None
            if '->' in line:
                parts = line.split('->')
            elif ':' in line:
                parts = line.split(':')
            elif '=' in line:
                parts = line.split('=')
                
            if parts and len(parts) == 2:
                pattern = parts[0].strip().strip('"\'')
                directory = parts[1].strip().strip('"\'')
                
                # Make sure the pattern looks like a regex
                if '*' in pattern or '\\' in pattern:
                    # Clean up directory path
                    if not directory.startswith('./'):
                        directory = './' + directory
                    if not directory.endswith('/'):
                        directory += '/'
                        
                    strategy[pattern] = directory
    
    # If we found at least some patterns, return them
    if strategy:
        return strategy
    return None

def generate_openai_strategy(prompt, args):
    """Generate organization strategy using OpenAI API."""
    config = load_config_file()
    openai_config = config['openai']

    model = openai_config.get('model', 'gpt-4')
    temperature = openai_config.get('temperature', 0.7)
    max_tokens = openai_config.get('max_tokens', 2000)
    system_prompt = openai_config.get('system_prompt', "You are a file system organization expert.")
    # Allow command-line override of timeout
    timeout = args.timeout if args.timeout else openai_config.get('timeout', 60)

    # Create OpenAI client (v1.0+ API) - API key read from OPENAI_API_KEY env variable
    from openai import OpenAI
    client = OpenAI()

    logging.info(f"Generating organization strategy using OpenAI ({model})...")
    logging.info(f"Temperature: {temperature}, Max tokens: {max_tokens}")
    logging.info(f"System prompt: \"{system_prompt}\"")

    # Call OpenAI API with timeout (v1.0+ syntax)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )

    # Extract content from response
    content = response.choices[0].message.content
    
    # Extract JSON from response
    json_start = content.find('{')
    json_end = content.rfind('}') + 1
    json_str = content[json_start:json_end]
    
    try:
        strategy = json.loads(json_str)
        # Convert to our expected format
        strategy = {pattern: target for pattern, target in strategy.items()}

        # Validate the strategy structure
        validate_strategy(strategy)

        return strategy, content
    except json.JSONDecodeError:
        logging.error("Failed to parse OpenAI response as JSON")
        raise
    
def generate_heuristic_strategy(file_analyses, duplicates, extension_counts, dir_patterns):
    """Generate organization strategy using rule-based heuristics."""
    strategy = {}
    
    # Group by common extensions
    for ext, count in extension_counts.items():
        if ext and count > 1:
            if ext.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'):
                strategy[f'.*\\{ext}$'] = './organized/images/'
            elif ext.lower() in ('.mp3', '.wav', '.flac', '.aac', '.ogg'):
                strategy[f'.*\\{ext}$'] = './organized/audio/'
            elif ext.lower() in ('.mp4', '.avi', '.mov', '.mkv', '.wmv'):
                strategy[f'.*\\{ext}$'] = './organized/videos/'
            elif ext.lower() in ('.doc', '.docx', '.pdf', '.txt', '.rtf', '.odt'):
                strategy[f'.*\\{ext}$'] = './organized/documents/'
            elif ext.lower() in ('.xls', '.xlsx', '.csv', '.numbers'):
                strategy[f'.*\\{ext}$'] = './organized/spreadsheets/'
            elif ext.lower() in ('.py', '.js', '.java', '.c', '.cpp', '.h', '.cs', '.php', '.rb', '.go'):
                strategy[f'.*\\{ext}$'] = './organized/code/'
            elif ext.lower() in ('.zip', '.rar', '.tar', '.gz', '.7z'):
                strategy[f'.*\\{ext}$'] = './organized/archives/'
            else:
                # Catch-all for other extensions with multiple files
                strategy[f'.*\\{ext}$'] = f'./organized/by_type/{ext[1:] if ext.startswith(".") else ext}/'
    
    # Special patterns based on content analysis
    keyword_patterns = {
        'tax': './organized/financial/tax/',
        'invoice': './organized/financial/invoices/',
        'receipt': './organized/financial/receipts/',
        'statement': './organized/financial/statements/',
        'budget': './organized/financial/budget/',
    }
    
    # Add keyword-based patterns
    for keyword, target in keyword_patterns.items():
        strategy[f'.*{keyword}.*'] = target
    
    # Add date-based organization for timestamped files
    strategy[r'.*\d{4}[-_]\d{2}[-_]\d{2}.*'] = './organized/by_date/'
    
    # Default catch-all pattern
    strategy[r'.*'] = './organized/unsorted/'
    
    return strategy

def apply_organization_strategy(strategy: Dict[str, str], duplicates: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """
    Apply the organization strategy to duplicates.
    Returns a list of operations to perform.
    """
    operations = []
    
    for file_hash, filepaths in duplicates.items():
        # Group files by their target location according to strategy
        location_groups = defaultdict(list)
        
        for filepath in filepaths:
            target_location = None
            
            # Find matching pattern in strategy
            for pattern, location in strategy.items():
                if re.match(pattern, filepath):
                    target_location = location
                    break
            
            # Use default if no pattern matches (shouldn't happen with catch-all)
            if target_location is None:
                target_location = './organized/unsorted/'
                
            location_groups[target_location].append(filepath)
        
        # For each target location, keep one file and mark others for removal
        for target_location, files in location_groups.items():
            if not files:
                continue
                
            # Choose the file to keep (simplest filename or first one)
            files_sorted = sorted(files, key=lambda f: len(os.path.basename(f)))
            keep_file = files_sorted[0]
            
            # Prepare target path
            filename = os.path.basename(keep_file)
            # Ensure target_location ends with a separator
            if not target_location.endswith(os.sep):
                target_location += os.sep
            target_path = os.path.join(target_location, filename)
            
            # Check if target path already exists (with a different hash)
            # Use the utility function for hashing
            target_hash = dedup_utils.calculate_file_hash(target_path) if os.path.exists(target_path) else None
            if target_hash and target_hash != file_hash:
                # Generate a unique name by adding a timestamp
                name, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_filename = f"{name}_{timestamp}{ext}"
                target_path = os.path.join(target_location, new_filename)
            
            operations.append({
                'action': 'move',
                'file': keep_file,
                'destination': target_path,
                'reason': 'moving to AI-determined location'
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

def visualize_strategy(strategy: Dict[str, str], file_analyses: List[Dict[str, Any]]) -> None:
    """Generate visualizations of the organization strategy."""
    if not VISUALIZATION_AVAILABLE:
        logging.warning("Visualization libraries not available. Install pandas and matplotlib for visualization support.")
        return
    
    # Create a DataFrame for analysis
    df = pd.DataFrame(file_analyses)
    
    # Count files by extension
    ext_counts = df['extension'].value_counts().head(10)
    plt.figure(figsize=(10, 6))
    ext_counts.plot(kind='bar')
    plt.title('Top 10 File Extensions')
    plt.xlabel('Extension')
    plt.ylabel('Count')
    plt.tight_layout()
    plt.savefig('file_extensions.png')
    
    # Count files by target directory
    targets = []
    for analysis in file_analyses:
        filepath = analysis['path']
        target = None
        for pattern, location in strategy.items():
            if re.match(pattern, filepath):
                target = location
                break
        targets.append(target)
    
    df['target'] = targets
    target_counts = df['target'].value_counts().head(10)
    plt.figure(figsize=(10, 6))
    target_counts.plot(kind='bar')
    plt.title('Top 10 Target Directories')
    plt.xlabel('Target Directory')
    plt.ylabel('Count')
    plt.tight_layout()
    plt.savefig('target_directories.png')
    
    logging.info("Visualizations saved to file_extensions.png and target_directories.png")

def main():
    parser = argparse.ArgumentParser(description='AI-Driven File Organization and Deduplication')
    parser.add_argument('--dry-run', action='store_true', help='Simulate operations without making changes')
    parser.add_argument('--directory', '-d', default='.', help='Directory to analyze (default: current directory)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--visualize', action='store_true', help='Generate visualizations')
    parser.add_argument('--use-lm-studio', action='store_true', help='Use LM Studio local server for AI generation')
    parser.add_argument('--config', help='Path to a custom configuration file')
    parser.add_argument('--temperature', type=float, help='Temperature for AI generation (0.0-1.0)')
    parser.add_argument('--system-prompt', help='Custom system prompt for AI')
    parser.add_argument('--no-ai', action='store_true', help='Skip AI processing and use heuristics only')
    parser.add_argument('--timeout', type=int, help='Timeout in seconds for AI requests')
    parser.add_argument('--lm-studio-url', help='Custom LM Studio server URL')
    parser.add_argument('--workers', type=int, help='Number of parallel workers for hashing (default: min(cpu_count, 8)). Recommended: 2-8 for SSD, 4-16 for HDD. Higher values may improve performance on fast storage but increase memory usage.')
    parser.add_argument('--undo', action='store_true', help='Rollback the last AI-driven organization operation')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt and execute operations (for automation)')
    parser.add_argument('--interactive', action='store_true', help='Force confirmation prompt even with --yes flag')
    parser.add_argument('--skip-patterns', type=str, default='', help='Comma-separated list of directory/file patterns to skip (example: ".custom_dir,temp_files,cache")')
    parser.add_argument('--skip-extensions', type=str, default='', help='Comma-separated list of file extensions to skip (example: ".tmp,.bak,.log")')
    parser.add_argument('--no-default-skips', action='store_true', help='Disable default skip patterns and only use custom patterns')
    parser.add_argument('--force-continue', action='store_true', help='Bypass transaction log safety checks and execute without creating a transaction log. WARNING: Use only if you fully understand the risks. Rollback will be impossible if something goes wrong.')
    args = parser.parse_args()

    # Validate workers argument if provided
    if args.workers is not None:
        if args.workers < 1:
            parser.error('--workers must be >= 1')

    # Set up logging using the utility function
    logger = dedup_utils.setup_logging('ai_deduplication.log', args.verbose)

    # Handle undo/rollback mode
    if args.undo:
        logging.info("ROLLBACK MODE: Undoing previous AI organization operation...")
        logging.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
        stats = dedup_utils.rollback_operations(dry_run=args.dry_run)
        logging.info("Rollback complete!")
        logging.info(f"{'No changes were made (dry run)' if args.dry_run else 'Changes have been rolled back.'}")
        return

    # Start the deduplication process
    logging.info("Starting AI-driven file organization process...")
    logging.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logging.info(f"Target directory: {os.path.abspath(args.directory)}")
    
    # Step 1: Parse custom skip patterns
    custom_skip_patterns = None
    custom_skip_extensions = None
    
    if args.skip_patterns:
        custom_skip_patterns = set(p.strip() for p in args.skip_patterns.split(',') if p.strip())
        logging.info(f"Using custom skip patterns: {custom_skip_patterns}")
    
    if args.skip_extensions:
        custom_skip_extensions = set(e.strip() for e in args.skip_extensions.split(',') if e.strip())
        logging.info(f"Using custom skip extensions: {custom_skip_extensions}")
    
    use_defaults = not args.no_default_skips
    if args.no_default_skips:
        logging.info("Default skip patterns disabled; using only custom patterns")
    
    # Step 2: Scan directory and analyze files using the utility function
    # Pass analyze_content=True as this script needs the analysis results
    duplicates, file_analyses = dedup_utils.scan_directory(
        args.directory, 
        analyze_content=True,
        skip_patterns=custom_skip_patterns,
        skip_extensions=custom_skip_extensions,
        use_default_skips=use_defaults,
        workers=args.workers
    )
    
    # Apply command-line overrides to configuration
    if args.config:
        if os.path.exists(args.config):
            try:
                with open(args.config, 'r') as f:
                    custom_config = json.load(f)
                
                # Update the global configuration
                for key, value in custom_config.items():
                    if key in AI_CONFIG:
                        AI_CONFIG[key].update(value)
                
                logging.info(f"Loaded custom configuration from {args.config}")
            except json.JSONDecodeError:
                logging.warning(f"Failed to parse custom configuration file: {args.config}")
        else:
            logging.warning(f"Custom configuration file not found: {args.config}")
    
    # Override temperature if provided
    if args.temperature is not None:
        AI_CONFIG['lm_studio']['temperature'] = args.temperature
        AI_CONFIG['openai']['temperature'] = args.temperature
        logging.info(f"Using custom temperature: {args.temperature}")
    
    # Override system prompt if provided
    if args.system_prompt:
        AI_CONFIG['lm_studio']['system_prompt'] = args.system_prompt
        AI_CONFIG['openai']['system_prompt'] = args.system_prompt
        logging.info(f"Using custom system prompt: \"{args.system_prompt}\"")
    
    # Step 3: Generate AI-driven organization strategy
    if args.use_lm_studio:
        logging.info("Using LM Studio local server for AI strategy generation")
    strategy = generate_ai_organization_strategy(file_analyses, duplicates, args)
    logging.info(f"Generated AI organization strategy with {len(strategy)} patterns:")
    # Log the generated strategy for clarity
    for pattern, target in strategy.items():
        logging.info(f"  '{pattern}' -> '{target}'")
    
    # Optional: Visualize strategy
    if args.visualize:
        visualize_strategy(strategy, file_analyses)
    
    # Step 4: Apply organization strategy to create operations plan
    operations = apply_organization_strategy(strategy, duplicates)
    logging.info(f"Generated plan with {len(operations)} operations")
    
    # Step 5: Execute operations using the utility function
    try:
        stats = dedup_utils.execute_operations(operations, dry_run=args.dry_run, skip_confirmation=args.yes, interactive=args.interactive)
    except dedup_utils.TransactionLogError as e:
        logging.error(f"Failed to execute operations: {e}")
        logging.info("No file operations were performed due to transaction log creation failure.")
        sys.exit(1)

    # Step 6: Generate and save report using utility functions
    report = dedup_utils.generate_report(duplicates, operations, stats, strategy)
    dedup_utils.save_report(report, filename='ai_deduplication_report.json')
    
    # Print summary
    logging.info("AI-driven organization process complete!")
    logging.info(f"{'No changes were made (dry run)' if args.dry_run else 'Changes have been applied based on the plan.'}")
    logging.info("See ai_deduplication_report.json for details")
    
    if args.visualize and VISUALIZATION_AVAILABLE:
        logging.info("Visualizations have been saved to file_extensions.png and target_directories.png")

if __name__ == "__main__":
    main()