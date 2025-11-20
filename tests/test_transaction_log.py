"""Tests for transaction log creation, error handling, and rollback functionality."""

import os
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from ai_deduplicator import dedup_utils


class TestTransactionLogError:
    """Test cases for TransactionLogError exception."""

    def test_transaction_log_error_is_exception(self):
        """Test that TransactionLogError is an Exception."""
        assert issubclass(dedup_utils.TransactionLogError, Exception)

    def test_transaction_log_error_can_be_raised(self):
        """Test that TransactionLogError can be raised and caught."""
        with pytest.raises(dedup_utils.TransactionLogError):
            raise dedup_utils.TransactionLogError("Test error message")

    def test_transaction_log_error_has_message(self):
        """Test that TransactionLogError can carry a message."""
        error_msg = "Custom error message"
        try:
            raise dedup_utils.TransactionLogError(error_msg)
        except dedup_utils.TransactionLogError as e:
            assert str(e) == error_msg


class TestCreateTransactionLog:
    """Test cases for create_transaction_log function."""

    def test_create_transaction_log_basic(self):
        """Test basic transaction log creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            operations = [
                {'action': 'move', 'file': 'file1.txt', 'destination': 'dir/file1.txt'},
                {'action': 'remove', 'file': 'duplicate.txt', 'reason': 'duplicate'}
            ]

            result = dedup_utils.create_transaction_log(operations, log_file)

            # Verify log was created
            assert result is True
            assert os.path.exists(log_file)

    def test_transaction_log_has_correct_format(self):
        """Test that transaction log has correct JSON structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            operations = [
                {'action': 'move', 'file': 'file.txt', 'destination': 'dest.txt'}
            ]

            dedup_utils.create_transaction_log(operations, log_file)

            # Read and verify structure
            with open(log_file, 'r') as f:
                transaction = json.load(f)

            assert 'timestamp' in transaction
            assert 'operations' in transaction
            assert 'completed' in transaction
            assert transaction['completed'] is False
            assert len(transaction['operations']) == 1

    def test_transaction_log_contains_all_operations(self):
        """Test that transaction log contains all provided operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            operations = [
                {'action': 'move', 'file': 'file1.txt', 'destination': 'dir1/file1.txt'},
                {'action': 'remove', 'file': 'dup1.txt', 'reason': 'duplicate'},
                {'action': 'move', 'file': 'file2.txt', 'destination': 'dir2/file2.txt'},
                {'action': 'remove', 'file': 'dup2.txt', 'reason': 'duplicate'}
            ]

            dedup_utils.create_transaction_log(operations, log_file)

            with open(log_file, 'r') as f:
                transaction = json.load(f)

            assert len(transaction['operations']) == 4
            assert transaction['operations'] == operations

    def test_transaction_log_timestamp_is_valid(self):
        """Test that transaction log has valid ISO timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            operations = []

            dedup_utils.create_transaction_log(operations, log_file)

            with open(log_file, 'r') as f:
                transaction = json.load(f)

            # Verify timestamp is valid ISO format
            try:
                timestamp = datetime.fromisoformat(transaction['timestamp'])
                assert timestamp is not None
            except ValueError:
                pytest.fail("Timestamp is not valid ISO format")

    def test_create_transaction_log_permission_error(self):
        """Test that create_transaction_log returns False on permission error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            operations = [{'action': 'move', 'file': 'file.txt', 'destination': 'dest.txt'}]

            # Mock open to raise PermissionError
            with patch('builtins.open', side_effect=PermissionError('Permission denied')):
                result = dedup_utils.create_transaction_log(operations, log_file)

            assert result is False

    def test_create_transaction_log_io_error(self):
        """Test that create_transaction_log handles IO errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a non-existent nested path
            log_file = os.path.join(tmpdir, 'nonexistent', 'dir', '.dedup_transaction.json')

            operations = [{'action': 'move', 'file': 'file.txt', 'destination': 'dest.txt'}]

            # Should return False instead of crashing
            result = dedup_utils.create_transaction_log(operations, log_file)

            assert result is False

    def test_create_transaction_log_empty_operations(self):
        """Test creating transaction log with empty operations list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            result = dedup_utils.create_transaction_log([], log_file)

            assert result is True
            assert os.path.exists(log_file)

            with open(log_file, 'r') as f:
                transaction = json.load(f)
            assert transaction['operations'] == []


class TestMarkTransactionComplete:
    """Test cases for mark_transaction_complete function."""

    def test_mark_transaction_complete_basic(self):
        """Test marking a transaction as completed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            # Create a transaction
            operations = [{'action': 'move', 'file': 'file.txt', 'destination': 'dest.txt'}]
            dedup_utils.create_transaction_log(operations, log_file)

            # Mark as complete
            result = dedup_utils.mark_transaction_complete(log_file)

            assert result is True

            # Verify the file was updated
            with open(log_file, 'r') as f:
                transaction = json.load(f)

            assert transaction['completed'] is True
            assert 'completed_at' in transaction

    def test_mark_transaction_complete_timestamp(self):
        """Test that mark_transaction_complete adds timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            operations = []
            dedup_utils.create_transaction_log(operations, log_file)
            dedup_utils.mark_transaction_complete(log_file)

            with open(log_file, 'r') as f:
                transaction = json.load(f)

            assert 'completed_at' in transaction
            try:
                datetime.fromisoformat(transaction['completed_at'])
            except ValueError:
                pytest.fail("completed_at is not valid ISO format")

    def test_mark_transaction_complete_missing_log(self):
        """Test that mark_transaction_complete handles missing log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'nonexistent.json')

            result = dedup_utils.mark_transaction_complete(log_file)

            assert result is False

    def test_mark_transaction_complete_invalid_json(self):
        """Test that mark_transaction_complete handles invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            # Create invalid JSON file
            with open(log_file, 'w') as f:
                f.write('{invalid json}')

            result = dedup_utils.mark_transaction_complete(log_file)

            assert result is False


class TestReadTransactionLog:
    """Test cases for read_transaction_log function."""

    def test_read_transaction_log_basic(self):
        """Test reading a transaction log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            operations = [{'action': 'move', 'file': 'file.txt', 'destination': 'dest.txt'}]
            dedup_utils.create_transaction_log(operations, log_file)

            # Read the log
            transaction = dedup_utils.read_transaction_log(log_file)

            assert transaction is not None
            assert 'operations' in transaction
            assert transaction['operations'] == operations

    def test_read_transaction_log_missing_file(self):
        """Test that read_transaction_log returns None for missing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'nonexistent.json')

            result = dedup_utils.read_transaction_log(log_file)

            assert result is None

    def test_read_transaction_log_invalid_json(self):
        """Test that read_transaction_log returns None for invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            with open(log_file, 'w') as f:
                f.write('{invalid}')

            result = dedup_utils.read_transaction_log(log_file)

            assert result is None


