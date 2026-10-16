import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/recovery-fixture.py"
spec = importlib.util.spec_from_file_location("mc_recovery_fixture", SCRIPT)
rec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rec)

class RecoveryFixtureTests(unittest.TestCase):
    def fixture(self, root):
        (root / rec.MARKER).touch()
        src, dst = root / "source", root / "installed"
        src.mkdir()
        dst.mkdir()
        (src / "a").write_text("new a")
        (src / "b").write_text("new b")
        (dst / "a").write_text("old a")
        (dst / "untouched").write_text("keep")
        return src, dst

    def test_partial_upgrade_recover_separately(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp)
            src, dst = self.fixture(root)
            self.assertEqual(rec.prepare(root), 2)
            rec.apply_partial(root, 2)
            self.assertEqual((dst / "a").read_text(), "new a")
            self.assertTrue((dst / "b").exists())
            self.assertEqual(rec.recover(root), 2)
            self.assertEqual((dst / "a").read_text(), "old a")
            self.assertFalse((dst / "b").exists())
            self.assertEqual((dst / "untouched").read_text(), "keep")
            self.assertFalse((root / rec.JOURNAL).exists())

    def test_unmarked_directory_refused(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            with self.assertRaises(ValueError):
                rec.prepare(tmp)

    def test_existing_journal_must_be_recovered(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp)
            self.fixture(root)
            rec.prepare(root)
            with self.assertRaises(ValueError):
                rec.prepare(root)
            rec.recover(root)

if __name__ == "__main__":
    unittest.main()
