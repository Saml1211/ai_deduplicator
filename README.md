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

- Python 3.7+
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

This project is packaged using standard Python tools (`setuptools` and `pyproject.toml`).

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd ai-deduplicator
    ```
2.  **Install the package:**
    *   **Basic installation (core functionality):**
        ```bash
        pip install .
        ```
    *   **With AI features (OpenAI):**
        ```bash
        pip install .[ai]
        ```
    *   **With Visualization features:**
        ```bash
        pip install .[viz]
        ```
    *   **Full installation (all optional features):**
        ```bash
        pip install .[full]
        ```

*(Using a virtual environment is highly recommended)*

This will install the necessary dependencies and make the `ai-deduplicate` and `deduplicate` commands available in your environment.

### Uninstallation

```bash
pip uninstall ai-deduplicator
```

## Usage

Once installed, you can use the commands directly:

### AI-Driven Organizer (Recommended)

Generates organization strategy dynamically based on the files in the target directory.

**Safe Workflow (Recommended):**

1. **Dry Run (No Changes - Always Start Here):**
```bash
# Analyze current directory without making any changes
ai-deduplicate --dry-run

# Analyze a specific directory
ai-deduplicate --directory /path/to/analyze --dry-run

# Review the generated plan and logs
cat ai_deduplication_report.json
cat ai_deduplication.log
```

2. **Execute with Confirmation Prompt:**
```bash
# This will ask for confirmation before executing
ai-deduplicate --directory /path/to/target

# Automated execution with explicit --yes flag
ai-deduplicate --directory /path/to/target --yes
```

3. **Undo/Rollback if Needed:**
```bash
# Rollback the last operation (restores moved files and archived duplicates)
ai-deduplicate --undo --dry-run  # Preview rollback first

# Execute the rollback
ai-deduplicate --undo
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
ai-deduplicate --directory /path/to/target --visualize
```

**Advanced Usage with Custom Settings:**
```bash
# Use multiple workers for faster hashing on SSD storage
ai-deduplicate --directory /path/to/target --workers 8 --dry-run

# Skip specific patterns and extensions
ai-deduplicate --skip-patterns ".custom_dir,temp_files" --skip-extensions ".tmp,.bak" --dry-run

# Force interactive prompt even with automated scripts
ai-deduplicate --yes --interactive --directory /path/to/target
```

### Standard Deduplicator (Rule-Based)

Operates based on the hardcoded `PREFERRED_STRUCTURE` in `deduplicate_files.py`.

**Dry Run:**
```bash
# deduplicate --dry-run
deduplicate --dry-run # Use the installed command
```

**Execute:**
```bash
# WARNING: This modifies files!
# deduplicate
deduplicate # Use the installed command
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

## Safety & Rollback Features

This tool provides multiple layers of safety to protect your files during deduplication and reorganization:

### Archive System (Safe Deletion)

Instead of permanently deleting duplicate files, the tool **archives them to a hidden directory** (`.dedup-deleted/`) that preserves the original directory structure:

- **Original Path:** `/path/to/Downloads/file_copy.txt`
- **Archived Path:** `.dedup-deleted/path/to/Downloads/file_copy_20250118_143052_123.txt`

Timestamps are added to prevent filename collisions. You can manually inspect and restore files from this archive at any time.

**Recovering Files from Archive:**
```bash
# List all archived files (within the directory where you ran the tool)
ls -la .dedup-deleted/

# Manually restore a specific file
mv ".dedup-deleted/path/to/Downloads/file_copy_20250118_143052_123.txt" /path/to/Downloads/file_copy.txt

# Or use the --undo flag to automatically restore files (see below)
```

### Transaction Log & Rollback

Every operation is recorded in a **transaction log** (`.dedup_transaction.json`) before execution, enabling full rollback capability:

- **move operations:** Files are moved to new locations according to the organization strategy
- **remove operations:** Files are archived to `.dedup-deleted/` with metadata recorded
- **Rollback capability:** All operations can be reversed using the `--undo` flag

**Transaction Log Contents:**
```json
{
  "timestamp": "2025-01-18T14:30:52.123456",
  "operations": [
    {"action": "move", "file": "/path/to/file.txt", "destination": "/path/to/organized/file.txt"},
    {"action": "remove", "file": "/path/to/duplicate.txt", "reason": "duplicate"}
  ],
  "completed": true,
  "completed_at": "2025-01-18T14:30:55.987654"
}
```