class TestTransactionLogErrorHandling:
    """Test error handling during execute_operations with transaction logs."""

    def test_execute_operations_raises_transaction_log_error_on_failure(self):
        """Test that execute_operations raises TransactionLogError when log creation fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            operations = [{'action': 'move', 'file': 'file.txt', 'destination': 'dest.txt'}]
            log_file = os.path.join(tmpdir, 'nonexistent_dir', '.dedup_transaction.json')

            # Should raise TransactionLogError when log creation fails
            with pytest.raises(dedup_utils.TransactionLogError):
                dedup_utils.execute_operations(
                    operations,
                    dry_run=False,
                    create_log=True,
                    log_file=log_file,
                    force_continue=False,
                    skip_confirmation=True
                )

    def test_execute_operations_with_log_creation_failure(self):
        """Test execute_operations with mocked log creation failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, 'source.txt')
            with open(source, 'w') as f:
                f.write('content')

            operations = [{
                'action': 'move',
                'file': source,
                'destination': os.path.join(tmpdir, 'dest.txt')
            }]

            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            # Mock create_transaction_log to return False
            with patch('ai_deduplicator.dedup_utils.create_transaction_log', return_value=False):
                with pytest.raises(dedup_utils.TransactionLogError) as exc_info:
                    dedup_utils.execute_operations(
                        operations,
                        dry_run=False,
                        create_log=True,
                        log_file=log_file,
                        force_continue=False,
                        skip_confirmation=True
                    )

                # Verify the error message is descriptive
                assert 'Failed to create transaction log' in str(exc_info.value)
                assert 'rollback capability' in str(exc_info.value)

    def test_execute_operations_skips_log_with_force_continue(self):
        """Test that force_continue bypasses log creation requirements."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, 'source.txt')
            dest = os.path.join(tmpdir, 'dest.txt')
            with open(source, 'w') as f:
                f.write('content')

            operations = [{
                'action': 'move',
                'file': source,
                'destination': dest
            }]

            log_file = os.path.join(tmpdir, 'nonexistent_dir', '.dedup_transaction.json')

            # Should NOT raise error with force_continue=True
            stats = dedup_utils.execute_operations(
                operations,
                dry_run=False,
                create_log=True,
                log_file=log_file,
                force_continue=True,
                skip_confirmation=True
            )

            # Operation should still execute
            assert stats['moved'] == 1
            assert not os.path.exists(source)
            assert os.path.exists(dest)

    def test_execute_operations_with_log_enabled_dry_run(self):
        """Test that dry-run mode doesn't require transaction log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, 'source.txt')
            with open(source, 'w') as f:
                f.write('content')

            operations = [{
                'action': 'move',
                'file': source,
                'destination': os.path.join(tmpdir, 'dest.txt')
            }]

            log_file = os.path.join(tmpdir, 'nonexistent_dir', '.dedup_transaction.json')

            # Dry-run should not raise error even if log creation would fail
            stats = dedup_utils.execute_operations(
                operations,
                dry_run=True,
                create_log=True,
                log_file=log_file,
                force_continue=False,
                skip_confirmation=True
            )

            assert stats['moved'] == 1

    def test_execute_operations_no_log_when_create_log_false(self):
        """Test that no log is created when create_log=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, 'source.txt')
            with open(source, 'w') as f:
                f.write('content')

            operations = [{
                'action': 'move',
                'file': source,
                'destination': os.path.join(tmpdir, 'dest.txt')
            }]

            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            # Should execute successfully without trying to create log
            stats = dedup_utils.execute_operations(
                operations,
                dry_run=False,
                create_log=False,
                log_file=log_file,
                force_continue=False,
                skip_confirmation=True
            )

            assert stats['moved'] == 1
            assert not os.path.exists(log_file)


class TestRollbackOperations:
    """Test cases for rollback functionality."""

    def test_rollback_operations_dry_run(self):
        """Test rollback in dry-run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            # Create a transaction log
            operations = [
                {'action': 'move', 'file': 'file.txt', 'destination': 'dest.txt'},
                {'action': 'remove', 'file': 'dup.txt', 'reason': 'duplicate'}
            ]
            dedup_utils.create_transaction_log(operations, log_file)
            dedup_utils.mark_transaction_complete(log_file)

            # Rollback in dry-run mode
            stats = dedup_utils.rollback_operations(
                log_file=log_file,
                dry_run=True,
                archive_dir=os.path.join(tmpdir, '.dedup-deleted')
            )

            # Verify log still exists in dry-run
            assert os.path.exists(log_file)

    def test_rollback_operations_missing_log(self):
        """Test rollback with missing log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'nonexistent.json')

            stats = dedup_utils.rollback_operations(
                log_file=log_file,
                dry_run=False,
                archive_dir=os.path.join(tmpdir, '.dedup-deleted')
            )

            # Should return empty stats
            assert stats['restored'] == 0
            assert stats['unmoved'] == 0

    def test_rollback_reverses_move_operations(self):
        """Test that rollback reverses move operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, 'source.txt')
            dest = os.path.join(tmpdir, 'dest', 'file.txt')

            # Create and move file
            with open(source, 'w') as f:
                f.write('content')

            os.makedirs(os.path.dirname(dest), exist_ok=True)
            os.rename(source, dest)

            # Create transaction log
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')
            operations = [{'action': 'move', 'file': source, 'destination': dest}]
            dedup_utils.create_transaction_log(operations, log_file)
            dedup_utils.mark_transaction_complete(log_file)

            # Verify current state
            assert not os.path.exists(source)
            assert os.path.exists(dest)

            # Rollback
            stats = dedup_utils.rollback_operations(
                log_file=log_file,
                dry_run=False,
                archive_dir=os.path.join(tmpdir, '.dedup-deleted')
            )

            # Verify rollback
            assert stats['unmoved'] == 1
            assert os.path.exists(source)
            assert not os.path.exists(dest)

    def test_rollback_restores_archived_files(self):
        """Test that rollback restores archived files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, 'file.txt')
            archive_dir = os.path.join(tmpdir, '.dedup-deleted')
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            # Create and archive file
            with open(test_file, 'w') as f:
                f.write('original content')

            operations = [{'action': 'remove', 'file': test_file, 'reason': 'duplicate'}]
            dedup_utils.create_transaction_log(operations, log_file)

            dedup_utils.execute_operations(
                operations,
                dry_run=False,
                create_log=False,
                archive_dir=archive_dir,
                force_continue=True,
                skip_confirmation=True
            )

            dedup_utils.mark_transaction_complete(log_file)

            # Verify file is archived
            assert not os.path.exists(test_file)

            # Rollback
            stats = dedup_utils.rollback_operations(
                log_file=log_file,
                dry_run=False,
                archive_dir=archive_dir
            )

            # Verify restoration
            assert stats['restored'] == 1
            assert os.path.exists(test_file)
            with open(test_file, 'r') as f:
                assert f.read() == 'original content'

    def test_rollback_processes_operations_in_reverse_order(self):
        """Test that rollback processes operations in reverse order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            # Create transaction with multiple operations
            operations = [
                {'action': 'move', 'file': 'file1.txt', 'destination': 'dest1.txt'},
                {'action': 'move', 'file': 'file2.txt', 'destination': 'dest2.txt'},
                {'action': 'move', 'file': 'file3.txt', 'destination': 'dest3.txt'},
            ]

            dedup_utils.create_transaction_log(operations, log_file)

            # Verify operations list is preserved
            with open(log_file, 'r') as f:
                transaction = json.load(f)

            # The order should be reversed during rollback
            assert transaction['operations'] == operations

    def test_rollback_archives_transaction_log(self):
        """Test that rollback archives the transaction log when operations exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            # Create a transaction with actual operations
            operations = [{'action': 'move', 'file': 'file.txt', 'destination': 'dest.txt'}]
            dedup_utils.create_transaction_log(operations, log_file)
            dedup_utils.mark_transaction_complete(log_file)

            # Rollback
            dedup_utils.rollback_operations(
                log_file=log_file,
                dry_run=False,
                archive_dir=os.path.join(tmpdir, '.dedup-deleted')
            )

            # Original log should be removed when operations are processed
            assert not os.path.exists(log_file)

    def test_rollback_incomplete_transaction_warning(self):
        """Test that rollback warns about incomplete transactions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, '.dedup_transaction.json')

            operations = [{'action': 'move', 'file': 'file.txt', 'destination': 'dest.txt'}]
            dedup_utils.create_transaction_log(operations, log_file)
            # Don't mark as complete

            # Rollback should still work but may warn
            stats = dedup_utils.rollback_operations(
                log_file=log_file,
                dry_run=True,
                archive_dir=os.path.join(tmpdir, '.dedup-deleted')
            )

            # Should still process operations
            assert len(stats) > 0


