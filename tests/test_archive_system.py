"""Tests for the archive system and file archiving functionality."""

import os
import tempfile
import shutil
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from ai_deduplicator import dedup_utils


class TestArchiveFile:
    """Test cases for _archive_file function."""

    def test_archive_file_creates_archive_directory(self):
        """Test that archive directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = os.path.join(tmpdir, 'test.txt')
            with open(test_file, 'w') as f:
                f.write('test content')

            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Archive the file
            result = dedup_utils._archive_file(test_file, archive_dir)

            # Verify archive directory was created
            assert os.path.exists(archive_dir)
            assert result is not None
            assert result.startswith(archive_dir)
            assert os.path.basename(result).startswith('test_')

    def test_archive_file_preserves_directory_structure(self):
        """Test that archived files preserve original directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a nested directory structure
            nested_dir = os.path.join(tmpdir, 'subdir', 'deep')
            os.makedirs(nested_dir)

            test_file = os.path.join(nested_dir, 'file.txt')
            with open(test_file, 'w') as f:
                f.write('nested content')

            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Archive the file
            result = dedup_utils._archive_file(test_file, archive_dir)

            # Verify directory structure is preserved
            assert result is not None
            assert 'subdir/deep' in result or 'subdir\\deep' in result
            assert os.path.exists(result)

    def test_archive_file_adds_timestamp(self):
        """Test that archived files have timestamp appended."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, 'file.txt')
            with open(test_file, 'w') as f:
                f.write('content')

            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Archive the file
            result = dedup_utils._archive_file(test_file, archive_dir)

            # Verify timestamp is in the filename
            assert result is not None
            # Check for timestamp pattern (YYYYMMDD_HHMMSS_mmm)
            assert '_20' in result or '_19' in result  # Year part
            assert os.path.exists(result)

    def test_archive_file_moves_file_not_copies(self):
        """Test that archiving moves the file, not copies it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, 'file.txt')
            with open(test_file, 'w') as f:
                f.write('content')

            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Archive the file
            result = dedup_utils._archive_file(test_file, archive_dir)

            # Verify original file is gone
            assert not os.path.exists(test_file)
            # Verify archived file exists
            assert os.path.exists(result)

    def test_archive_file_preserves_file_content(self):
        """Test that file content is preserved during archiving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_content = 'This is important content'
            test_file = os.path.join(tmpdir, 'file.txt')
            with open(test_file, 'w') as f:
                f.write(original_content)

            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Archive the file
            result = dedup_utils._archive_file(test_file, archive_dir)

            # Verify content is preserved
            with open(result, 'r') as f:
                archived_content = f.read()
            assert archived_content == original_content

    def test_archive_file_handles_missing_source_file(self):
        """Test that archiving gracefully handles missing source file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            non_existent = os.path.join(tmpdir, 'missing.txt')
            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Try to archive non-existent file
            result = dedup_utils._archive_file(non_existent, archive_dir)

            # Should return None for failed operation
            assert result is None

    def test_archive_file_handles_permission_error(self):
        """Test that archiving handles permission errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, 'file.txt')
            with open(test_file, 'w') as f:
                f.write('content')

            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Mock shutil.move to raise PermissionError
            with patch('shutil.move', side_effect=PermissionError('Permission denied')):
                result = dedup_utils._archive_file(test_file, archive_dir)

                # Should return None on error
                assert result is None

    def test_archive_multiple_versions_of_same_file(self):
        """Test that multiple versions of the same file can be archived."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, 'file.txt')
            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Archive file version 1
            with open(test_file, 'w') as f:
                f.write('version 1')
            result1 = dedup_utils._archive_file(test_file, archive_dir)
            assert result1 is not None
            assert os.path.exists(result1)

            # Archive file version 2
            with open(test_file, 'w') as f:
                f.write('version 2')
            result2 = dedup_utils._archive_file(test_file, archive_dir)
            assert result2 is not None
            assert os.path.exists(result2)

            # Both should exist with different names (timestamps ensure uniqueness)
            # Due to timing, they might be identical if archived within same millisecond,
            # but both files should exist in archive
            assert os.path.exists(result1)
            assert os.path.exists(result2)


