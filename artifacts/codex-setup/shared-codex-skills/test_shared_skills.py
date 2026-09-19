import os
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("share_skills", Path(__file__).with_name("share-skills.py"))
share_skills = importlib.util.module_from_spec(spec)
spec.loader.exec_module(share_skills)
migrate = share_skills.migrate


class ShareSkillsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "per-host"
        self.source = self.home / "skills"
        self.shared = self.root / "shared-home" / "skills"

    def skill(self, root, name, content="instructions"):
        directory = root / name
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(content)
        return directory

    def apply(self):
        return migrate(self.home, self.shared, apply=True)

    def backups(self):
        return list(self.home.glob("skills.backup-*"))

    def test_fresh_home_links_to_shared(self):
        self.apply()
        self.assertTrue(self.shared.is_dir())
        self.assertTrue(self.source.is_symlink())
        self.assertEqual(os.readlink(self.source), str(self.shared))
        self.assertEqual(self.backups(), [])

    def test_custom_merge_preserves_original_directory(self):
        custom = self.skill(self.source, "example")
        (custom / "empty").mkdir()
        (custom / "alias").symlink_to("SKILL.md")
        self.skill(self.shared, "existing")
        self.apply()
        self.assertTrue((self.shared / "example" / "empty").is_dir())
        self.assertEqual(os.readlink(self.shared / "example" / "alias"), "SKILL.md")
        self.assertTrue((self.shared / "existing" / "SKILL.md").is_file())
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual((self.backups()[0] / "example" / "SKILL.md").read_text(), "instructions")

    def test_top_level_skill_alias_is_copied_as_directory(self):
        real = self.skill(self.root / "other-host", "goal", "goal instructions")
        self.source.mkdir(parents=True)
        (self.source / "goal").symlink_to(real, target_is_directory=True)
        self.apply()
        self.assertFalse((self.shared / "goal").is_symlink())
        self.assertEqual((self.shared / "goal" / "SKILL.md").read_text(), "goal instructions")
        self.assertTrue((self.backups()[0] / "goal").is_symlink())

    def test_conflict_refuses_before_copy_or_source_rename(self):
        self.skill(self.source, "a-new")
        self.skill(self.source, "z-conflict", "source")
        self.skill(self.shared, "z-conflict", "shared")
        with self.assertRaisesRegex(ValueError, "Conflicting.*z-conflict"):
            self.apply()
        self.assertFalse(self.source.is_symlink())
        self.assertEqual(self.backups(), [])
        self.assertFalse((self.shared / "a-new").exists())
        self.assertEqual((self.source / "z-conflict" / "SKILL.md").read_text(), "source")
        self.assertEqual((self.shared / "z-conflict" / "SKILL.md").read_text(), "shared")

    def test_identical_duplicate_retains_destination_file(self):
        self.skill(self.source, "same")
        target = self.skill(self.shared, "same") / "SKILL.md"
        inode = target.stat().st_ino
        self.apply()
        self.assertEqual(target.stat().st_ino, inode)
        self.assertTrue(self.source.is_symlink())

    def test_repeat_is_noop(self):
        self.skill(self.source, "example")
        self.apply()
        backups = self.backups()
        self.assertEqual(self.apply(), [f"Already shared: {self.source}"])
        self.assertEqual(self.backups(), backups)

    def test_dry_run_does_not_create_anything(self):
        self.skill(self.source, "example")
        original = sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*"))
        output = migrate(self.home, self.shared)
        self.assertIn("Dry run", output[0])
        self.assertEqual(sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*")), original)
        self.assertFalse(self.source.is_symlink())

    def test_existing_system_tree_is_not_replaced(self):
        self.skill(self.source, ".system", "source version")
        self.skill(self.shared, ".system", "shared version")
        self.apply()
        self.assertEqual((self.shared / ".system" / "SKILL.md").read_text(), "shared version")
        self.assertEqual((self.backups()[0] / ".system" / "SKILL.md").read_text(), "source version")

    def test_missing_system_tree_is_seeded(self):
        self.skill(self.source, ".system", "source version")
        self.apply()
        self.assertEqual((self.shared / ".system" / "SKILL.md").read_text(), "source version")

    def test_failed_symlink_restores_original_source(self):
        self.skill(self.source, "example")
        with patch.object(Path, "symlink_to", side_effect=OSError("simulated failure")):
            with self.assertRaisesRegex(OSError, "simulated failure"):
                self.apply()
        self.assertFalse(self.source.is_symlink())
        self.assertEqual(self.backups(), [])
        self.assertEqual((self.source / "example" / "SKILL.md").read_text(), "instructions")

    def test_unexpected_source_root_link_refuses(self):
        other = self.root / "other"
        self.skill(other, "example")
        self.home.mkdir()
        self.source.symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "another location"):
            self.apply()
        self.assertEqual(self.source.resolve(), other)
        self.assertEqual(self.backups(), [])

    def test_shared_home_itself_is_noop(self):
        self.shared.mkdir(parents=True)
        output = migrate(self.shared.parent, self.shared, apply=True)
        self.assertEqual(output, [f"Already shared: {self.shared}"])
        self.assertFalse(self.shared.is_symlink())


if __name__ == "__main__":
    unittest.main()
