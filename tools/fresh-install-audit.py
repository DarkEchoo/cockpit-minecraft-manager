#!/usr/bin/env python3
"""Read-only readiness audit for a fresh Ubuntu Cockpit installation.

This is deliberately stricter than the existing file-only upgrade preflight:
a green package validation alone does NOT mean a clean host is supported.
No passwords, tokens, server data, or host files are copied.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "install.sh",
    "cockpit/minecraft-manager/manifest.json",
    "cockpit/minecraft-manager/index.html",
    "cockpit/minecraft-manager/app.js",
    "backend/cockpit-minecraft-helper",
    "tools/production-transaction.py",
]
TOOLS = ["python3", "bash", "systemctl", "flock", "tar", "sha256sum"]
# A clean install must provision these capabilities before claiming readiness.
UNIMPLEMENTED = [
    "Create and constrain a dedicated minecraft system account/group",
    "Install and validate an appropriately scoped privileged-helper authorization policy",
    "Generate per-host configuration and secure credential storage without hard-coded paths",
    "Install required systemd units from reviewed, host-independent templates",
    "Configure supported game-server storage and permissions without touching existing worlds",
    "Validate feature-specific dependencies and disable unavailable optional features",
    "Run fresh-host install, exercise Cockpit controls, and verify uninstall/rollback in a disposable Ubuntu VM",
]

def command_ok(*args):
    try:
        result = subprocess.run(args, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=8, check=False)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False

def audit(repo, host):
    checks = []
    for rel in REQUIRED:
        item = repo / rel
        checks.append({"name": "package:" + rel, "ok": item.is_file() and not item.is_symlink()})
    for tool in TOOLS:
        checks.append({"name": "tool:" + tool, "ok": shutil.which(tool) is not None})
    if host:
        is_ubuntu = Path("/etc/os-release").exists() and (
            "ubuntu" in Path("/etc/os-release").read_text(errors="replace").lower())
        checks.append({"name": "host:Ubuntu", "ok": is_ubuntu})
        checks.append({"name": "host:Cockpit installed",
                       "ok": shutil.which("cockpit-bridge") is not None})
        checks.append({"name": "host:cockpit.socket active",
                       "ok": command_ok("systemctl", "is-active", "--quiet", "cockpit.socket")})
        checks.append({"name": "host:privileged helper location available",
                       "ok": Path("/usr/local/libexec").is_dir()})
    return {
        "mode": "read-only fresh-host readiness audit",
        "package_checks": checks,
        "checks_pass": all(c["ok"] for c in checks),
        "fresh_install_supported": False,
        "unimplemented_requirements": UNIMPLEMENTED,
        "note": ("Passing file and host checks does not make this a general-purpose "
                 "installer; --apply currently installs app files only."),
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=ROOT)
    p.add_argument("--host", action="store_true", help="Inspect local host; no changes")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    report = audit(a.repo.resolve(), a.host)
    if a.json:
        print(json.dumps(report, indent=2))
    else:
        print("Cockpit Minecraft Manager: fresh-install readiness (read-only)")
        for check in report["package_checks"]:
            print(("PASS" if check["ok"] else "FAIL") + "  " + check["name"])
        print("\nNOT READY for general fresh installation. Missing:")
        for i, item in enumerate(report["unimplemented_requirements"], 1):
            print(f"  {i}. {item}")
        print("\nExisting --apply mode is a file-only transaction, not full setup.")
    # Exit 2 explicitly means incomplete fresh-install support even if file checks pass.
    raise SystemExit(2 if report["checks_pass"] else 1)

if __name__ == "__main__":
    main()
