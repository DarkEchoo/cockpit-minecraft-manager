#!/usr/bin/env python3
"""Fixtures for read-only Cockpit module inventory."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "tools/cockpit-module-inventory.py"
spec = importlib.util.spec_from_file_location("cockpit_module_inventory", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class InventoryTests(unittest.TestCase):
    def test_detects_candidates_without_authorizing_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for name in ("minecraft-manager", "minecraft-old"):
                folder = root / name
                folder.mkdir()
                (folder / "manifest.json").write_text(json.dumps({"tools":{"minecraft":{"label":"Minecraft"}}}))
            records = module.inventory([str(root)])
            self.assertEqual(len(records), 2)
            self.assertTrue(all(r["safe_to_delete_automatically"] is False for r in records))
            self.assertEqual({r["classification"] for r in records}, {"canonical-name-candidate", "review-required"})

    def test_ignores_unrelated_and_symlink_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            other = root / "dashboard"
            other.mkdir()
            (other / "manifest.json").write_text('{"tools":{"dashboard":{}}}')
            link = root / "minecraft-symlink"
            link.symlink_to(other, target_is_directory=True)
            self.assertEqual(module.inventory([str(root)]), [])

if __name__ == "__main__":
    unittest.main()
