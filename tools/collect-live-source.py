#!/usr/bin/env python3
"""Review-only snapshot of installed Cockpit Minecraft Manager application code.

Default: list candidate files and hashes. --export creates a ZIP only if
the automated sensitive-content checks find no suspicious source lines.
NO Git push, service change, config export, or privilege escalation.
Review the ZIP yourself before sharing it.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import sys
import zipfile

FRONTEND = Path("/usr/local/share/cockpit/minecraft-manager")
BACKEND = Path("/usr/local/libexec")
FRONT_NAMES = {
    "app.js", "index.html", "manifest.json", "styles.css", "ui.js",
    "announcer-ui.js", "modpacks.js", "modpack-audit-ui.js",
    "modpack-backup-ui.js", "modpack-schedule-ui.js",
}
BACK_NAMES = {
    "cockpit-minecraft-helper", "cockpit-minecraft-announcements",
    "cockpit-minecraft-branding", "cockpit-minecraft-branding-v8",
    "cockpit-minecraft-curseforge-browser", "cockpit-minecraft-default-port",
    "cockpit-minecraft-join-control", "cockpit-minecraft-metrics-collector",
    "cockpit-minecraft-modpack-audit", "cockpit-minecraft-modpacks",
    "cockpit-minecraft-records", "cockpit-minecraft-resource-queue",
    "cockpit-minecraft-scheduler-v9", "minecraft-default-proxy",
    "minecraft-join-announcer", "minecraft-manual-backup",
    "mc-console-aio.py",
}
# Conservative heuristic: manual review remains mandatory.
SUSPECT = re.compile(
    r'''(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|
private[_-]?key|credential)[ ]*[:=][ ]*["'][^"']{4,}'''.replace("\n", "")
)
PRIVATE_KEY = re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")
MAX_BYTES = 2_000_000

def collect():
    found = {}
    skipped = []
    for base, names, prefix in (
        (FRONTEND, FRONT_NAMES, "cockpit/minecraft-manager"),
        (BACKEND, BACK_NAMES, "backend"),
    ):
        for name in sorted(names):
            path = base / name
            if not path.exists():
                continue
            if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
                skipped.append(f"{path}: unsafe file type")
                continue
            if path.stat().st_size > MAX_BYTES:
                skipped.append(f"{path}: exceeds size limit")
                continue
            raw = path.read_bytes()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                skipped.append(f"{path}: not UTF-8 source")
                continue
            found[f"{prefix}/{name}"] = (raw, text)
    return found, skipped

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, metavar="OUTPUT.zip",
                        help="Create a review ZIP if automated checks pass")
    args = parser.parse_args()
    found, skipped = collect()
    findings = []
    inventory = []
    for rel, (raw, text) in sorted(found.items()):
        inventory.append({"path": rel, "bytes": len(raw),
                          "sha256": hashlib.sha256(raw).hexdigest()})
        for i, line in enumerate(text.splitlines(), 1):
            if SUSPECT.search(line) or PRIVATE_KEY.search(line):
                findings.append({"file": rel, "line": i,
                                 "reason": "possible embedded credential"})
    report = {"notice": "REVIEW SOURCE FILES MANUALLY BEFORE SHARING",
              "files": inventory, "skipped": skipped,
              "possible_sensitive_lines": findings}
    print(json.dumps(report, indent=2))
    if not args.export:
        return 0
    if not found or findings or skipped:
        print("Export blocked: no files, flagged lines, or unsafe inputs. "
              "Inspect locally and resolve before sharing.", file=sys.stderr)
        return 2
    dest = args.export.expanduser().absolute()
    if dest.suffix.lower() != ".zip" or dest.exists():
        print("Choose a new output filename ending in .zip.", file=sys.stderr)
        return 2
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for rel, (raw, _) in sorted(found.items()):
            z.writestr(rel, raw)
        z.writestr("SOURCE_INVENTORY.json", json.dumps(report, indent=2))
    print(f"Created {dest}")
    print("IMPORTANT: Scan and manually inspect ZIP contents before uploading.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
