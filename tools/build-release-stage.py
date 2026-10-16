#!/usr/bin/env python3
"""Build a self-contained, unprivileged v1.2 release staging tree.

Never deploys to /usr, /etc or systemd. Host-specific backup configuration
and unit templates are included as data, not activated.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = {
    "cockpit": ("cockpit/minecraft-manager", "share/cockpit/minecraft-manager"),
    "backend": ("backend", "libexec"),
    "backup_helpers": ("addons/backup-manager/helpers", "libexec"),
    "backup_units_templates": ("addons/backup-manager/systemd", "templates/systemd"),
}
# The backup schedule UI is already part of the unified frontend.
REQUIRED = {
    "cockpit": ("manifest.json", "index.html", "app.js",
                "modpacks.js", "modpack-audit-ui.js", "modpack-backup-ui.js",
                "modpack-schedule-ui.js"),
    "backend": ("cockpit-minecraft-helper", "cockpit-minecraft-modpack-audit", "minecraft-default-proxy", "minecraft-join-announcer"),
    "backup_helpers": ("mc_backup_config.py", "cockpit-mc-snapshot", "cockpit-mc-schedule",
                       "cockpit-minecraft-backup", "cockpit-minecraft-backup-center"),
    "backup_units_templates": ("cockpit-mc-snapshot@.service.in",
                               "cockpit-mc-snapshot@.timer"),
}

def checksum(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def stage(repo, output):
    repo, output = Path(repo).resolve(strict=True), Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("Destination must not exist; refusing overwrite")
    if not (output.is_relative_to("/tmp") or output.is_relative_to("/var/tmp")):
        raise ValueError("Staging output must be beneath /tmp or /var/tmp")
    if any(part.is_symlink() for part in (output.parent,)):
        raise ValueError("Symlink parent refused")
    if output.is_relative_to(repo) or repo.is_relative_to(output):
        raise ValueError("Repository and staging output must be disjoint")
    inventory = []
    # Check the complete source package before creating any staging output.
    sources = []
    for label, (source_dir, destination_dir) in COMPONENTS.items():
        src_dir = repo / source_dir
        if src_dir.is_symlink() or not src_dir.is_dir():
            raise ValueError("Missing component directory: " + source_dir)
        available = {}
        for src in sorted(src_dir.iterdir()):
            if src.is_symlink() or not src.is_file() or not stat.S_ISREG(src.lstat().st_mode):
                raise ValueError("Unsafe source entry: " + str(src))
            available[src.name] = src
        missing = set(REQUIRED[label]) - set(available)
        if missing:
            raise ValueError("Missing release files: " + ", ".join(sorted(missing)))
        for name, src in available.items():
            sources.append((label, src, Path(destination_dir) / name))
    output.mkdir(mode=0o700)
    try:
        for label, src, rel in sources:
            dest = output / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            dest.chmod(0o755 if rel.parts[0] == "libexec" and rel.suffix != ".py" else 0o644)
            if checksum(src) != checksum(dest):
                raise OSError("Staging checksum mismatch")
            inventory.append({"component": label, "path": str(rel),
                              "sha256": checksum(dest), "bytes": dest.stat().st_size})
        manifest = {"format": 1, "release": "v1.2-rc", "fixture_only": True,
                    "production_apply_enabled": False, "files": inventory,
                    "notes": [
                        "Backup unit templates require host-specific validation and rendering.",
                        "No systemd units, services, timers, worlds, or host configuration were modified.",
                        "Frontend backup schedule UI is shipped within core cockpit directory.",
                    ]}
        manifest_file = output / "release-manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2) + "\n")
        return manifest
    except BaseException:
        shutil.rmtree(output)
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(ROOT))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = stage(args.repo, args.output)
    print(json.dumps({"files": len(result["files"]), "output": args.output,
                      "production_apply_enabled": False}, indent=2))

if __name__ == "__main__":
    main()
