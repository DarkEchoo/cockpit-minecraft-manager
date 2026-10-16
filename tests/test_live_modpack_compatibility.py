import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SOURCE=Path(__file__).resolve().parents[1]/"backend/cockpit-minecraft-modpacks"
spec=importlib.util.spec_from_file_location("mc_modpacks",SOURCE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class LiveModpackCompatibilityTests(unittest.TestCase):
    def test_live_loader_actions_preserved(self):
        from inspect import getsource
        dispatch=getsource(mod.main)
        self.assertIn("loader-plan",dispatch)
        self.assertIn("preflight",dispatch)
    def test_java_minimum_baselines(self):
        self.assertEqual(mod._required_java_major("1.20.4"),17)
        self.assertEqual(mod._required_java_major("1.20.5"),21)
        self.assertEqual(mod._required_java_major("1.21.1"),21)
        self.assertIsNone(mod._required_java_major("snapshot"))
    def test_loader_version_input_validation(self):
        for value in ("../unsafe", "a/b", "", "a"*100):
            with self.assertRaises(ValueError):
                mod._loader_version(value)
    def test_nonfabric_plan_does_not_install(self):
        meta={"loader":"neoforge","minecraft_version":"1.21.1","status":"custom-manifest-only"}
        with patch.object(mod,"load",return_value=(Path("/tmp/workspace"),meta)):
            plan=mod.loader_plan("test")
        self.assertFalse(plan["changes_made"])
        self.assertEqual(plan["status"],"planning-only")
    def test_fabric_metadata_plan_is_read_only(self):
        meta={"loader":"fabric","minecraft_version":"1.21.1","status":"custom-manifest-only"}
        def metadata(path):
            return [{"loader":{"stable":True,"version":"0.17.2"}}] if path.startswith("loader") else [{"stable":True,"version":"1.1.0"}]
        with patch.object(mod,"load",return_value=(Path("/tmp/workspace"),meta)),patch.object(mod,"_fabric_json",side_effect=metadata):
            plan=mod.loader_plan("test")
        self.assertTrue(plan["can_stage"])
        self.assertFalse(plan["changes_made"])
if __name__=="__main__":unittest.main()
