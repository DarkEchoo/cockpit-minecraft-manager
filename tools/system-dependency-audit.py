#!/usr/bin/env python3
"""Read-only Linux executable inventory for v1.2 preflight. No installs."""
import json
import shutil
import subprocess

REQUIRED = ("python3", "systemctl", "findmnt", "tar", "sha256sum", "bash")
OPTIONAL = ("java", "cockpit-bridge", "restic", "node", "git", "rsync", "unzip")

def audit(which=shutil.which):
    def record(name, required):
        path = which(name)
        return {"command": name, "required_for_preflight": required,
                "available": path is not None, "path": path}
    checks = [record(c, True) for c in REQUIRED] + [record(c, False) for c in OPTIONAL]
    return {"read_only": True, "checks": checks,
            "missing_required": [r["command"] for r in checks if r["required_for_preflight"] and not r["available"]],
            "install_ready": False,
            "note": "Executable presence does not validate versions, privileges, packages, services or runtime compatibility."}

if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
