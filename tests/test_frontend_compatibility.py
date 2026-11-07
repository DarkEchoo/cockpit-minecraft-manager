import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/frontend-compatibility.py"
spec = importlib.util.spec_from_file_location("mc_frontend_compat", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class FrontendCompatibilityTests(unittest.TestCase):
    def test_extra_installed_asset_blocks_auto_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, installed = Path(tmp) / "repo", Path(tmp) / "installed"
            repo.mkdir()
            installed.mkdir()
            (repo / "app.js").write_text("new")
            (installed / "app.js").write_text("old")
            (installed / "backup-ui.js").write_text("keep")
            result = mod.compare(repo, installed)
            self.assertEqual(result["installed_only"], ["backup-ui.js"])
            self.assertEqual(result["different"], ["app.js"])
            self.assertFalse(result["safe_to_upgrade"])

    def test_identical_files_are_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, installed = Path(tmp) / "repo", Path(tmp) / "installed"
            repo.mkdir()
            installed.mkdir()
            (repo / "ui.js").write_text("same")
            (installed / "ui.js").write_text("same")
            result = mod.compare(repo, installed)
            self.assertEqual(result["identical"], ["ui.js"])
            self.assertEqual(result["different"], [])

    def test_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, installed = Path(tmp) / "repo", Path(tmp) / "installed"
            repo.mkdir()
            installed.mkdir()
            (repo / "app.js").write_text("code")
            (installed / "app.js").symlink_to(repo / "app.js")
            result = mod.compare(repo, installed)
            self.assertTrue(result["blockers"])
            self.assertFalse(result["safe_to_upgrade"])

if __name__ == "__main__":
    unittest.main()
