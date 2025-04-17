# AI-Driven File Organization and Deduplication Tools

This repository provides a suite of tools designed to bring intelligent order to your directories. It features an advanced AI-driven organizer that analyzes file content and patterns to propose optimal structures, alongside a traditional rule-based deduplicator. A setup script facilitates easy global installation for use across all your projects.

## Core Philosophy

Go beyond simple duplicate removal. These tools aim to understand your data and create logical, maintainable directory structures, leveraging AI for dynamic adaptation to different content domains (code, documents, media, etc.).

## Features

**AI-Driven Organizer (`ai_dynamic_deduplicate.py` / `ai-deduplicate` command - Primary Tool):**
- **Intelligent Organization:** Analyzes file content, metadata, naming conventions, and existing directory patterns to generate a custom organization strategy for the target directory.
- **Content-Aware Grouping:** Recognizes different file types and domains (e.g., financial documents, code projects, images) to group related files logically.
- **Adaptive Learning:** Identifies existing organizational structures and can extend or refine them.
- **Deduplication Included:** Optionally identifies and handles duplicate files (based on content hash) as part of the organization process, consolidating them intelligently.
- **Multiple AI Options:** Integrates with LM Studio (local) and OpenAI API.
- **Deep AI Configuration:** Fine-tune AI behavior (model, temperature, prompts) via command-line or `.deduplication_config.json`.
- **Heuristic Fallback:** Provides a basic organization strategy if AI is unavailable.
- **Visualization (Optional):** Generates charts (`file_extensions.png`, `target_directories.png`) showing file distribution and the proposed AI strategy.

**Standard Deduplicator (`deduplicate_files.py` / `deduplicate` command - Legacy/Rule-Based):**
- **Rule-Based Deduplication:** Consolidates duplicate files based on a predefined, hardcoded `PREFERRED_STRUCTURE` within the script.
- **Content Hashing:** Uses SHA-256 to identify true duplicates.

**Common Features (Both Tools):**
- **Dry-Run Mode:** Preview all proposed changes before any files are moved or deleted.
- **Detailed Reporting:** Creates JSON reports (`ai_deduplication_report.json` / `deduplication_report.json`) summarizing actions.
- **Comprehensive Logging:** Records all steps and decisions to log files (`ai_deduplication.log` / `deduplication.log`).

**Setup Tool (`setup_deduplication_tools.py`):**
- **Global Installation:** Installs tools centrally for easy access.
- **Command-Line Access:** Creates `ai-deduplicate` and `deduplicate` commands.

## Requirements

- Python 3.6+
- **Required Packages:**
  ```bash
  pip install requests
  ```
- **Optional Packages** (for AI Organizer features):
  ```bash
  pip install openai pandas matplotlib
  ```
  *(Note: `pathlib` is part of the standard library in Python 3.4+)*

## Setup and Installation

Use the `setup_deduplication_tools.py` script to install the tools.

### Option 1: Global Installation (Recommended)

Installs tools to `~/utils/deduplication_tools` (default) and adds them to your PATH.

```bash
python setup_deduplication_tools.py --global
```

Now you can use `ai-deduplicate` and `deduplicate` from any directory.

### Option 2: Custom Global Location

```bash
python setup_deduplication_tools.py --global --tools-dir /path/to/your/tools
```

### Option 3: Local Symlinks (Requires Prior Global Install)

Creates local shortcuts in the current directory pointing to the global tools.

```bash
python setup_deduplication_tools.py
```

*Note: If commands aren't available after global install, restart your terminal or update your PATH manually.*

## Usage

### AI-Driven Organizer (Recommended)

Generates organization strategy dynamically based on the files in the target directory.

**Dry Run (Recommended First):**
```bash
# Analyze current directory
# Using the script directly:
python ai_dynamic_deduplicate.py --dry-run
# Using the global command (if installed):
ai-deduplicate --dry-run

# Analyze a specific directory
ai-deduplicate --directory /path/to/analyze --dry-run
```

**Using LM Studio (Local AI):**
```bash
ai-deduplicate --use-lm-studio --dry-run
```

**Using OpenAI API:**
```bash
# Ensure OPENAI_API_KEY environment variable is set
ai-deduplicate --dry-run
```

**Execute Reorganization (After Reviewing Dry Run):**
```bash
# WARNING: This modifies files!
ai-deduplicate --directory /path/to/target
```

**Execute with Visualization:**
```bash
ai-deduplicate --directory /path/to/target --visualize
```

### Standard Deduplicator (Rule-Based)

Operates based on the hardcoded `PREFERRED_STRUCTURE` in `deduplicate_files.py`.

**Dry Run:**
```bash
deduplicate --dry-run
```

**Execute:**
```bash
# WARNING: This modifies files!
deduplicate
```

## Configuration

### AI Organizer Configuration (`.deduplication_config.json`)

Create a `.deduplication_config.json` file in the directory where you run `ai-deduplicate` for persistent, repository-specific settings.

```json
{
  "lm_studio": {
    "url": "http://127.0.0.1:1234/v1/chat/completions", // Your local server URL
    "model": "local-model", // Specify model loaded in LM Studio
    "temperature": 0.7,
    "max_tokens": 2000,
    "timeout": 300, // Timeout in seconds
    "system_prompt": "You are a file system organization expert. Analyze the provided file system information and generate an optimal organization strategy (JSON format) that groups similar files together logically."
  },
  "openai": {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000,
    "timeout": 60,
    "system_prompt": "You are a file system organization expert. Analyze the provided file system information and generate an optimal organization strategy (JSON format) that groups similar files together logically."
  }
}
```

**Command-Line Overrides:**
Override config settings via arguments:
```bash
ai-deduplicate --use-lm-studio --temperature 0.2 --system-prompt "Organize these photos by event and date."
ai-deduplicate --config ./alternate_config.json
```

### Standard Deduplicator Customization

Modify the `PREFERRED_STRUCTURE` dictionary directly within the `deduplicate_files.py` script.

## Output Files

- **AI-Driven:** `ai_deduplication_report.json`, `ai_deduplication.log`, (optional) `file_extensions.png`, `target_directories.png`.
- **Standard:** `deduplication_report.json`, `deduplication.log`.

## Example Use Cases for AI Tool

- **Downloads Folder Cleanup:** Intelligently sort mixed downloaded files into relevant categories (documents, images, installers, archives).
- **Project Directory Structuring:** Analyze a project folder (code, notes, assets) and suggest a standardized structure.
- **Research Data Consolidation:** Organize papers, datasets, and notes by topic, project, or date.
- **Photo Library Management:** Group photos by inferred event, date, or potentially recognized content (future enhancement).
- **Financial Document Archiving:** Categorize scans of receipts, statements, and tax documents. 