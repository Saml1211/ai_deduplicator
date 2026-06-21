#!/usr/bin/env python3
"""
apply_manifest.py — execute a *vetted* (keeper, drop) dedup manifest through this
package's proven safe archive + rollback engine.

Why this exists
---------------
The auto deduper (`ai-deduplicate`) keeps the "first-seen" copy and may reorganise
folders. For a *curated* cleanup — e.g. an externally reviewed plan where you have
already decided exactly which copy to keep and which to drop — you instead want to:

  * delete EXACTLY the duplicates you vetted,
  * keep EXACTLY the copies you chose,
  * touch nothing else,

while still getting this package's safety guarantees. So this thin layer reuses
`dedup_utils.execute_operations()`:

  * every "drop" is ARCHIVED to ``<root>/.dedup-deleted`` (never hard-deleted),
  * a transaction log is written so the whole run is reversible (``--undo``),
  * a "drop" is only archived if it is byte-identical (SHA-256) to its keeper,
  * keepers are never touched, and dry-run is the default.

Manifest format
---------------
TSV, optional header row, columns = ``sizeGB <TAB> KEEPER_PATH <TAB> DROP_PATH``.
Blank lines and lines beginning with ``#`` are ignored.

Usage
-----
    python -m ai_deduplicator.apply_manifest -m plan.tsv                  # dry-run preview
    python -m ai_deduplicator.apply_manifest -m plan.tsv --execute        # archive drops (reversible)
    python -m ai_deduplicator.apply_manifest -m plan.tsv --undo --execute # roll the run back
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import List, Tuple

try:  # installed as part of the package
    from . import dedup_utils
except ImportError:  # running the file directly
    import dedup_utils  # type: ignore


def _volume_root(path: str) -> str:
    """Return the mount root for *path* (``/Volumes/NAME`` for externals, else ``/``)."""
    parts = os.path.abspath(path).split(os.sep)
    if len(parts) >= 3 and parts[1] == "Volumes":
        return os.sep.join(parts[:3])  # /Volumes/NAME
    return os.sep


def parse_manifest(path: str) -> List[Tuple[str, str, str]]:
    """Parse a ``sizeGB <TAB> KEEPER <TAB> DROP`` TSV into (keeper, drop, size) tuples."""
    pairs: List[Tuple[str, str, str]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) < 3:
                continue
            size, keeper, drop = cols[0].strip(), cols[1].strip(), cols[2].strip()
            if not keeper or not drop:
                continue
            try:  # skip a header row whose first column is not numeric
                float(size)
            except ValueError:
                continue
            pairs.append((keeper, drop, size))
    return pairs


def verify_pairs(pairs, full_hash: bool = True):
    """Return ``(ops, skipped)``.

    ``ops`` are ``{'action': 'remove', ...}`` dicts for drops confirmed safe to archive
    (the drop exists, the keeper exists, and — when *full_hash* — they are byte-identical).
    Anything uncertain is left untouched and reported in ``skipped``.
    """
    ops, skipped = [], []
    for keeper, drop, _size in pairs:
        if not os.path.isfile(drop):
            skipped.append((drop, "drop-missing (already gone)"))
            continue
        if not os.path.isfile(keeper):
            skipped.append((drop, "KEEPER MISSING — kept drop to be safe"))
            continue
        try:
            if os.path.getsize(keeper) != os.path.getsize(drop):
                skipped.append((drop, "size-mismatch — kept"))
                continue
        except OSError as exc:
            skipped.append((drop, f"stat-error: {exc} — kept"))
            continue
        if full_hash:
            hk = dedup_utils.calculate_file_hash(keeper)
            hd = dedup_utils.calculate_file_hash(drop)
            if not hk or not hd:
                skipped.append((drop, "hash-failed — kept"))
                continue
            if hk != hd:
                skipped.append((drop, "HASH MISMATCH — kept (not a true duplicate!)"))
                continue
        ops.append({
            "action": "remove",
            "file": drop,
            "reason": f"verified duplicate of {keeper}",
        })
    return ops, skipped


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply a vetted (keeper, drop) dedup manifest via the safe archive + undo engine.")
    parser.add_argument("-m", "--manifest", required=True, help="TSV: sizeGB<TAB>KEEPER<TAB>DROP")
    parser.add_argument("--execute", action="store_true",
                        help="Actually archive the drops (reversible). Omit for a dry run.")
    parser.add_argument("--undo", action="store_true", help="Roll back the last apply on this volume.")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip the confirmation prompt.")
    parser.add_argument("--archive-dir", default=None,
                        help="Override the archive + log location (default: the files' volume root).")
    parser.add_argument("--no-hash", action="store_true",
                        help="Skip SHA-256 verification (size-only). NOT recommended.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    pairs = parse_manifest(args.manifest)
    if not pairs:
        print("No (keeper, drop) pairs found in manifest.")
        return 1

    root = args.archive_dir or _volume_root(pairs[0][1])
    archive_dir = os.path.join(root, ".dedup-deleted")
    log_file = os.path.join(root, ".dedup_transaction.json")

    if args.undo:
        print(f"↩  Rolling back from {log_file}  ({'LIVE' if args.execute else 'dry-run'}) ...")
        stats = dedup_utils.rollback_operations(
            log_file=log_file, dry_run=not args.execute, archive_dir=archive_dir)
        print(f"   {stats}")
        return 0

    print(f"Manifest : {len(pairs)} pairs")
    print(f"Archive  : {archive_dir}")
    print(f"Verifying ({'SHA-256' if not args.no_hash else 'size-only'}) ...")
    ops, skipped = verify_pairs(pairs, full_hash=not args.no_hash)

    freed = 0
    for op in ops:
        try:
            freed += os.path.getsize(op["file"])
        except OSError:
            pass

    print(f"\n✅ verified safe to archive: {len(ops)} files  ({freed / 1024 ** 3:.2f} GB)")
    if skipped:
        print(f"⏭  skipped / kept: {len(skipped)}")
        for path, why in skipped[:40]:
            print(f"     - {why}: {path}")

    if not ops:
        print("Nothing to do.")
        return 0

    if not args.execute:
        print("\n(DRY RUN — nothing changed. Re-run with --execute to archive the drops.)")
        print("Each drop is archived (not deleted) with a transaction log; undo with --undo --execute.")
        return 0

    stats = dedup_utils.execute_operations(
        ops, dry_run=False, create_log=True, log_file=log_file,
        archive_dir=archive_dir, skip_confirmation=args.yes)
    print(f"\nDone: archived={stats.get('archived', 0)} errors={stats.get('errors', 0)}")
    print(f"Space is reclaimed once you purge the archive:  rm -rf '{archive_dir}'  (when you're happy)")
    print(f"Undo before then:  python -m ai_deduplicator.apply_manifest -m '{args.manifest}' --undo --execute")
    return 0


if __name__ == "__main__":
    sys.exit(main())
