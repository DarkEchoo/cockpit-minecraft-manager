import importlib.util
from pathlib import Path
import subprocess
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/cockpit-prerequisite.py"
spec = importlib.util.spec_from_file_location("cockpit_prerequisite", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class CockpitPrerequisiteTests(unittest.TestCase):
    def run_fake(self, args, **kwargs):
        if "-W" in args:
            output = "install ok installed"
        elif "show" in args:
            output = "loaded"
        else:
            output = "active"
        return subprocess.CompletedProcess(args, 0, output, "")

    def test_installed_active(self):
        result = module.check(lambda name: "/usr/bin/" + name, self.run_fake)
        self.assertTrue(result["ready"])

    def test_missing_cockpit_not_ready(self):
        result = module.check(lambda name: None, self.run_fake)
        self.assertFalse(result["ready"])
        self.assertTrue(result["issues"])

    def test_inactive_socket_not_ready(self):
        def stopped(args, **kwargs):
            if "is-active" in args:
                return subprocess.CompletedProcess(args, 3, "inactive", "")
            return self.run_fake(args, **kwargs)
        result = module.check(lambda name: "/usr/bin/" + name, stopped)
        self.assertFalse(result["ready"])
        self.assertFalse(result["socket_active"])

if __name__ == "__main__":
    unittest.main()
