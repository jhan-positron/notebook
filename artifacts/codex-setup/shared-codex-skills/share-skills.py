#!/usr/bin/env python3
"""Share skills across Codex homes while retaining each original directory."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile


def exists(path):
    return os.path.lexists(path)


def fingerprint(path):
    """Compare content, empty directories, and internal symbolic links."""
    root = path.resolve(strict=True) if path.is_symlink() else path
    entries = []

    def visit(item, relative):
        mode = item.lstat().st_mode
        if stat.S_ISLNK(mode):
            entries.append((relative, "link", os.readlink(item)))
        elif stat.S_ISDIR(mode):
            entries.append((relative, "directory"))
            for child in sorted(item.iterdir()):
                visit(child, relative + "/" + child.name)
        elif stat.S_ISREG(mode):
            digest = hashlib.sha256()
            with item.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            entries.append((relative, "file", digest.hexdigest()))
        else:
            raise ValueError(f"Unsupported file type: {item}")

    visit(root, "")
    return entries


def copy_entry(source, target):
    source = source.resolve(strict=True) if source.is_symlink() else source
    if source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    else:
        shutil.copy2(source, target)


@contextmanager
def shared_lock(shared):
    shared.parent.mkdir(parents=True, exist_ok=True)
    with (shared.parent / ".skills-share.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def prepare(source, shared):
    if source.resolve() == shared:
        if not shared.is_dir():
            raise ValueError(f"Shared skills directory is missing: {shared}")
        return None
    if source.is_symlink():
        raise ValueError(f"Skills already links to another location: {source}")
    if exists(source) and not source.is_dir():
        raise ValueError(f"Skills path is not a directory: {source}")
    if exists(shared) and not shared.is_dir():
        raise ValueError(f"Shared path is not a directory: {shared}")
    if source in shared.parents or shared in source.parents:
        raise ValueError("Source and shared skills directories must not contain each other")

    missing = []
    conflicts = []
    for entry in sorted(source.iterdir()) if source.is_dir() else []:
        destination = shared / entry.name
        if entry.name == ".system" and exists(destination):
            continue
        source_contents = fingerprint(entry)
        if not exists(destination):
            missing.append(entry)
        elif source_contents != fingerprint(destination):
            conflicts.append(entry.name)
    if conflicts:
        raise ValueError("Conflicting skill contents; nothing migrated: " + ", ".join(conflicts))
    return missing


def migrate(codex_home, shared, apply=False):
    source = Path(os.path.abspath(codex_home)) / "skills"
    shared = Path(shared).resolve()

    def run():
        missing = prepare(source, shared)
        if missing is None:
            return [f"Already shared: {source}"]
        messages = [f"Copy: {entry} -> {shared / entry.name}" for entry in missing]
        if source.exists():
            messages.append(f"Preserve original directory beside: {source}")
        messages.append(f"Link: {source} -> {shared}")
        if not apply:
            return ["Dry run; no files changed."] + messages

        # Finish all copies before changing either skills root.
        with tempfile.TemporaryDirectory(prefix=".skills-share-", dir=shared.parent) as temporary:
            staged = Path(temporary)
            for entry in missing:
                copy_entry(entry, staged / entry.name)
            shared.mkdir(parents=True, exist_ok=True)
            for entry in missing:
                destination = shared / entry.name
                if exists(destination):
                    raise ValueError(f"Destination appeared during migration: {destination}")
                (staged / entry.name).rename(destination)

        source.parent.mkdir(parents=True, exist_ok=True)
        backup = None
        if source.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            backup = source.with_name(f"skills.backup-{stamp}")
            if exists(backup):
                raise ValueError(f"Backup path already exists: {backup}")
            source.rename(backup)
        try:
            source.symlink_to(shared, target_is_directory=True)
        except OSError:
            if backup is not None:
                backup.rename(source)
            raise
        if backup is not None:
            messages.append(f"Backup: {backup}")
        return messages

    if not apply:
        return run()
    with shared_lock(shared):
        return run()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--shared", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply changes and preserve the original skills directory")
    mode.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files (default)")
    args = parser.parse_args()
    try:
        for message in migrate(args.codex_home, args.shared, apply=args.apply):
            print(message)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
