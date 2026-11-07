#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "tools/install-plan.py"
spec = importlib.util.spec_from_file_location("mc_install_plan", SCRIPT)
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)

class PlanTests(unittest.TestCase):
    def fixture(self, root):
        source = root / "source/cockpit/minecraft-manager"
        source.mkdir(parents=True)
        (source / "manifest.json").write_text('{"tools":{"minecraft":{}}}')
        return root / "source"

    def test_upgrade_preserves_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source = self.fixture(root)
            live = root / "cockpit/minecraft-manager"
            live.mkdir(parents=True)
            (live / "manifest.json").write_text('{"tools":{"minecraft":{}}}')
            result = planner.plan([str(root / "cockpit")], source)
            self.assertEqual(result["mode"], "upgrade")
            self.assertEqual(result["canonical_target"], str(live))
            self.assertFalse(result["install_ready"])
            self.assertFalse(result["will_delete_modules"])

    def test_fresh_install_stays_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source = self.fixture(root)
            result = planner.plan([str(root / "cockpit")], source)
            self.assertEqual(result["mode"], "fresh")
            self.assertFalse(result["install_ready"])

    def test_noncanonical_module_requires_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source = self.fixture(root)
            other = root / "cockpit/minecraft-legacy"
            other.mkdir(parents=True)
            (other / "manifest.json").write_text('{"tools":{"minecraft":{}}}')
            result = planner.plan([str(root / "cockpit")], source)
            self.assertTrue(any("manual review" in b for b in result["blockers"]))
            self.assertFalse(result["will_delete_modules"])

if __name__ == "__main__":
    unittest.main()
