#!/usr/bin/env python3
"""Collect a LOCAL, review-before-sharing snapshot of Cockpit frontend files.

Does not access backend/server files, credentials, worlds, service state, or
historical app.js backups. No uploads. Review source before sharing it.
"""
import argparse
from pathlib import Path
import shutil
import stat
import tempfile

NAMES = ("app.js", "index.html", "modpacks.js", "modpack-audit-ui.js",
         "modpack-backup-ui.js", "modpack-schedule-ui.js")
DEFAULT_SOURCE = Path("/usr/local/share/cockpit/minecraft-manager")

def collect(source=DEFAULT_SOURCE, output_parent=None):
    source = Path(source)
    if source.is_symlink() or not source.is_dir():
        raise ValueError("Source must be an existing nonsymlink directory")
    out = Path(tempfile.mkdtemp(prefix="mc-frontend-review-", dir=output_parent))
    out.chmod(0o700)
    copied = []
    for name in NAMES:
        src = source / name
        try:
            metadata = src.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"Unsafe source entry: {name}")
        dst = out / name
        shutil.copyfile(src, dst)
        dst.chmod(0o600)
        copied.append(name)
    (out / "REVIEW_BEFORE_SHARING.txt").write_text(
        "LOCAL FRONTEND REVIEW SNAPSHOT ONLY. No file was uploaded.\n"
        "Inspect every .js/.html file for IP addresses, hostnames, API keys,\n"
        "tokens, player identifiers, domain names, credentials, and personal\n"
        "paths before sharing. Remove or redact any secrets first.\n"
        "Only frontend assets are copied; historical backups are excluded.\n"
    )
    print("Local review directory:", out)
    print("Copied:", ", ".join(copied) if copied else "(none)")
    print("NOT uploaded. Review and redact before attaching.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output-parent", default=None)
    args = parser.parse_args()
    collect(args.source, args.output_parent)
