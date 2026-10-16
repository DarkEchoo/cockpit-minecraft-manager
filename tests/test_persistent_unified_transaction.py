import importlib.util
from pathlib import Path
import tempfile
import unittest

TOOLS=Path(__file__).resolve().parents[1]/"tools"
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,TOOLS/path)
 obj=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(obj)
 return obj
tx=load("persistent-unified-transaction.py","persistent_tx")
builder=load("build-release-stage.py","release_builder")

class PersistentUnifiedTests(unittest.TestCase):
 def fixture(self,root):
  (root/tx.MARKER).touch()
  (root/"installed/share/cockpit/minecraft-manager").mkdir(parents=True)
  (root/"installed/share/cockpit/minecraft-manager/app.js").write_text("original")
  builder.stage(TOOLS.parent,root/"release-stage")
 def test_interrupt_and_recover_across_components(self):
  with tempfile.TemporaryDirectory(dir="/tmp") as folder:
   root=Path(folder)
   self.fixture(root)
   tx.prepare(root)
   with self.assertRaises(RuntimeError):
    tx.apply(root,fail_after=10)
   self.assertTrue((root/tx.JOURNAL/"manifest.json").is_file())
   tx.recover(root)
   self.assertEqual((root/"installed/share/cockpit/minecraft-manager/app.js").read_text(),"original")
   self.assertFalse((root/"installed/libexec/cockpit-minecraft-helper").exists())
 def test_corrupt_backup_is_rejected_before_restore(self):
  with tempfile.TemporaryDirectory(dir="/tmp") as folder:
   root=Path(folder)
   self.fixture(root)
   tx.prepare(root)
   tx.apply(root,fail_after=None)
   (root/tx.JOURNAL/"backups/share/cockpit/minecraft-manager/app.js").write_text("corrupted")
   with self.assertRaisesRegex(ValueError,"damaged backup"):
    tx.recover(root)
 def test_missing_marker_refused(self):
  with tempfile.TemporaryDirectory(dir="/tmp") as folder:
   with self.assertRaises(ValueError):
    tx.prepare(folder)
if __name__=="__main__":unittest.main()
