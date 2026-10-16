import importlib.util
from pathlib import Path
import tempfile
import unittest
SCRIPT=Path(__file__).resolve().parents[1]/"tools/unified-install-fixture.py"
spec=importlib.util.spec_from_file_location("unified_install_fixture",SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
class UnifiedInstallFixtureTests(unittest.TestCase):
 def fixture(self,root):
  (root/".mc-fixture-only").touch()
  (root/"installed").mkdir()
  old=root/"installed/share/cockpit/minecraft-manager"
  old.mkdir(parents=True)
  (old/"app.js").write_text("original")
  return old
 def test_full_install_stages_components(self):
  with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
   root=Path(tmp)
   self.fixture(root)
   result=mod.install_fixture(SCRIPT.parents[1],root)
   self.assertTrue(result["ok"])
   self.assertTrue((root/"installed/libexec/cockpit-minecraft-helper").is_file())
   self.assertTrue((root/"installed/templates/systemd/cockpit-mc-snapshot@.service.in").is_file())
 def test_failure_restores_original_app(self):
  with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
   root=Path(tmp)
   old=self.fixture(root)
   with self.assertRaises(RuntimeError):
    mod.install_fixture(SCRIPT.parents[1],root,fail_after=8)
   self.assertEqual((old/"app.js").read_text(),"original")
 def test_requires_fixture_marker(self):
  with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
   root=Path(tmp)
   (root/"installed").mkdir()
   with self.assertRaises(ValueError):
    mod.install_fixture(SCRIPT.parents[1],root)
if __name__=="__main__":unittest.main()
