import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/dependency-audit.py"
spec = importlib.util.spec_from_file_location("mc_dependency_audit", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class DependencyAuditTests(unittest.TestCase):
    def test_detects_nonstdlib_without_executing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = root / "backend"
            helpers = root / "addons/backup-manager/helpers"
            backend.mkdir()
            helpers.mkdir(parents=True)
            (backend / "worker").write_text("import json\nimport psutil\nfrom requests import get\n")
            result = module.inspect_imports(root)
            self.assertEqual({d["module"] for d in result["dependencies"]},
                             {"psutil", "requests"})
            self.assertTrue(result["read_only"])
            self.assertFalse(result["ready_for_public_install"])

    def test_missing_directory_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = module.inspect_imports(Path(tmp))
            self.assertEqual(len(result["parse_errors"]), 2)

if __name__ == "__main__":
    unittest.main()