class TestConfirmationPrompts:
    """Test cases for user confirmation prompts."""

    def test_skip_confirmation_flag_skips_prompt(self):
        """Test that skip_confirmation=True skips the prompt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, 'source.txt')
            dest = os.path.join(tmpdir, 'dest.txt')

            with open(source, 'w') as f:
                f.write('content')

            operations = [{
                'action': 'move',
                'file': source,
                'destination': dest
            }]

            # Mock input to verify it's not called
            with patch('builtins.input') as mock_input:
                stats = dedup_utils.execute_operations(
                    operations,
                    dry_run=False,
                    create_log=False,
                    force_continue=True,
                    skip_confirmation=True
                )

                # input() should not be called
                mock_input.assert_not_called()
                assert stats['moved'] == 1

    def test_interactive_flag_shows_prompt_even_with_skip(self):
        """Test that interactive=True overrides skip_confirmation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, 'source.txt')
            dest = os.path.join(tmpdir, 'dest.txt')

            with open(source, 'w') as f:
                f.write('content')

            operations = [{
                'action': 'move',
                'file': source,
                'destination': dest
            }]

            # Mock input to return 'yes'
            with patch('builtins.input', return_value='yes'):
                stats = dedup_utils.execute_operations(
                    operations,
                    dry_run=False,
                    create_log=False,
                    force_continue=True,
                    skip_confirmation=True,
                    interactive=True
                )

                # Should execute because user answered 'yes'
                assert stats['moved'] == 1

    def test_user_declines_operations(self):
        """Test that operations are cancelled when user says no."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, 'source.txt')
            dest = os.path.join(tmpdir, 'dest.txt')

            with open(source, 'w') as f:
                f.write('content')

            operations = [{
                'action': 'move',
                'file': source,
                'destination': dest
            }]

            # Mock input to return 'no'
            with patch('builtins.input', return_value='no'):
                stats = dedup_utils.execute_operations(
                    operations,
                    dry_run=False,
                    create_log=False,
                    force_continue=True,
                    skip_confirmation=False,
                    interactive=True
                )

                # Operations should not be executed
                assert stats['moved'] == 0
                assert os.path.exists(source)
                assert not os.path.exists(dest)

    def test_user_confirms_with_yes_variant(self):
        """Test that user can confirm with 'y' instead of 'yes'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, 'source.txt')
            dest = os.path.join(tmpdir, 'dest.txt')

            with open(source, 'w') as f:
                f.write('content')

            operations = [{
                'action': 'move',
                'file': source,
                'destination': dest
            }]

            # Mock input to return 'y'
            with patch('builtins.input', return_value='y'):
                stats = dedup_utils.execute_operations(
                    operations,
                    dry_run=False,
                    create_log=False,
                    force_continue=True,
                    skip_confirmation=False,
                    interactive=True
                )

                # Should execute
                assert stats['moved'] == 1
                assert not os.path.exists(source)
                assert os.path.exists(dest)

    def test_no_prompt_in_dry_run_mode(self):
        """Test that no confirmation prompt is shown in dry-run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, 'source.txt')
            dest = os.path.join(tmpdir, 'dest.txt')

            with open(source, 'w') as f:
                f.write('content')

            operations = [{
                'action': 'move',
                'file': source,
                'destination': dest
            }]

            # Mock input to verify it's not called
            with patch('builtins.input') as mock_input:
                stats = dedup_utils.execute_operations(
                    operations,
                    dry_run=True,
                    create_log=False,
                    skip_confirmation=False,
                    interactive=False
                )

                # input() should not be called in dry-run
                mock_input.assert_not_called()
                assert stats['moved'] == 1
                assert os.path.exists(source)  # File not moved in dry-run
