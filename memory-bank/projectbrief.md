# AI Deduplicator Project Brief

## Project Overview
AI Deduplicator is a suite of tools designed to bring intelligent organization to file systems. It consists of an advanced AI-driven organizer that analyzes file content and patterns to propose optimal directory structures, alongside a traditional rule-based deduplicator.

## Core Requirements

1. **AI-Driven Organizer Tool** (`ai_dynamic_deduplicate.py`):
   - Analyze file content, metadata, naming conventions, and existing directory patterns
   - Generate custom organization strategies for target directories
   - Provide content-aware grouping for different file types and domains
   - Identify and handle duplicate files based on content hash
   - Support multiple AI options (local LM Studio and OpenAI API)
   - Allow deep AI configuration via command-line or configuration file
   - Include heuristic fallback for when AI is unavailable
   - Optional visualization capabilities for file distribution

2. **Standard Deduplicator Tool** (`deduplicate_files.py`):
   - Provide rule-based deduplication using predefined structure
   - Identify true duplicates using content hashing (SHA-256)

3. **Common Features**:
   - Dry-run mode to preview changes
   - Detailed reporting and logging
   - Command-line interface

4. **Usability and Installation**:
   - Packaged using standard Python tools
   - Support for global installation and command-line access
   - Clear documentation for setup and usage
   - Support for virtual environments

## Constraints and Considerations
- Python 3.6+ compatibility
- Minimal core dependencies (requests)
- Optional dependencies for enhanced functionality (openai, pandas, matplotlib)
- Prioritize data safety with dry-run mode and detailed logging 