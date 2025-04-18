# AI Deduplicator Project

A suite of tools designed to bring intelligent organization to file systems using AI-driven analysis and traditional rule-based deduplication.

## Core Features

### AI-Driven Organizer (`ai_dynamic_deduplicate.py`)
- Analyzes file content, metadata, and existing patterns
- Generates custom organization strategies
- Provides content-aware grouping
- Identifies and handles duplicate files
- Supports multiple AI options (Local LM Studio and OpenAI)
- Allows deep AI configuration
- Includes heuristic fallback for when AI is unavailable
- Optional visualization capabilities

### Standard Deduplicator (`deduplicate_files.py`)
- Rule-based deduplication using predefined structures
- Content hashing with SHA-256

## Common Features
- Dry-run mode to preview changes
- Detailed reporting (JSON reports)
- Comprehensive logging
- Command-line interface

## Technical Implementation
- Python 3.6+ compatibility
- Modular design with shared utilities
- Minimal core dependencies (requests)
- Optional dependencies for enhanced functionality (openai, pandas, matplotlib)

## Usage Examples
- Downloads folder cleanup
- Project directory structuring
- Research data consolidation
- Photo library management
- Financial document archiving

## Project Status
The project is currently operational with both the AI-driven organizer and standard deduplication tools functional. Ongoing improvements focus on enhancing AI analysis capabilities and expanding the types of organizational strategies the system can generate. 