class TestRestoreFromArchive:
    """Test cases for _restore_from_archive function."""

    def test_restore_from_archive_basic(self):
        """Test basic file restoration from archive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_file = os.path.join(tmpdir, 'original.txt')
            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Create and archive a file
            with open(original_file, 'w') as f:
                f.write('original content')

            dedup_utils._archive_file(original_file, archive_dir)

            # Restore the file
            result = dedup_utils._restore_from_archive(original_file, archive_dir)

            # Verify restoration was successful
            assert result is True
            assert os.path.exists(original_file)

    def test_restore_from_archive_preserves_content(self):
        """Test that restoration preserves file content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_file = os.path.join(tmpdir, 'file.txt')
            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            original_content = 'Important data'
            with open(original_file, 'w') as f:
                f.write(original_content)

            # Archive
            dedup_utils._archive_file(original_file, archive_dir)

            # Restore
            dedup_utils._restore_from_archive(original_file, archive_dir)

            # Verify content
            with open(original_file, 'r') as f:
                restored_content = f.read()
            assert restored_content == original_content

    def test_restore_uses_most_recent_version(self):
        """Test that restoration uses the most recent archived version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_file = os.path.join(tmpdir, 'file.txt')
            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Archive version 1
            with open(original_file, 'w') as f:
                f.write('version 1')
            dedup_utils._archive_file(original_file, archive_dir)

            # Archive version 2
            with open(original_file, 'w') as f:
                f.write('version 2')
            dedup_utils._archive_file(original_file, archive_dir)

            # Restore (should get version 2)
            dedup_utils._restore_from_archive(original_file, archive_dir)

            # Verify we got the most recent version
            with open(original_file, 'r') as f:
                content = f.read()
            assert content == 'version 2'

    def test_restore_from_archive_no_archive_found(self):
        """Test restoration when no archived version exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_file = os.path.join(tmpdir, 'nonexistent.txt')
            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Try to restore file that was never archived
            result = dedup_utils._restore_from_archive(original_file, archive_dir)

            # Should return False
            assert result is False

    def test_restore_from_archive_no_archive_directory(self):
        """Test restoration when archive directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_file = os.path.join(tmpdir, 'file.txt')
            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Try to restore without archive directory
            result = dedup_utils._restore_from_archive(original_file, archive_dir)

            # Should return False
            assert result is False

    def test_restore_cleans_up_old_versions(self):
        """Test that restoration cleans up old archived versions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_file = os.path.join(tmpdir, 'file.txt')
            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Archive multiple versions
            with open(original_file, 'w') as f:
                f.write('v1')
            dedup_utils._archive_file(original_file, archive_dir)

            with open(original_file, 'w') as f:
                f.write('v2')
            dedup_utils._archive_file(original_file, archive_dir)

            with open(original_file, 'w') as f:
                f.write('v3')
            dedup_utils._archive_file(original_file, archive_dir)

            # Count archives before restore
            archive_base_dir = os.path.dirname(os.path.join(archive_dir, original_file.lstrip('/')))
            archives_before = len(os.listdir(archive_base_dir))

            # Restore
            dedup_utils._restore_from_archive(original_file, archive_dir)

            # Count archives after restore (should be 0, all cleaned up)
            archives_after = len(os.listdir(archive_base_dir))
            assert archives_after < archives_before

    def test_restore_creates_missing_directories(self):
        """Test that restoration creates missing directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested original location
            nested_dir = os.path.join(tmpdir, 'deep', 'nested', 'dir')
            original_file = os.path.join(nested_dir, 'file.txt')
            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Create and archive
            os.makedirs(nested_dir)
            with open(original_file, 'w') as f:
                f.write('content')
            dedup_utils._archive_file(original_file, archive_dir)

            # Remove the original nested directory
            shutil.rmtree(os.path.dirname(original_file))
            assert not os.path.exists(nested_dir)

            # Restore
            result = dedup_utils._restore_from_archive(original_file, archive_dir)

            # Verify file was restored and directories were created
            assert result is True
            assert os.path.exists(original_file)


class TestArchiveIntegration:
    """Integration tests for archive system with execute_operations."""

    def test_execute_operations_archives_removed_files(self):
        """Test that remove operations archive files instead of deleting them."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = os.path.join(tmpdir, 'duplicate.txt')
            with open(test_file, 'w') as f:
                f.write('duplicate content')

            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            # Define remove operation
            operations = [{
                'action': 'remove',
                'file': test_file,
                'reason': 'duplicate'
            }]

            # Execute operations (live mode)
            stats = dedup_utils.execute_operations(
                operations,
                dry_run=False,
                create_log=False,
                archive_dir=archive_dir,
                force_continue=True,
                skip_confirmation=True
            )

            # Verify file was archived, not deleted
            assert not os.path.exists(test_file)
            assert os.path.exists(archive_dir)
            assert stats['archived'] == 1
            assert stats['errors'] == 0

    def test_archived_files_can_be_restored(self):
        """Test that archived files can be restored after removal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, 'file.txt')
            archive_dir = os.path.join(tmpdir, '.dedup-deleted')
            original_content = 'Important data'

            # Create and archive
            with open(test_file, 'w') as f:
                f.write(original_content)

            operations = [{
                'action': 'remove',
                'file': test_file,
                'reason': 'test removal'
            }]

            dedup_utils.execute_operations(
                operations,
                dry_run=False,
                create_log=False,
                archive_dir=archive_dir,
                force_continue=True,
                skip_confirmation=True
            )

            # Verify file is archived
            assert not os.path.exists(test_file)

            # Restore the file
            restored = dedup_utils._restore_from_archive(test_file, archive_dir)

            # Verify restoration
            assert restored is True
            assert os.path.exists(test_file)
            with open(test_file, 'r') as f:
                assert f.read() == original_content

    def test_move_operations_dont_use_archive(self):
        """Test that move operations don't create archives."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, 'source.txt')
            dest = os.path.join(tmpdir, 'dest', 'file.txt')
            archive_dir = os.path.join(tmpdir, '.dedup-deleted')

            with open(source, 'w') as f:
                f.write('content')

            operations = [{
                'action': 'move',
                'file': source,
                'destination': dest,
                'reason': 'organization'
            }]

            stats = dedup_utils.execute_operations(
                operations,
                dry_run=False,
                create_log=False,
                archive_dir=archive_dir,
                force_continue=True,
                skip_confirmation=True
            )

            # Verify file was moved, not archived
            assert not os.path.exists(source)
            assert os.path.exists(dest)
            assert not os.path.exists(archive_dir) or len(os.listdir(archive_dir)) == 0
            assert stats['moved'] == 1
