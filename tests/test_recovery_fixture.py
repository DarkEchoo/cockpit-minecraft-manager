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

    def test_corrupt_journal_rejected_without_restoration(self):
        import json
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp)
            _, dst = self.fixture(root)
            rec.prepare(root)
            rec.apply_partial(root, 1)
            journal = root / rec.JOURNAL / "manifest.json"
            data = json.loads(journal.read_text())
            data["entries"][1]["name"] = data["entries"][0]["name"]
            journal.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                rec.recover(root)
            self.assertEqual((dst / "a").read_text(), "new a")
            self.assertTrue((root / rec.JOURNAL).exists())

    def test_bad_journal_id_rejected(self):
        import json
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp)
            self.fixture(root)
            rec.prepare(root)
            journal = root / rec.JOURNAL / "manifest.json"
            data = json.loads(journal.read_text())
            data["entries"][0]["id"] = "../escape"
            journal.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                rec.recover(root)

    def test_recover_can_be_replayed_before_journal_cleanup(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp)
            _, dst = self.fixture(root)
            rec.prepare(root)
            rec.apply_partial(root, 2)
            # Inject an interruption after restoring a file by replacing the
            # directory sync hook. Recovery must retain originals.
            real_sync = rec.fsync_dir
            count = [0]
            def interrupted_sync(path):
                count[0] += 1
                if count[0] == 1:
                    raise RuntimeError("simulated recovery interruption")
                return real_sync(path)
            try:
                rec.fsync_dir = interrupted_sync
                with self.assertRaises(RuntimeError):
                    rec.recover(root)
            finally:
                rec.fsync_dir = real_sync
            self.assertTrue((root / rec.JOURNAL / "backups/0").exists())
            rec.recover(root)
            self.assertEqual((dst / "a").read_text(), "old a")
            self.assertFalse((dst / "b").exists())
            self.assertEqual((dst / "untouched").read_text(), "keep")

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
