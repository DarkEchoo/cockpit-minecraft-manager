#!/usr/bin/env python3
"""Read-only Cockpit prerequisite check. Never installs/enables a service."""
import json
import shutil
import subprocess

def check(which=shutil.which, runner=subprocess.run):
    bridge = which("cockpit-bridge")
    systemctl = which("systemctl")
    dpkg = which("dpkg-query")
    result = {"read_only": True, "cockpit_bridge": bool(bridge),
              "package_installed": False, "socket_unit_present": False,
              "socket_active": False, "ready": False, "issues": []}
    def run(args):
        try:
            return runner(args, capture_output=True, text=True, timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return None
    if dpkg:
        proc = run([dpkg, "-W", "-f=${Status}", "cockpit"])
        result["package_installed"] = bool(proc and proc.returncode == 0 and
                                           proc.stdout.strip() == "install ok installed")
    if systemctl:
        unit = run([systemctl, "show", "cockpit.socket", "--property=LoadState", "--value"])
        result["socket_unit_present"] = bool(unit and unit.returncode == 0 and
                                            unit.stdout.strip() == "loaded")
        active = run([systemctl, "is-active", "cockpit.socket"])
        result["socket_active"] = bool(active and active.returncode == 0 and
                                       active.stdout.strip() == "active")
    if not result["cockpit_bridge"]: result["issues"].append("cockpit-bridge executable missing")
    if not result["package_installed"]: result["issues"].append("Cockpit package not confirmed installed")
    if not result["socket_unit_present"]: result["issues"].append("cockpit.socket unit not loaded")
    if not result["socket_active"]: result["issues"].append("cockpit.socket not active")
    result["ready"] = not result["issues"]
    return result

if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
