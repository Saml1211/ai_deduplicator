#!/usr/bin/env python3
"""
Sample script for testing file analysis capabilities.
"""

import os
import sys
import json
from datetime import datetime


def analyze_files(directory):
    """
    Analyze files in a directory and return statistics.
    """
    stats = {
        "file_count": 0,
        "extensions": {},
        "total_size": 0,
        "largest_file": {"name": "", "size": 0}
    }
    
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            ext = os.path.splitext(file)[1].lower() or "no_extension"
            
            # Update stats
            stats["file_count"] += 1
            stats["total_size"] += file_size
            stats["extensions"][ext] = stats["extensions"].get(ext, 0) + 1
            
            # Check if this is the largest file
            if file_size > stats["largest_file"]["size"]:
                stats["largest_file"] = {"name": file_path, "size": file_size}
    
    return stats


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: script.py <directory>")
        return 1
    
    directory = sys.argv[1]
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        return 1
    
    try:
        results = analyze_files(directory)
        print(json.dumps(results, indent=2))
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
