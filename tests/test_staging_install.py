import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/staging-install.py"
spec = importlib.util.spec_from_file_location("mc_staging", SCRIPT)
staging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(staging)

class StagingTests(unittest.TestCase):
    def test_real_repo_files_staged_safely(self):
        repo = SCRIPT.parents[1]
        with tempfile.TemporaryDirectory(prefix="mc-v12-", dir="/tmp") as tmp:
            sandbox = Path(tmp)
            (sandbox / staging.MARKER).touch()
            result = staging.deploy(repo, sandbox)
            self.assertTrue(result["fixture_only"])
            self.assertFalse(result["production_apply_enabled"])
            self.assertTrue((sandbox / "installed/frontend/manifest.json").is_file())
            self.assertTrue((sandbox / "installed/backend/cockpit-minecraft-helper").is_file())

    def test_unmarked_fixture_refused(self):
        repo = SCRIPT.parents[1]
        with tempfile.TemporaryDirectory(prefix="mc-v12-", dir="/tmp") as tmp:
            with self.assertRaises(ValueError):
                staging.deploy(repo, tmp)

    def test_failure_injection_refuses_success(self):
        repo = SCRIPT.parents[1]
        with tempfile.TemporaryDirectory(prefix="mc-v12-", dir="/tmp") as tmp:
            sandbox = Path(tmp)
            (sandbox / staging.MARKER).touch()
            with self.assertRaises(RuntimeError):
                staging.deploy(repo, sandbox, fail_after=1)
            self.assertFalse(any((sandbox / "installed/frontend").iterdir()))

if __name__ == "__main__":
    unittest.main()
