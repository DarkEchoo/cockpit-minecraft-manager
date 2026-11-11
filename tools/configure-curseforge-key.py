#!/usr/bin/env python3
"""Safely configure a host-local CurseForge API key; never accept it in argv.

Run: sudo python3 tools/configure-curseforge-key.py
For intentional rotation: sudo python3 tools/configure-curseforge-key.py --replace
"""
import argparse
import getpass
import os
from pathlib import Path
import stat
import sys
import tempfile

DIRECTORY = Path("/etc/cockpit-minecraft")
TARGET = DIRECTORY / "curseforge-api-key"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true",
                        help="Explicitly replace an existing key; does not print it")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Run with sudo; the key file is readable only by root.")
    if DIRECTORY.is_symlink() or (DIRECTORY.exists() and not DIRECTORY.is_dir()):
        parser.error("Unsafe configuration directory")
    if TARGET.is_symlink() or (TARGET.exists() and not TARGET.is_file()):
        parser.error("Unsafe key file")
    if TARGET.exists() and not args.replace:
        parser.error("A key is already configured; specify --replace to rotate it")
    if DIRECTORY.exists() and DIRECTORY.stat().st_mode & stat.S_IWOTH:
        parser.error("Configuration directory is world-writable; refusing")
    try:
        key = getpass.getpass("Enter your own CurseForge API key (input hidden): ")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=sys.stderr)
        return 1
    if not key or len(key) > 500 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        print("Invalid key format. No changes made.", file=sys.stderr)
        return 2
    DIRECTORY.mkdir(mode=0o750, parents=True, exist_ok=True)
    os.chown(DIRECTORY, 0, DIRECTORY.stat().st_gid)
    fd, temp_path = tempfile.mkstemp(prefix=".curseforge-api-key-", dir=DIRECTORY)
    try:
        os.fchmod(fd, 0o600)
        os.fchown(fd, 0, 0)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(key + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        # Refuse late appearance unless rotation was explicitly requested.
        if TARGET.exists() and not args.replace:
            raise RuntimeError("Key appeared during setup; refusing overwrite")
        os.replace(temp_path, TARGET)
        print("Configured root-owned CurseForge key at /etc/cockpit-minecraft/curseforge-api-key (0600).")
        print("The key was not added to source code or printed.")
        return 0
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == "__main__":
    raise SystemExit(main())
