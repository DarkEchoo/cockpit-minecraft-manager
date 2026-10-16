import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/package-inventory.py"
spec = importlib.util.spec_from_file_location("mc_package_inventory", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PackageInventoryTests(unittest.TestCase):
    def test_real_repo_includes_backup_assets(self):
        result = mod.inventory(SCRIPT.parents[1])
        self.assertFalse(result["blockers"])
        self.assertTrue(any(p.endswith("mc_backup_config.py") for p in result["packages"]["backup_helpers"]))
        self.assertTrue(any(p.endswith("modpack-schedule-ui.js") for p in result["packages"]["backup_frontend"]))
        self.assertTrue(result["packages"]["backup_units"])
        self.assertFalse(result["safe_to_install"])

    def test_missing_components_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = mod.inventory(tmp)
            self.assertTrue(result["blockers"])
            self.assertFalse(result["safe_to_install"])

if __name__ == "__main__":
    unittest.main()
