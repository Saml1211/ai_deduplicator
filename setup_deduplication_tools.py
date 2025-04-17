#!/usr/bin/env python3
"""
Setup Script for Deduplication Tools

This script creates a dedicated directory structure for the deduplication tools
and makes them easily accessible across all your repositories.

Usage:
    python setup_deduplication_tools.py [--global]
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

# Default location for the tools
DEFAULT_TOOLS_DIR = os.path.expanduser("~/utils/deduplication_tools")

def setup_global_tools(tools_dir):
    """Set up the deduplication tools in a global location."""
    print(f"Setting up deduplication tools in {tools_dir}...")
    
    # Create the tools directory if it doesn't exist
    os.makedirs(tools_dir, exist_ok=True)
    
    # Copy the deduplication scripts to the tools directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    files_to_copy = [
        "deduplicate_files.py",
        "ai_dynamic_deduplicate.py",
        "deduplicate_README.md",
        "ai_deduplicate_README.md",
    ]
    
    for file in files_to_copy:
        source_path = os.path.join(script_dir, file)
        target_path = os.path.join(tools_dir, file)
        
        if os.path.exists(source_path):
            shutil.copy2(source_path, target_path)
            print(f"Copied {file} to {tools_dir}")
        else:
            print(f"Warning: Could not find {file} in {script_dir}")
    
    # Create the wrapper scripts
    create_wrapper_scripts(tools_dir)
    
    # Add to PATH if global installation
    setup_path_integration(tools_dir)
    
    print("\nSetup complete!")
    print(f"\nDeduplication tools are now installed in: {tools_dir}")
    print("\nYou can now use the tools with these commands:")
    print("  deduplicate - Run the standard deduplication script")
    print("  ai-deduplicate - Run the AI-driven deduplication script")
    
    if os.name == 'posix':  # Unix-like systems
        print("\nIf the commands aren't available, you may need to restart your terminal or run:")
        print(f"  export PATH=\"$PATH:{tools_dir}\"")

def create_wrapper_scripts(tools_dir):
    """Create wrapper scripts for easy access."""
    
    # Create standard deduplication wrapper
    standard_wrapper_path = os.path.join(tools_dir, "deduplicate")
    with open(standard_wrapper_path, "w") as f:
        if os.name == 'posix':  # Unix-like systems
            f.write("#!/bin/bash\n\n")
            f.write(f"python3 {os.path.join(tools_dir, 'deduplicate_files.py')} \"$@\"\n")
        else:  # Windows
            f.write(f"@echo off\n\n")
            f.write(f"python {os.path.join(tools_dir, 'deduplicate_files.py')} %*\n")
    
    # Create AI deduplication wrapper
    ai_wrapper_path = os.path.join(tools_dir, "ai-deduplicate")
    with open(ai_wrapper_path, "w") as f:
        if os.name == 'posix':  # Unix-like systems
            f.write("#!/bin/bash\n\n")
            f.write(f"python3 {os.path.join(tools_dir, 'ai_dynamic_deduplicate.py')} \"$@\"\n")
        else:  # Windows
            f.write(f"@echo off\n\n")
            f.write(f"python {os.path.join(tools_dir, 'ai_dynamic_deduplicate.py')} %*\n")
    
    # Make the wrapper scripts executable on Unix-like systems
    if os.name == 'posix':
        os.chmod(standard_wrapper_path, 0o755)
        os.chmod(ai_wrapper_path, 0o755)
        
    # Create Windows batch files if on Windows
    if os.name != 'posix':
        with open(os.path.join(tools_dir, "deduplicate.bat"), "w") as f:
            f.write(f"@echo off\n\n")
            f.write(f"python {os.path.join(tools_dir, 'deduplicate_files.py')} %*\n")
        
        with open(os.path.join(tools_dir, "ai-deduplicate.bat"), "w") as f:
            f.write(f"@echo off\n\n")
            f.write(f"python {os.path.join(tools_dir, 'ai_dynamic_deduplicate.py')} %*\n")

def setup_path_integration(tools_dir):
    """Add the tools directory to the PATH."""
    
    if os.name == 'posix':  # Unix-like systems
        # Check if .bashrc or .zshrc exists
        bashrc_path = os.path.expanduser("~/.bashrc")
        zshrc_path = os.path.expanduser("~/.zshrc")
        
        if os.path.exists(zshrc_path):
            config_path = zshrc_path
        elif os.path.exists(bashrc_path):
            config_path = bashrc_path
        else:
            print("Could not find .bashrc or .zshrc to update PATH.")
            return
        
        # Check if the tools directory is already in PATH
        with open(config_path, "r") as f:
            content = f.read()
        
        path_line = f'export PATH="$PATH:{tools_dir}"'
        if path_line not in content:
            # Add the tools directory to PATH
            with open(config_path, "a") as f:
                f.write(f"\n# Added by deduplication tools setup\n{path_line}\n")
            
            print(f"Added {tools_dir} to PATH in {config_path}")
        else:
            print(f"{tools_dir} is already in PATH")
    
    elif os.name == 'nt':  # Windows
        try:
            # Get the current PATH
            process = subprocess.run(
                ["powershell", "-Command", "[Environment]::GetEnvironmentVariable('Path', 'User')"],
                capture_output=True,
                text=True,
                check=True
            )
            current_path = process.stdout.strip()
            
            # Check if the tools directory is already in PATH
            if tools_dir.lower() not in current_path.lower():
                # Add the tools directory to PATH
                new_path = current_path + ";" + tools_dir
                subprocess.run(
                    ["powershell", "-Command", f"[Environment]::SetEnvironmentVariable('Path', '{new_path}', 'User')"],
                    check=True
                )
                print(f"Added {tools_dir} to PATH")
            else:
                print(f"{tools_dir} is already in PATH")
        except subprocess.CalledProcessError:
            print("Failed to update PATH. You may need to add it manually.")

def create_local_symlinks():
    """Create symlinks to the global tools in the current directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tools_dir = DEFAULT_TOOLS_DIR
    
    if not os.path.exists(tools_dir):
        print(f"Error: Global tools directory {tools_dir} not found.")
        print("Run with --global first to set up the global tools.")
        return
    
    # Create symlinks to the wrapper scripts
    if os.name == 'posix':  # Unix-like systems
        for script in ["deduplicate", "ai-deduplicate"]:
            source = os.path.join(tools_dir, script)
            target = os.path.join(script_dir, script)
            
            if os.path.exists(source) and not os.path.exists(target):
                os.symlink(source, target)
                print(f"Created symlink: {target} -> {source}")
    else:  # Windows
        for script in ["deduplicate.bat", "ai-deduplicate.bat"]:
            source = os.path.join(tools_dir, script)
            target = os.path.join(script_dir, script)
            
            if os.path.exists(source) and not os.path.exists(target):
                shutil.copy2(source, target)
                print(f"Copied {script} to current directory")
    
    print("\nLocal setup complete!")
    print("You can now use the deduplication tools from this directory.")

def main():
    parser = argparse.ArgumentParser(description="Set up deduplication tools")
    parser.add_argument("--global", dest="global_install", action="store_true",
                        help="Install the tools globally (in ~/utils/deduplication_tools)")
    parser.add_argument("--tools-dir", dest="tools_dir", default=DEFAULT_TOOLS_DIR,
                        help=f"Custom directory for global installation (default: {DEFAULT_TOOLS_DIR})")
    args = parser.parse_args()
    
    if args.global_install:
        setup_global_tools(args.tools_dir)
    else:
        create_local_symlinks()

if __name__ == "__main__":
    main()