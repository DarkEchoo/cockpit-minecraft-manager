import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/system-dependency-audit.py"
spec = importlib.util.spec_from_file_location("mc_system_dependency_audit", SCRIPT)
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)

class SystemDependencyTests(unittest.TestCase):
    def test_missing_required_is_reported(self):
        result = audit_module.audit(lambda name: None)
        self.assertIn("python3", result["missing_required"])
        self.assertFalse(result["install_ready"])

    def test_optional_missing_does_not_count_as_required(self):
        result = audit_module.audit(lambda name: "/bin/" + name if name in audit_module.REQUIRED else None)
        self.assertEqual(result["missing_required"], [])
        self.assertTrue(any(not v["available"] and not v["required_for_preflight"] for v in result["checks"]))

if __name__ == "__main__":
    unittest.main()
