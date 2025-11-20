"""Pytest configuration and fixtures for AI Deduplicator tests."""

import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add the parent directory to the path so tests can import the package
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Fixtures for testing

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample test files in temporary directory."""
    files = {}

    # Create a simple text file
    file1 = os.path.join(temp_dir, 'file1.txt')
    with open(file1, 'w') as f:
        f.write('test content 1')
    files['file1'] = file1

    # Create a duplicate file with same content
    file2 = os.path.join(temp_dir, 'file2.txt')
    with open(file2, 'w') as f:
        f.write('test content 1')
    files['file2'] = file2

    # Create a unique file
    file3 = os.path.join(temp_dir, 'file3.txt')
    with open(file3, 'w') as f:
        f.write('unique content')
    files['file3'] = file3

    return files


@pytest.fixture
def archive_dir(temp_dir):
    """Create an archive directory for testing."""
    archive = os.path.join(temp_dir, '.dedup-deleted')
    os.makedirs(archive, exist_ok=True)
    return archive


@pytest.fixture
def transaction_log_path(temp_dir):
    """Provide a path for transaction log testing."""
    return os.path.join(temp_dir, '.dedup_transaction.json')
