import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location("migrate_index", Path(__file__).with_name("migrate-index.py"))
migration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migration)
OLD = "/home/codex-home-test"
NEW = "/home/jhan/codex-home-test"


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "state_5.sqlite"
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT NOT NULL, title TEXT)")

    def add(self, thread, path, create_file=True):
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO threads VALUES (?, ?, ?)", (thread, path, "unchanged"))
        if create_file:
            rollout = self.root / "sessions" / (thread + ".jsonl")
            rollout.parent.mkdir(exist_ok=True)
            rollout.write_bytes(b'{"synthetic":true}\n')

    def rows(self, database=None):
        with sqlite3.connect(database or self.db) as conn:
            return conn.execute("SELECT id, rollout_path, title FROM threads ORDER BY id").fetchall()

    def test_dry_run_normalizes_double_slashes_and_respects_boundary(self):
        self.add("a", OLD + "/sessions/a.jsonl")
        self.add("b", "/home//codex-home-test/sessions/b.jsonl")
        self.add("c", OLD + "-other/sessions/c.jsonl", False)
        before = self.db.read_bytes()
        result = migration.migrate(self.root, OLD, NEW)
        self.assertEqual(result["matching_paths"], 2)
        self.assertEqual(result["changed_paths"], 0)
        self.assertEqual(before, self.db.read_bytes())
        self.assertEqual(list(self.root.glob("*.backup-*")), [])

    def test_apply_backup_integrity_and_repeat_noop(self):
        self.add("a", OLD + "/sessions/a.jsonl")
        self.add("b", "/home//codex-home-test/sessions/b.jsonl")
        original = self.rows()
        content = (self.root / "sessions/a.jsonl").read_bytes()
        result = migration.migrate(self.root, OLD, NEW, apply=True)
        backup = Path(result["backup"])
        self.assertEqual(result["changed_paths"], 2)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.rows(backup), original)
        self.assertEqual(self.rows(), [("a", NEW + "/sessions/a.jsonl", "unchanged"),
                                       ("b", NEW + "/sessions/b.jsonl", "unchanged")])
        self.assertEqual((self.root / "sessions/a.jsonl").read_bytes(), content)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("PRAGMA quick_check").fetchone(), ("ok",))
        again = migration.migrate(self.root, OLD, NEW, apply=True)
        self.assertEqual(again["changed_paths"], 0)
        self.assertIsNone(again["backup"])
        self.assertEqual(len(list(self.root.glob("*.backup-*"))), 1)

    def test_missing_rollout_refuses_before_backup_or_change(self):
        self.add("a", OLD + "/sessions/a.jsonl", False)
        before = self.rows()
        for apply in (False, True):
            with self.assertRaisesRegex(migration.MigrationError, "missing"):
                migration.migrate(self.root, OLD, NEW, apply=apply)
        self.assertEqual(self.rows(), before)
        self.assertEqual(list(self.root.glob("*.backup-*")), [])

    def test_destination_collision_refuses(self):
        self.add("a", OLD + "/sessions/a.jsonl")
        self.add("b", NEW + "/sessions/a.jsonl", False)
        with self.assertRaisesRegex(migration.MigrationError, "conflicts"):
            migration.migrate(self.root, OLD, NEW, apply=True)

    def test_backup_includes_committed_wal_data(self):
        with sqlite3.connect(self.db) as keeper:
            self.assertEqual(keeper.execute("PRAGMA journal_mode=WAL").fetchone(), ("wal",))
            keeper.execute("PRAGMA wal_autocheckpoint=0")
            keeper.execute("SELECT count(*) FROM threads").fetchone()
            self.add("a", OLD + "/sessions/a.jsonl")
            self.assertTrue(Path(str(self.db) + "-wal").exists())
            result = migration.migrate(self.root, OLD, NEW, apply=True)
            self.assertEqual(self.rows(result["backup"]),
                             [("a", OLD + "/sessions/a.jsonl", "unchanged")])

    def test_failed_validation_rolls_back_and_retains_backup(self):
        self.add("a", OLD + "/sessions/a.jsonl")
        original = self.rows()
        check = migration.check_database
        calls = 0

        def fail_after_update(conn):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise migration.MigrationError("Synthetic integrity failure")
            return check(conn)

        with mock.patch.object(migration, "check_database", side_effect=fail_after_update):
            with self.assertRaisesRegex(migration.MigrationError, "Synthetic"):
                migration.migrate(self.root, OLD, NEW, apply=True)
        self.assertEqual(self.rows(), original)
        backups = list(self.root.glob("*.backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(self.rows(backups[0]), original)

    def test_symlink_database_refuses(self):
        actual = self.root / "actual.sqlite"
        self.db.rename(actual)
        self.db.symlink_to(actual)
        with self.assertRaisesRegex(migration.MigrationError, "symlink"):
            migration.migrate(self.root, OLD, NEW)

    def test_ambiguous_database_refuses(self):
        (self.root / "state_6.sqlite").touch()
        with self.assertRaisesRegex(migration.MigrationError, "at most one"):
            migration.migrate(self.root, OLD, NEW)

    def test_fresh_home_without_database_is_noop(self):
        self.db.unlink()
        for apply in (False, True):
            result = migration.migrate(self.root, OLD, NEW, apply=apply)
            self.assertEqual(result["changed_paths"], 0)
            self.assertIsNone(result["backup"])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_noop_rechecks_destination_rollout_exists(self):
        self.add("a", NEW + "/sessions/a.jsonl", False)
        with self.assertRaisesRegex(migration.MigrationError, "missing"):
            migration.migrate(self.root, OLD, NEW, apply=True)

    def test_unexpected_schema_refuses(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("ALTER TABLE threads RENAME COLUMN rollout_path TO wrong_path")
        with self.assertRaisesRegex(migration.MigrationError, "schema"):
            migration.migrate(self.root, OLD, NEW)

    def test_unrelated_insert_and_column_update_triggers_are_allowed(self):
        self.add("a", OLD + "/sessions/a.jsonl")
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE trigger_events (value TEXT)")
            conn.execute("CREATE TRIGGER title_changed AFTER UPDATE OF title ON threads "
                         "BEGIN INSERT INTO trigger_events VALUES ('update'); END")
            conn.execute("CREATE TRIGGER thread_added AFTER INSERT ON threads "
                         "BEGIN INSERT INTO trigger_events VALUES ('insert'); END")
        result = migration.migrate(self.root, OLD, NEW, apply=True)
        self.assertEqual(result["changed_paths"], 1)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM trigger_events").fetchone(), (0,))

    def test_trigger_on_rollout_update_refuses_without_changes(self):
        self.add("a", OLD + "/sessions/a.jsonl")
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TRIGGER rollout_changed AFTER UPDATE OF rollout_path ON threads "
                         "BEGIN UPDATE threads SET title='unexpected' WHERE id=NEW.id; END")
        original = self.rows()
        with self.assertRaisesRegex(migration.MigrationError, "trigger"):
            migration.migrate(self.root, OLD, NEW, apply=True)
        self.assertEqual(self.rows(), original)
        self.assertEqual(list(self.root.glob("*.backup-*")), [])

    def snapshot(self, name, content, mode=0o640):
        directory = self.root / "shell_snapshots"
        directory.mkdir(exist_ok=True)
        path = directory / name
        path.write_bytes(content)
        path.chmod(mode)
        return path

    def test_snapshot_dry_run_and_apply_preserve_backup_mode_and_boundaries(self):
        original = (b'export CODEX_HOME="/home//codex-home-test"\n'
                    b"PATH='/home/codex-home-test/bin:/bin'\n"
                    b"LOOKALIKE=/home/codex-home-test-other\n"
                    b"NESTED=/other/home/codex-home-test\n")
        path = self.snapshot("example.sh", original)
        result = migration.migrate(self.root, OLD, NEW)
        self.assertEqual(result["matching_snapshots"], 1)
        self.assertEqual(result["changed_snapshots"], 0)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(self.root.glob("shell-snapshots.backup-*")), [])
        result = migration.migrate(self.root, OLD, NEW, apply=True)
        backup = Path(result["snapshot_backup"])
        self.assertEqual(result["changed_snapshots"], 1)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        self.assertEqual((backup / path.name).read_bytes(), original)
        self.assertEqual((backup / path.name).stat().st_mode & 0o777, 0o640)
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        self.assertEqual(path.read_bytes(),
                         b'export CODEX_HOME="/home/jhan/codex-home-test"\n'
                         b"PATH='/home/jhan/codex-home-test/bin:/bin'\n"
                         b"LOOKALIKE=/home/codex-home-test-other\n"
                         b"NESTED=/other/home/codex-home-test\n")
        again = migration.migrate(self.root, OLD, NEW, apply=True)
        self.assertEqual(again["changed_snapshots"], 0)
        self.assertIsNone(again["snapshot_backup"])
        self.assertEqual(list(self.root.glob("shell-snapshots.backup-*")), [backup])

    def test_snapshot_failure_after_database_commit_can_be_retried(self):
        self.add("a", OLD + "/sessions/a.jsonl")
        original = b"export CODEX_HOME=/home/codex-home-test\n"
        first = self.snapshot("a.sh", original)
        second = self.snapshot("b.sh", original)
        replace = migration.os.replace
        calls = 0

        def fail_second(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("Synthetic replacement failure")
            return replace(source, destination)

        with mock.patch.object(migration.os, "replace", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "Synthetic"):
                migration.migrate(self.root, OLD, NEW, apply=True)
        self.assertEqual(self.rows()[0][1], NEW + "/sessions/a.jsonl")
        self.assertNotEqual(first.read_bytes(), original)
        self.assertEqual(second.read_bytes(), original)
        initial_backup = next(self.root.glob("shell-snapshots.backup-*"))
        self.assertEqual((initial_backup / "a.sh").read_bytes(), original)
        self.assertEqual((initial_backup / "b.sh").read_bytes(), original)
        again = migration.migrate(self.root, OLD, NEW, apply=True)
        self.assertEqual(again["changed_paths"], 0)
        self.assertEqual(again["changed_snapshots"], 1)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertTrue(initial_backup.exists())


if __name__ == "__main__":
    unittest.main()