**Undo/Rollback Operations:**
```bash
# Preview what will be rolled back (DRY RUN)
ai-deduplicate --undo --dry-run

# Execute the rollback
ai-deduplicate --undo

# Rollback from a different transaction log
ai-deduplicate --undo --transaction-log /path/to/custom_transaction.json
```

### Rollback Limitations & What Can Be Reversed

**What CAN be rolled back:**
- Files moved to new directories (will be moved back to original locations)
- Files archived as duplicates (will be restored from `.dedup-deleted/`)
- All changes from the most recent operation

**What CANNOT be rolled back:**
- Operations executed with `--force-continue` flag (no transaction log created)
- Archived files manually deleted from `.dedup-deleted/` directory
- Operations from previous executions if the transaction log was deleted
- Partial operations if the tool crashed before completing all operations
- Changes made to files after they were moved or archived

### Transaction Log Safety Warnings

**Automatic Transaction Log Creation:**
```bash
ai-deduplicate --directory /path/to/target
# Creates: .dedup_transaction.json (automatically)
# Allows: Full rollback capability
```

**Bypass Transaction Log (DANGEROUS):**
```bash
ai-deduplicate --directory /path/to/target --force-continue
# WARNING: No transaction log created
# WARNING: Rollback will be impossible
# WARNING: Only use if you fully understand the risks
```

### Best Practices for Safe Deduplication

1. **Always Start with Dry-Run:**
   ```bash
   ai-deduplicate --directory /path/to/target --dry-run
   cat ai_deduplication_report.json  # Review the plan
   ```

2. **Review Generated Plan:**
   - Check `ai_deduplication_report.json` for unexpected changes
   - Verify that files are organized logically
   - Look for any files that might be marked as duplicates incorrectly

3. **Execute with Confirmation:**
   ```bash
   ai-deduplicate --directory /path/to/target
   # You will be prompted to confirm before executing
   ```

4. **Backup Critical Data:**
   ```bash
   # Before running deduplication on important directories
   cp -r /path/to/target /path/to/target.backup
   ```

5. **Monitor the Operation:**
   - Keep the terminal open while operations are running
   - Watch for any error messages in the log
   - Check `ai_deduplication.log` for warnings

6. **Verify Results:**
   ```bash
   # After execution, verify the new structure
   tree /path/to/target

   # Check for any errors in the log
   grep -i "error\|warning" ai_deduplication.log
   ```

7. **Keep Transaction Logs:**
   ```bash
   # Store transaction logs safely if you might need to rollback later
   cp .dedup_transaction.json .dedup_transaction_backup.json
   ```

## Command-Line Flags

### Operational Flags

- **`--dry-run`** - Preview all changes without modifying files. Always run this first to review the plan.
  ```bash
  ai-deduplicate --directory /path/to/target --dry-run
  ```

- **`--undo`** - Rollback the last operation by reversing moves and restoring archived files.
  ```bash
  ai-deduplicate --undo --dry-run    # Preview rollback
  ai-deduplicate --undo              # Execute rollback
  ```

### Interactive & Confirmation Flags

- **`--yes`, `-y`** - Skip confirmation prompts and execute operations automatically. Useful for scripting and automation.
  ```bash
  ai-deduplicate --directory /path/to/target --yes
  ```

- **`--interactive`** - Force confirmation prompt even when `--yes` is set. Useful when you want to override automated behavior for critical operations.
  ```bash
  ai-deduplicate --directory /path/to/target --yes --interactive
  ```

### Performance Flags

- **`--workers N`** - Number of parallel workers for file hashing. Higher values improve performance on fast storage. Defaults to `min(cpu_count, 8)`.
  ```bash
  ai-deduplicate --directory /path/to/target --workers 8 --dry-run
  # Recommended: 2-4 for HDDs, 4-8 for SSDs (values > 8 not recommended due to memory overhead)
  ```

### Filter Flags

- **`--skip-patterns "pattern1,pattern2,pattern3"`** - Comma-separated list of directory/file patterns to skip.
  ```bash
  ai-deduplicate --skip-patterns ".custom_dir,temp_files,cache" --dry-run
  # Default patterns skipped: .git, node_modules, __pycache__, venv, .idea, .vscode, .DS_Store
  ```

- **`--skip-extensions ".ext1,.ext2,.ext3"`** - Comma-separated list of file extensions to skip.
  ```bash
  ai-deduplicate --skip-extensions ".tmp,.bak,.log" --dry-run
  # Default extensions skipped: .pyc, .pyo, .pyd, .so, .dll, .exe
  ```

