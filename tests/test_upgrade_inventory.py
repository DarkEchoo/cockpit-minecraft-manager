import importlib.util
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "tools/upgrade-inventory.py"
spec = importlib.util.spec_from_file_location("upgrade_inventory", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class UpgradeInventoryTests(unittest.TestCase):
    def test_existing_and_missing_files_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            source = base / "src"
            front = source / "cockpit/minecraft-manager"
            back = source / "backend"
            front.mkdir(parents=True)
            back.mkdir()
            (front / "index.html").write_text("new")
            (back / "helper").write_text("new")
            target_front = base / "installed-frontend"
            target_back = base / "installed-backend"
            target_front.mkdir()
            target_back.mkdir()
            (target_front / "index.html").write_text("old")
            result = module.build_plan(source, target_front, target_back)
            self.assertFalse(result["safe_to_apply"])
            self.assertEqual(len(result["files"]), 2)
            self.assertEqual({e["action"] for e in result["files"]},
                             {"replace-existing-file", "review-backend-path"})
            self.assertEqual((target_front / "index.html").read_text(), "old")

    def test_symlink_destination_blocks_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            source = base / "src"
            front = source / "cockpit/minecraft-manager"
            back = source / "backend"
            front.mkdir(parents=True)
            back.mkdir()
            (front / "index.html").write_text("new")
            target_front = base / "installed-frontend"
            target_front.mkdir()
            target_back = base / "installed-backend"
            target_back.mkdir()
            (target_front / "index.html").symlink_to(front / "index.html")
            result = module.build_plan(source, target_front, target_back)
            self.assertTrue(any("Unsafe destination type" in b for b in result["blockers"]))
            self.assertFalse(any(e["destination"].endswith("index.html") for e in result["files"]))

if __name__ == "__main__":
    unittest.main()
