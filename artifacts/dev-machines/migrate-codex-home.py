#!/usr/bin/env python3
"""Migrate rollout indexes and shell snapshots after stopping every Codex writer."""

import argparse
from collections import Counter
from contextlib import closing
import os
from pathlib import Path
import posixpath
import re
import sqlite3
import stat
import sys
import tempfile


UPDATE_SQL = "UPDATE threads SET rollout_path=? WHERE id=? AND rollout_path=?"


class MigrationError(Exception):
    pass


def prefix(value):
    if not value.startswith("/") or ".." in value.split("/"):
        raise MigrationError("Prefixes must be absolute paths without '..'.")
    value = posixpath.normpath("/" + value.lstrip("/"))
    if value == "/":
        raise MigrationError("A prefix cannot be the filesystem root.")
    return value


def locate_database(data_dir):
    root = Path(data_dir).absolute()
    if not root.is_dir() or root.resolve() != root:
        raise MigrationError("Data directory must exist and have no symlink components.")
    candidates = list(root.glob("state_*.sqlite"))
    if not candidates:
        return root, None
    if len(candidates) > 1:
        raise MigrationError("Expected at most one state_*.sqlite database.")
    db = candidates[0]
    if not db.is_file() or db.is_symlink():
        raise MigrationError("State database must be a regular file, not a symlink.")
    for suffix in ("-wal", "-shm", "-journal"):
        if Path(str(db) + suffix).is_symlink():
            raise MigrationError("Database journal files cannot be symlinks.")
    return root, db


def connect(db, mode):
    conn = sqlite3.connect(db.as_uri() + "?mode=" + mode, uri=True, timeout=10)
    conn.execute("PRAGMA trusted_schema=OFF")
    if mode == "ro":
        conn.execute("PRAGMA query_only=ON")
    return conn


def check_database(conn):
    if conn.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
        raise MigrationError("Database integrity check failed.")
    columns = {row[1]: row for row in conn.execute("PRAGMA table_info(threads)")}
    if (
        "id" not in columns
        or columns["id"][2].upper() != "TEXT"
        or columns["id"][5] != 1
        or "rollout_path" not in columns
        or columns["rollout_path"][2].upper() != "TEXT"
        or columns["rollout_path"][3] != 1
        or [name for name, row in columns.items() if row[5]] != ["id"]
        or conn.execute("SELECT type FROM sqlite_master WHERE name='threads'").fetchone() != ("table",)
    ):
        raise MigrationError("Unexpected threads schema; refusing migration.")
    # EXPLAIN compiles without executing. Program opcodes invoke trigger subprograms.
    # INSERT triggers and UPDATE OF unrelated columns cannot affect this update.
    bytecode = conn.execute("EXPLAIN " + UPDATE_SQL, ("", "", "")).fetchall()
    if any(row[1] == "Program" for row in bytecode):
        raise MigrationError("A trigger can run on rollout_path updates; refusing migration.")


def plan(conn, root, old, new):
    rows = conn.execute("SELECT id, rollout_path FROM threads").fetchall()
    if any(not isinstance(thread, str) or not isinstance(path, str) or not path.startswith("/")
           for thread, path in rows):
        raise MigrationError("Thread identifiers must be text and rollout paths must be absolute text paths.")
    normalized = [(thread, path, prefix(path)) for thread, path in rows]
    occupied = Counter(canonical for _, _, canonical in normalized)
    updates = []
    targets = set()
    for thread, path, canonical in normalized:
        relevant_prefix = next((p for p in (old, new) if canonical.startswith(p + "/")), None)
        if relevant_prefix is not None:
            rollout = root / canonical[len(relevant_prefix) + 1 :]
            if not rollout.is_file() or not rollout.resolve().is_relative_to(root):
                raise MigrationError("A matching rollout file is missing or outside the data directory.")
        if not canonical.startswith(old + "/"):
            continue
        suffix = canonical[len(old) + 1 :]
        target = new + "/" + suffix
        if target in occupied or target in targets:
            raise MigrationError("A destination rollout path conflicts with another index entry.")
        targets.add(target)
        updates.append((target, thread, path))
    return len(rows), updates


def make_backup(db):
    fd, filename = tempfile.mkstemp(prefix=db.name + ".backup-", dir=db.parent)
    os.fchmod(fd, 0o600)
    os.close(fd)
    backup = Path(filename)
    try:
        with closing(connect(db, "ro")) as source:
            with closing(sqlite3.connect(backup)) as target:
                source.backup(target)
                if target.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                    raise MigrationError("Backup integrity check failed.")
    except Exception:
        backup.unlink()
        raise
    return backup


