"""Verify the entry point resolves source relative to itself, never the caller's cwd."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class LocationIndependentInstallerTests(unittest.TestCase):
    def test_check_from_unrelated_cwd(self):
        with tempfile.TemporaryDirectory(prefix="mc-caller-") as tmp:
            result = subprocess.run(["bash", str(ROOT / "install.sh"), "--check"],
                                    cwd=tmp, capture_output=True, text=True, timeout=30)
            self.assertIn("Source present: cockpit/minecraft-manager/manifest.json",
                          result.stdout)
            self.assertIn("Unified installer --apply is intentionally blocked", result.stdout)

    def test_moved_tree_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="mc-relocate-") as tmp:
            dest = Path(tmp) / "Moved Release Folder"
            shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            result = subprocess.run(["bash", str(dest / "install.sh"), "--check"],
                                    cwd="/", capture_output=True, text=True, timeout=30)
            self.assertIn("Source present: cockpit/minecraft-manager/index.html",
                          result.stdout)
            self.assertNotIn("Missing source:", result.stdout)

    def test_apply_remains_blocked_from_arbitrary_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(["bash", str(ROOT / "install.sh"), "--apply"],
                                    cwd=tmp, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 3)
            self.assertIn("BLOCKED:", result.stderr)

if __name__ == "__main__":
    unittest.main()
