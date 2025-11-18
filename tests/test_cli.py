"""Smoke tests for CLI entry points."""

import subprocess
import sys


def test_ai_deduplicate_help():
    """Test that ai-deduplicate --help runs without errors."""
    result = subprocess.run(
        [sys.executable, '-m', 'ai_deduplicator.ai_dynamic_deduplicate', '--help'],
        capture_output=True,
        text=True
    )

    # Verify command ran successfully
    assert result.returncode == 0
    assert 'usage:' in result.stdout.lower() or 'AI-Driven File Organization' in result.stdout


def test_deduplicate_help():
    """Test that deduplicate --help runs without errors."""
    result = subprocess.run(
        [sys.executable, '-m', 'ai_deduplicator.deduplicate_files', '--help'],
        capture_output=True,
        text=True
    )

    # Verify command ran successfully
    assert result.returncode == 0
    assert 'usage:' in result.stdout.lower() or 'Deduplicate files' in result.stdout


def test_imports_work():
    """Test that main modules can be imported without errors."""
    # This will fail if there are import-time errors
    from ai_deduplicator import ai_dynamic_deduplicate
    from ai_deduplicator import deduplicate_files
    from ai_deduplicator import dedup_utils

    assert ai_dynamic_deduplicate is not None
    assert deduplicate_files is not None
    assert dedup_utils is not None