def apply_index(db, root, old, new, result):
    with closing(connect(db, "rw")) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            check_database(conn)
            total, updates = plan(conn, root, old, new)
            result.update(total_threads=total, matching_paths=len(updates))
            if not updates:
                conn.rollback()
                return
            backup = make_backup(db)
            result["backup"] = str(backup)
            print("Rollback backup: " + str(backup), flush=True)
            changed = conn.executemany(UPDATE_SQL, updates).rowcount
            if changed != len(updates):
                raise MigrationError("Updated row count differs from the migration plan.")
            check_database(conn)
            after_total, remaining = plan(conn, root, old, new)
            if after_total != total or remaining:
                raise MigrationError("Post-update path counts differ from the migration plan.")
            actual = dict(conn.execute("SELECT id, rollout_path FROM threads"))
            if any(actual.get(thread) != target for target, thread, _ in updates):
                raise MigrationError("Post-update destination paths differ from the migration plan.")
            conn.commit()
            result["changed_paths"] = changed
        except Exception:
            conn.rollback()
            raise


def plan_snapshots(root, old, new):
    directory = root / "shell_snapshots"
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise MigrationError("Shell snapshots must be a directory, not a symlink.")
    # Match directory prefixes in shell assignments, quoted strings, and PATH lists.
    pattern = re.compile(rb"(?<![A-Za-z0-9_/.\-])/+" +
                         b"/+".join(re.escape(os.fsencode(part)) for part in old.split("/")[1:]) +
                         rb"(?=$|[/\s'\";:])")
    snapshots = []
    for path in sorted(directory.glob("*.sh")):
        if path.is_symlink() or not path.is_file():
            raise MigrationError("Shell snapshots must be regular files, not symlinks.")
        original = path.read_bytes()
        updated = pattern.sub(lambda _: os.fsencode(new), original)
        if updated != original:
            snapshots.append((path, original, updated, stat.S_IMODE(path.stat().st_mode)))
    return snapshots


def write_private(fd, content, mode):
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fchmod(stream.fileno(), mode)
        os.fsync(stream.fileno())


def apply_snapshots(root, snapshots, result):
    if not snapshots:
        return
    backup = Path(tempfile.mkdtemp(prefix="shell-snapshots.backup-", dir=root))
    backup.chmod(0o700)
    result["snapshot_backup"] = str(backup)
    print("Shell snapshot rollback backup: " + str(backup), flush=True)
    for path, original, updated, mode in snapshots:
        if path.is_symlink() or path.read_bytes() != original or stat.S_IMODE(path.stat().st_mode) != mode:
            raise MigrationError("A shell snapshot changed after inspection; refusing replacement.")
        fd = os.open(backup / path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        write_private(fd, original, mode)
        fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".migration-", dir=path.parent)
        try:
            write_private(fd, updated, mode)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        if path.read_bytes() != updated or stat.S_IMODE(path.stat().st_mode) != mode:
            raise MigrationError("Shell snapshot replacement verification failed.")
        result["changed_snapshots"] += 1


def migrate(data_dir, old_prefix, new_prefix, apply=False):
    root, db = locate_database(data_dir)
    old, new = prefix(old_prefix), prefix(new_prefix)
    if old == new or old.startswith(new + "/") or new.startswith(old + "/"):
        raise MigrationError("Old and new prefixes must be different, non-overlapping directories.")
    snapshots = plan_snapshots(root, old, new)
    total, updates = 0, []
    if db is not None:
        with closing(connect(db, "ro")) as conn:
            check_database(conn)
            total, updates = plan(conn, root, old, new)
    result = {"database": db.name if db else "(none)", "total_threads": total,
              "matching_paths": len(updates), "changed_paths": 0, "backup": None,
              "matching_snapshots": len(snapshots), "changed_snapshots": 0,
              "snapshot_backup": None, "apply": apply}
    if apply:
        if updates:
            apply_index(db, root, old, new, result)
        # File changes follow the database commit. A failure stops the caller;
        # a rerun migrates only the remaining snapshots and retains all backups.
        apply_snapshots(root, snapshots, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_dir", help="Existing backing directory containing state_*.sqlite")
    parser.add_argument("old_prefix")
    parser.add_argument("new_prefix")
    parser.add_argument("--apply", action="store_true", help="Write changes; stop all writers first")
    args = parser.parse_args()
    try:
        result = migrate(args.data_dir, args.old_prefix, args.new_prefix, args.apply)
    except (MigrationError, OSError, sqlite3.Error) as error:
        print("Migration refused: " + str(error), file=sys.stderr)
        return 1
    print("Mode: " + ("apply" if args.apply else "read-only dry run"))
    for name in ("database", "total_threads", "matching_paths", "changed_paths",
                 "matching_snapshots", "changed_snapshots"):
        print(name + ": " + str(result[name]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
