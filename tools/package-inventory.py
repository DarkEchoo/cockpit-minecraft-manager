#!/usr/bin/env python3
"""Read-only packaging audit: inventory all components of v1.2.

Inventory is not an installation authorization; destinations for addon assets
must be decided and tested before any production file replacement.
"""
import json
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {
    "core_frontend": "cockpit/minecraft-manager",
    "core_backend": "backend",
    "backup_frontend": "addons/backup-manager/cockpit",
    "backup_helpers": "addons/backup-manager/helpers",
    "backup_units": "addons/backup-manager/systemd",
}

def inventory(root=ROOT):
    root = Path(root)
    packages = {}
    problems = []
    for group, relative in GROUPS.items():
        directory = root / relative
        entries = []
        if directory.is_symlink() or not directory.is_dir():
            problems.append(f"Missing or unsafe component directory: {relative}")
            packages[group] = []
            continue
        for item in sorted(directory.iterdir()):
            if item.is_symlink() or not item.is_file() or not stat.S_ISREG(item.lstat().st_mode):
                problems.append(f"Unsafe package entry: {item.relative_to(root)}")
                continue
            entries.append(str(item.relative_to(root)))
        if not entries:
            problems.append(f"Empty package component: {relative}")
        packages[group] = entries
    backup_import = root / "addons/backup-manager/helpers/mc_backup_config.py"
    if not backup_import.is_file():
        problems.append("Backup helper dependency mc_backup_config.py missing")
    return {
        "read_only": True,
        "packages": packages,
        "file_count": sum(len(files) for files in packages.values()),
        "blockers": problems,
        "safe_to_install": False,
        "warning": "Repository inclusion does not prove installed UI compatibility, dependencies, unit safety, or ownership.",
    }

if __name__ == "__main__":
    print(json.dumps(inventory(), indent=2))
