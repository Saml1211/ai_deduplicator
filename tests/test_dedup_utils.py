"""Basic smoke tests for dedup_utils module."""

import os
import tempfile
import pytest
from ai_deduplicator import dedup_utils


def test_imports():
    """Test that the module can be imported."""
    assert dedup_utils is not None
    assert hasattr(dedup_utils, 'calculate_file_hash')
    assert hasattr(dedup_utils, 'get_files_recursively')
    assert hasattr(dedup_utils, 'scan_directory')
    assert hasattr(dedup_utils, 'execute_operations')
    assert hasattr(dedup_utils, 'generate_report')
    assert hasattr(dedup_utils, 'save_report')


def test_calculate_file_hash():
    """Test file hashing with a known file."""
    # Create a temporary file with known content
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("test content")
        temp_path = f.name

    try:
        # Calculate hash
        file_hash = dedup_utils.calculate_file_hash(temp_path)

        # Verify hash is returned and is a string
        assert file_hash is not None
        assert isinstance(file_hash, str)
        assert len(file_hash) == 64  # SHA-256 produces 64 hex characters

        # Verify same content produces same hash
        hash2 = dedup_utils.calculate_file_hash(temp_path)
        assert file_hash == hash2
    finally:
        # Clean up
        os.unlink(temp_path)


def test_get_files_recursively():
    """Test recursive file scanning with a fixture directory."""
    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some test files
        os.makedirs(os.path.join(tmpdir, 'subdir'))

        file1 = os.path.join(tmpdir, 'file1.txt')
        file2 = os.path.join(tmpdir, 'subdir', 'file2.txt')

        with open(file1, 'w') as f:
            f.write("content1")
        with open(file2, 'w') as f:
            f.write("content2")

        # Get all files
        files = list(dedup_utils.get_files_recursively(tmpdir))

        # Verify we found both files
        assert len(files) == 2
        assert any('file1.txt' in str(f) for f in files)
        assert any('file2.txt' in str(f) for f in files)


def test_scan_directory_basic():
    """Test basic directory scanning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two identical files
        file1 = os.path.join(tmpdir, 'file1.txt')
        file2 = os.path.join(tmpdir, 'file2.txt')

        with open(file1, 'w') as f:
            f.write("duplicate content")
        with open(file2, 'w') as f:
            f.write("duplicate content")

        # Scan directory
        duplicates, analyses = dedup_utils.scan_directory(tmpdir, analyze_content=False)

        # Verify duplicates were found
        assert len(duplicates) == 1  # One hash with duplicates
        for file_hash, files in duplicates.items():
            assert len(files) == 2  # Two files with same hash


def test_execute_operations_dry_run():
    """Test that dry run doesn't actually execute operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        source = os.path.join(tmpdir, 'source.txt')
        dest = os.path.join(tmpdir, 'dest.txt')

        with open(source, 'w') as f:
            f.write("test")

        # Define an operation
        operations = [{
            'action': 'move',
            'file': source,
            'destination': dest,
            'reason': 'test'
        }]

        # Execute in dry run mode
        stats = dedup_utils.execute_operations(operations, dry_run=True)

        # Verify stats were recorded
        assert 'moved' in stats
        assert stats['moved'] == 1

        # Verify file was NOT actually moved
        assert os.path.exists(source)
        assert not os.path.exists(dest)


def test_generate_report():
    """Test report generation."""
    duplicates = {
        'hash1': ['/path/to/file1.txt', '/path/to/file2.txt']
    }
    operations = [{
        'action': 'remove',
        'file': '/path/to/file2.txt',
        'reason': 'duplicate'
    }]
    stats = {'moved': 0, 'removed': 1, 'errors': 0}

    # Generate report
    report = dedup_utils.generate_report(duplicates, operations, stats, strategy=None)

    # Verify report structure
    assert 'timestamp' in report
    assert 'statistics' in report
    assert 'duplicates' in report
    assert 'operations' in report
    assert report['statistics']['operations'] == stats
