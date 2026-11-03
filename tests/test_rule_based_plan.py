"""Each scanned duplicate should be archived once, including preferred copies."""

import pytest

from ai_deduplicator import dedup_utils
from ai_deduplicator.deduplicate_files import generate_deduplication_plan


@pytest.mark.parametrize("preferred_count,outside_count", [(2, 0), (3, 0), (2, 2), (1, 2), (0, 3)])
def test_each_duplicate_has_one_operation(tmp_path, preferred_count, outside_count):
    preferred = tmp_path / "preferred"
    outside = tmp_path / "outside"
    files = [str(preferred / f"copy{i}.txt") for i in range(preferred_count)]
    files += [str(outside / f"copy{i}.txt") for i in range(outside_count)]
    operations = generate_deduplication_plan({"hash": files}, {r".*": str(preferred)})
    removals = [op["file"] for op in operations if op["action"] == "remove"]
    moves = [op for op in operations if op["action"] == "move"]
    assert removals == files[1:]
    assert len(moves) == (0 if preferred_count else 1)
    if moves:
        assert moves[0]["file"] == files[0]
        assert moves[0]["destination"] == str(preferred / "copy0.txt")


@pytest.mark.parametrize("rich_available", [False, True])
def test_planned_archive_and_undo_round_trip(tmp_path, monkeypatch, rich_available):
    if rich_available and not dedup_utils.RICH_AVAILABLE:
        pytest.skip("Rich is not installed")
    monkeypatch.setattr(dedup_utils, "RICH_AVAILABLE", rich_available)
    preferred = tmp_path / "preferred"
    preferred.mkdir()
    paths = [preferred / f"copy{i}.txt" for i in range(3)]
    for path in paths:
        path.write_bytes(b"same file contents\n")
    duplicates, _ = dedup_utils.scan_directory(str(preferred), parallel=False)
    operations = generate_deduplication_plan(duplicates, {r".*": str(preferred)})
    log = str(tmp_path / "transaction.json")
    archive = str(tmp_path / "archive")
    preview = dedup_utils.execute_operations(operations, dry_run=True)
    actual = dedup_utils.execute_operations(
        operations, dry_run=False, skip_confirmation=True,
        log_file=log, archive_dir=archive,
    )
    assert actual == preview == {"moved": 0, "archived": 2, "errors": 0}
    assert sum(path.exists() for path in paths) == 1
    restored = dedup_utils.rollback_operations(log, dry_run=False, archive_dir=archive)
    assert restored == {"restored": 2, "unmoved": 0, "errors": 0, "skipped": 0}
    assert all(path.read_bytes() == b"same file contents\n" for path in paths)


def test_distinct_preferred_groups_keep_their_own_copy():
    files = ["/docs/a.txt", "/docs/b.txt", "/images/a.png", "/images/b.png"]
    operations = generate_deduplication_plan(
        {"hash": files}, {r".*\.txt$": "/docs/", r".*": "/images/"},
    )
    assert [op["file"] for op in operations] == ["/docs/b.txt", "/images/b.png"]
    assert all(op["action"] == "remove" for op in operations)
