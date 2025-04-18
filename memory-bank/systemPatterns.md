# AI Deduplicator System Patterns

## System Architecture
The AI Deduplicator follows a modular architecture pattern with clear separation of concerns:

```
┌────────────────┐     ┌─────────────────────┐     ┌────────────────────┐
│ CLI Interface  │────▶│ Analysis & Strategy │────▶│ File Operations    │
└────────────────┘     └─────────────────────┘     └────────────────────┘
        │                        │                          │
        │                        ▼                          │
        │              ┌─────────────────────┐             │
        └─────────────▶│ Reporting & Logging │◀────────────┘
                       └─────────────────────┘
```

### Key Components

1. **CLI Interface** (`main()` function)
   - Parses command-line arguments
   - Sets up configuration and logging
   - Orchestrates the overall process flow

2. **Analysis & Strategy**
   - `analyze_file_content()`: Extracts metadata and content features
   - `generate_ai_organization_strategy()`: Determines organization structure
   - Various AI integrations (OpenAI, LM Studio, heuristic fallback)

3. **File Operations**
   - `apply_organization_strategy()`: Maps files to destinations
   - `execute_operations()`: Performs the actual file movements
   - Hash-based deduplication logic

4. **Reporting & Logging**
   - Detailed logging of all operations
   - JSON report generation
   - Optional visualization

## Design Patterns

1. **Factory Pattern**
   - Different strategy generation methods (AI vs. heuristic)
   - Dynamic selection based on availability and configuration

2. **Strategy Pattern**
   - Pluggable organization strategies
   - Swappable AI backends

3. **Command Pattern**
   - Operations are defined before execution
   - Supports dry-run mode without actual file changes

4. **Adapter Pattern**
   - Common interface for different AI services
   - Consistent strategy format regardless of source

## Data Flows

1. **File Analysis Flow**
   - Scan directory structure
   - Calculate file hashes
   - Extract file metadata and content features
   - Identify duplicates

2. **Strategy Generation Flow**
   - Prepare data for AI prompt
   - Call relevant AI service
   - Parse and validate returned strategy
   - Fall back to heuristics if needed

3. **Execution Flow**
   - Apply strategy to generate operations list
   - Validate operations for safety
   - Execute or simulate operations based on mode
   - Generate reports and visualizations

## Configuration Management
- Command-line arguments for immediate override
- Local `.deduplication_config.json` for persistent settings
- Environment variables for sensitive information (API keys)
- Sensible defaults for all options

## Error Handling
- Graceful degradation when AI services unavailable
- Exception handling for file operations
- Logging of all errors and warnings
- User-friendly error messages

## Extension Points
- New AI service integrations
- Additional file analysis techniques
- Enhanced visualization options
- Additional reporting formats 