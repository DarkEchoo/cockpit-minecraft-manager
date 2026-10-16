import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/build-release-stage.py"
spec = importlib.util.spec_from_file_location("mc_build_stage", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ReleaseStageTests(unittest.TestCase):
    def test_build_includes_frontend_and_backup_units(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            out = Path(tmp) / "stage"
            result = mod.stage(SCRIPT.parents[1], out)
            self.assertFalse(result["production_apply_enabled"])
            paths = {entry["path"] for entry in result["files"]}
            self.assertIn("share/cockpit/minecraft-manager/modpack-backup-ui.js", paths)
            self.assertIn("share/cockpit/minecraft-manager/modpack-schedule-ui.js", paths)
            self.assertIn("libexec/mc_backup_config.py", paths)
            self.assertIn("templates/systemd/cockpit-mc-snapshot@.service.in", paths)
            self.assertTrue((out / "release-manifest.json").is_file())

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            with self.assertRaises(ValueError):
                mod.stage(SCRIPT.parents[1], tmp)

    def test_staging_outside_tmp_refused(self):
        with self.assertRaises(ValueError):
            mod.stage(SCRIPT.parents[1], "/usr/local/share/cockpit/test-v12-stage")

if __name__ == "__main__":
    unittest.main()
