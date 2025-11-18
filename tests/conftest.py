"""Pytest configuration and fixtures for AI Deduplicator tests."""

import pytest
import sys
from pathlib import Path

# Add the parent directory to the path so tests can import the package
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
