# Dynamic File Deduplication and Organization Tools

This repository provides a suite of tools for identifying duplicate files and intelligently organizing directory structures. It includes both a standard rule-based deduplicator and an advanced AI-driven organizer. A setup script is also included to facilitate global installation and usage across multiple repositories.

## Features

**Both Tools:**
- **Content-based Deduplication:** Identifies true duplicates using SHA-256 hashing, not just filenames.
- **Dry-Run Mode:** Preview changes safely before execution.
- **Detailed Reporting:** Generates JSON reports (`deduplication_report.json` / `ai_deduplication_report.json`) detailing duplicates and actions.
- **Comprehensive Logging:** Logs all operations to a file (`deduplication.log` / `ai_deduplication.log`).

**Standard Deduplicator (`deduplicate_files.py` / `deduplicate` command):**
- **Preferred Structure Aware:** Consolidates duplicates based on a predefined directory structure within the script.

**AI-Driven Deduplicator (`ai_dynamic_deduplicate.py` / `ai-deduplicate` command):**
- **Dynamic Analysis:** Examines file content, metadata, naming patterns, and directory structures.
- **AI-Generated Strategy:** Uses AI (LM Studio or OpenAI) to create an optimal, context-aware organization plan for your specific data on each run.
- **Adaptive Organization:** Recognizes different content domains (documents, media, code) and learns existing patterns.
- **Heuristic Fallback:** Uses a rule-based approach if AI integration is unavailable.
- **Multiple AI Integration Options:** Supports LM Studio (local) and OpenAI API.
- **Deep AI Configuration:** Customize AI model, temperature, system prompts, etc., via command-line or config file.
- **Advanced Visualization (Optional):** Generates `file_extensions.png` and `target_directories.png` to visualize file distribution and the proposed organization strategy.

**Setup Tool (`setup_deduplication_tools.py`):**
- **Global Installation:** Installs tools centrally for use across repositories.
- **Easy Access:** Creates simple commands (`deduplicate`, `ai-deduplicate`) accessible from PATH.
- **Local Symlinks:** Option to create local shortcuts to global tools.

## Requirements

- Python 3.6+
- **Required Packages:**
  ```bash
  pip install requests
  ```
- **Optional Packages** (for AI Deduplicator features):
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

After installation, you can use `deduplicate` and `ai-deduplicate` commands from any directory.

### Option 2: Custom Global Location

```bash
python setup_deduplication_tools.py --global --tools-dir /path/to/your/tools
```

### Option 3: Local Symlinks (Requires Prior Global Install)

Creates local symlinks in the current directory pointing to the global tools.

```bash
python setup_deduplication_tools.py
```

*Note: If commands aren't available after global install, restart your terminal or update your PATH manually as per the setup script's output.*

## Usage

### Standard Deduplicator

Operates based on the `PREFERRED_STRUCTURE` defined within `deduplicate_files.py`.

**Dry Run (Recommended First):**
```bash
# Using the script directly
python deduplicate_files.py --dry-run

# Using the global command (if installed)
deduplicate --dry-run
```

**Verbose Dry Run:**
```bash
deduplicate --dry-run --verbose
```

**Execute (After Reviewing Dry Run):**
```bash
# WARNING: This modifies files!
deduplicate
```

### AI-Driven Deduplicator

Generates organization strategy dynamically.

**Dry Run (Recommended First):**
```bash
# Using the script directly
python ai_dynamic_deduplicate.py --dry-run

# Using the global command (if installed)
ai-deduplicate --dry-run
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

**Execute with Visualization:**
```bash
# WARNING: This modifies files!
ai-deduplicate --visualize
```

**Analyze Specific Directory:**
```bash
ai-deduplicate --directory /path/to/analyze --dry-run
```

## Configuration

### Standard Deduplicator Customization

Modify the `PREFERRED_STRUCTURE` dictionary directly within the `deduplicate_files.py` script to change the rule-based organization.

### AI Deduplicator Configuration (`.deduplication_config.json`)

Create a `.deduplication_config.json` file in the root of the repository where you run `ai-deduplicate` for persistent, repository-specific settings.

```json
{
  "lm_studio": {
    "url": "http://192.168.2.2:1234/v1/chat/completions", // Or your local URL
    "model": "gemma-3-27b-it", // Or your preferred model
    "temperature": 0.5,
    "max_tokens": 3000,
    "timeout": 300, // Timeout in seconds
    "system_prompt": "You are an expert file organization assistant specialized in financial documents."
  },
  "openai": {
    "model": "gpt-4", // Or your preferred model
    "temperature": 0.3,
    "max_tokens": 2000,
    "timeout": 60, // Timeout in seconds
    "system_prompt": "You are an expert file organization assistant specialized in financial documents."
  }
  // Note: The 'preferred_structure' key mentioned in older READMEs is not used by the AI script;
  // the AI generates the structure dynamically. Hardcoded structure is only used by the standard script.
}
```

This allows:
- Defining specific AI models, endpoints, and parameters per project.
- Setting custom system prompts to tailor AI behavior.

**Command-Line Overrides:**
You can override config file settings using command-line arguments:

```bash
# Override temperature and system prompt
ai-deduplicate --use-lm-studio --temperature 0.2 --system-prompt "Organize code files."

# Specify a custom config file location
ai-deduplicate --config ./configs/project_config.json
```

## Output Files

- **Standard:**
    - `deduplication_report.json`: Report of duplicates and actions.
    - `deduplication.log`: Process log.
- **AI-Driven:**
    - `ai_deduplication_report.json`: Report including the generated strategy.
    - `ai_deduplication.log`: Process log including AI interaction details.
    - `file_extensions.png` (optional, with `--visualize`): Visualization of file types.
    - `target_directories.png` (optional, with `--visualize`): Visualization of AI-generated organization.

## How the AI Tool is Different

Unlike traditional tools with static rules, the AI-driven approach:
- **Adapts:** Generates a unique organization strategy based on *your current files* each time.
- **Understands:** Analyzes content and metadata, not just names or extensions.
- **Learns:** Identifies and extends existing organizational patterns.
- **Optimizes:** Aims to create the most logical structure, not just remove duplicates.

## Example Use Cases for AI Tool

- **Research Data:** Organize by project, experiment type, date.
- **Photo Libraries:** Group by event, location, recognized people (future potential).
- **Financial Documents:** Intelligently categorize receipts, statements, tax forms.
- **Code Repositories:** Structure by language, framework, module.
- **General Downloads Folder:** Bring order to chaos based on detected file types and content. 