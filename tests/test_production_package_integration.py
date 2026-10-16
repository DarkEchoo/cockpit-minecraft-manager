import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path)
 module=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(module)
 return module
transaction=load("production_transaction_integration","tools/production-transaction.py")

class CompletePackageUpgradeTests(unittest.TestCase):
 def test_complete_repository_upgrades_without_touching_config_and_units(self):
  with tempfile.TemporaryDirectory(dir="/tmp") as directory:
   root=Path(directory)
   frontend=root/"usr/local/share/cockpit/minecraft-manager"
   frontend.mkdir(parents=True)
   (frontend/"app.js").write_text("live customized frontend")
   config=root/"etc/minecraft-backup/manual-backup.conf"
   config.parent.mkdir(parents=True)
   config.write_text("custom backup settings")
   unit=root/"etc/systemd/system/minecraft-26.service"
   unit.parent.mkdir(parents=True)
   unit.write_text("original service")
   result=transaction.apply(ROOT,root)
   self.assertGreater(result["applied"],20)
   self.assertEqual(config.read_text(),"custom backup settings")
   self.assertEqual(unit.read_text(),"original service")
   self.assertTrue((root/"usr/local/libexec/cockpit-minecraft-modpack-audit").is_file())
   self.assertTrue((root/"usr/local/libexec/minecraft-manual-backup").is_file())
   self.assertTrue((root/"usr/local/share/cockpit/minecraft-manager/app.js").is_file())
   transaction.recover(root)
   self.assertEqual((frontend/"app.js").read_text(),"live customized frontend")
   self.assertEqual(config.read_text(),"custom backup settings")
   self.assertEqual(unit.read_text(),"original service")
   self.assertFalse((root/"usr/local/libexec/cockpit-minecraft-modpack-audit").exists())
if __name__=="__main__":unittest.main()