- **`--no-default-skips`** - Disable default skip patterns and only use custom patterns. Use with caution!
  ```bash
  ai-deduplicate --skip-patterns ".git" --no-default-skips --dry-run
  # This will include node_modules, __pycache__, etc. in processing
  ```

### Safety Flags

- **`--force-continue`** - Bypass transaction log safety checks and execute without creating a transaction log. **NOT RECOMMENDED.**

  ```bash
  ai-deduplicate --directory /path/to/target --force-continue
  ```

  **WARNINGS:**
  - Rollback capability is **DISABLED** - you cannot use `--undo` after this
  - If something goes wrong during execution, you will NOT be able to recover
  - Only use if you fully understand the risks and have complete backups
  - Useful only for low-importance files where rollback is unnecessary

### AI Configuration Flags

- **`--use-lm-studio`** - Use local LM Studio server instead of OpenAI API.
  ```bash
  ai-deduplicate --use-lm-studio --dry-run
  ```

- **`--lm-studio-url URL`** - Custom LM Studio server URL (default: http://127.0.0.1:1234/v1/chat/completions).
  ```bash
  ai-deduplicate --use-lm-studio --lm-studio-url http://localhost:8080/v1/chat/completions --dry-run
  ```

- **`--config FILE`** - Path to custom configuration file (`.deduplication_config.json`).
  ```bash
  ai-deduplicate --config ./custom_config.json --dry-run
  ```

- **`--temperature FLOAT`** - AI generation temperature (0.0-1.0). Lower = more deterministic, Higher = more creative.
  ```bash
  ai-deduplicate --temperature 0.3 --dry-run  # More conservative organization
  ```

- **`--system-prompt "PROMPT"`** - Custom system prompt for AI analysis.
  ```bash
  ai-deduplicate --system-prompt "Organize files for archival, not daily use" --dry-run
  ```

- **`--no-ai`** - Skip AI processing and use heuristic-based organization only.
  ```bash
  ai-deduplicate --no-ai --dry-run
  ```

- **`--timeout SECONDS`** - Timeout for AI requests (default: 60s for OpenAI, 300s for LM Studio).
  ```bash
  ai-deduplicate --timeout 120 --dry-run
  ```

### Other Flags

- **`--directory PATH`, `-d PATH`** - Target directory to analyze (default: current directory).
  ```bash
  ai-deduplicate --directory /path/to/target --dry-run
  ```

- **`--visualize`** - Generate visualization charts of file distribution and organization strategy.
  ```bash
  ai-deduplicate --directory /path/to/target --visualize
  # Creates: file_extensions.png, target_directories.png
  ```

- **`--verbose`, `-v`** - Enable verbose logging output for debugging.
  ```bash
  ai-deduplicate --directory /path/to/target --verbose --dry-run
  ```

## Output Files

- **AI-Driven:** `ai_deduplication_report.json`, `ai_deduplication.log`, (optional) `file_extensions.png`, `target_directories.png`.
- **Standard:** `deduplication_report.json`, `deduplication.log`.

## Security Considerations

The AI Deduplicator creates transaction logs and reports that contain file system paths and directory structure information. This is important for recovery and auditing purposes, but these files require appropriate security protection.

**Important Security Practices:**
- Transaction logs (`.dedup_transaction.json`) contain full file paths from your system
- Set restrictive permissions on transaction logs: `chmod 600 .dedup_transaction.json`
- Set restrictive permissions on archive directories: `chmod 700 .dedup-deleted`
- Add to `.gitignore`: `.dedup_transaction.json*`, `.dedup-deleted/`, `.deduplication_config.json`
- Securely delete old transaction logs when no longer needed
- Never commit transaction logs or detailed reports to version control

For comprehensive security guidance, including handling sensitive data, multi-user systems, and enterprise deployments, see **[SECURITY.md](SECURITY.md)**.

## Example Use Cases for AI Tool

- **Downloads Folder Cleanup:** Intelligently sort mixed downloaded files into relevant categories (documents, images, installers, archives).
- **Project Directory Structuring:** Analyze a project folder (code, notes, assets) and suggest a standardized structure.
- **Research Data Consolidation:** Organize papers, datasets, and notes by topic, project, or date.
- **Photo Library Management:** Group photos by inferred event, date, or potentially recognized content (future enhancement).
- **Financial Document Archiving:** Categorize scans of receipts, statements, and tax documents.