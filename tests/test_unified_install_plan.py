import importlib.util
from pathlib import Path
import tempfile
import unittest
SCRIPT=Path(__file__).resolve().parents[1]/"tools/unified-install-plan.py"
spec=importlib.util.spec_from_file_location("unified_install_plan",SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
class UnifiedInstallPlanTests(unittest.TestCase):
 def test_existing_and_new_are_distinguished(self):
  with tempfile.TemporaryDirectory() as tmp:
   front=Path(tmp)/"front";backend=Path(tmp)/"libexec"
   front.mkdir();backend.mkdir()
   (front/"app.js").write_text("original")
   result=mod.plan(SCRIPT.parents[1],front,backend)
   self.assertFalse(result["production_apply_enabled"])
   self.assertEqual(next(f for f in result["files"] if f["destination"]==str(front/"app.js"))["operation"],"replace-with-backup")
   self.assertTrue(any(f["operation"]=="create" for f in result["files"]))
 def test_config_and_units_not_overwritten(self):
  with tempfile.TemporaryDirectory() as tmp:
   result=mod.plan(SCRIPT.parents[1],Path(tmp)/"front",Path(tmp)/"libexec")
   self.assertIn(mod.CONFIG,result["excluded_from_transaction"])
   self.assertTrue(all("/etc/" not in f["destination"] for f in result["files"]))
if __name__=="__main__":unittest.main()
