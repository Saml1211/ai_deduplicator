# AI Deduplicator Technical Context

## Core Technologies

### Programming Language
- **Python 3.6+**: Primary development language
  - Chosen for cross-platform compatibility, rich ecosystem, and accessibility

### Packaging and Distribution
- **setuptools** and **pyproject.toml**: Standard Python packaging
- Package installable via pip with optional extras

### Core Dependencies
- **pathlib**: File system path manipulation (standard library)
- **requests**: HTTP client for API interactions
- **hashlib**: File content hashing (standard library)
- **argparse**: Command-line argument parsing (standard library)
- **logging**: Structured logging (standard library)
- **json**: JSON parsing and generation (standard library)

### Optional Dependencies
- **openai**: OpenAI API client for GPT model access
- **pandas**: Data manipulation for analysis
- **matplotlib**: Visualization of file distributions

### AI Integration
- **OpenAI API**: For cloud-based AI analysis
- **LM Studio**: For local AI model deployment
- **API-compatible local LLMs**: Alternative local AI options

## Development Environment

### Requirements
- Python 3.6+ environment
- Virtual environment recommended
- Optional: LM Studio for local AI testing

### Installation Methods
- Direct from repository (development)
- Via pip (user installation)
- Global installation for command-line access

## Technical Constraints

### Performance Considerations
- File hashing is CPU and I/O intensive for large files
- AI API calls introduce latency and potential timeouts
- Large directories require significant memory for analysis

### Security Considerations
- File operations require careful validation
- API keys must be stored securely
- Dry-run mode should be encouraged as default

### Platform Compatibility
- Must work on Windows, macOS, and Linux
- Path handling must be cross-platform
- File operation atomicity varies by OS

### API Limitations
- OpenAI API has rate limits and token constraints
- Local AI models have different capabilities and limitations
- Fallback mechanisms required for when AI is unavailable

## Technical Debt

### Current Limitations
- Visualization could be enhanced with more interactive options
- Error handling in some edge cases could be improved
- Unit test coverage needs expansion

### Future Technical Improvements
- More AI backend options
- More sophisticated content analysis
- Better parallelization for performance with large file sets
- Interactive web UI for visualization and control

## Integration Points

### External Services
- OpenAI API
- LM Studio local API
- Potential for other LLM APIs

### File System
- Direct file system access for scanning and operations
- Support for various file systems and their limitations 