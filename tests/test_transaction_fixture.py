import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/transaction-fixture.py"
spec = importlib.util.spec_from_file_location("mc_transaction", SCRIPT)
tx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tx)

class TransactionFixtureTests(unittest.TestCase):
    def fixture(self, root):
        src = root / "source"
        dst = root / "installed"
        src.mkdir()
        dst.mkdir()
        (src / "existing").write_text("new")
        (src / "added").write_text("added")
        (dst / "existing").write_text("old")
        (dst / "untouched").write_text("preserved")
        return src, dst

    def test_success_preserves_unrelated_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src, dst = self.fixture(root)
            outcome = tx.transact(root, src, dst)
            self.assertTrue(outcome["ok"])
            self.assertEqual((dst / "existing").read_text(), "new")
            self.assertEqual((dst / "added").read_text(), "added")
            self.assertEqual((dst / "untouched").read_text(), "preserved")

    def test_injected_failure_restores_originals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src, dst = self.fixture(root)
            with self.assertRaises(RuntimeError):
                tx.transact(root, src, dst, fail_after=2)
            self.assertEqual((dst / "existing").read_text(), "old")
            self.assertFalse((dst / "added").exists())
            self.assertEqual((dst / "untouched").read_text(), "preserved")

    def test_outside_sandbox_refused(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            src, dst = self.fixture(root)
            with self.assertRaises(ValueError):
                tx.transact(root, src, outside)

    def test_symlink_destination_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src, dst = self.fixture(root)
            (dst / "added").symlink_to(dst / "untouched")
            with self.assertRaises(ValueError):
                tx.transact(root, src, dst)
            self.assertEqual((dst / "existing").read_text(), "old")

if __name__ == "__main__":
    unittest.main()
