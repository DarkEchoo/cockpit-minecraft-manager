#!/usr/bin/env python3
"""Fixture-only interruption recovery prototype. NEVER runs against production paths.

Prepares a durable journal and originals before replacement. A separate
recover invocation uses those originals even after the writer exits. This
does not yet guarantee power-loss atomicity across a filesystem.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

MARKER = ".mc-fixture-only"
JOURNAL = ".mc-recovery-journal"

def checked(root):
    p = Path(root).absolute()
    if not (p.is_relative_to("/tmp") or p.is_relative_to("/var/tmp")):
        raise ValueError("Fixture must be under /tmp or /var/tmp")
    if p.is_symlink() or not p.is_dir() or not (p / MARKER).is_file():
        raise ValueError("Missing valid fixture marker")
    return p

def ensure_regular(p):
    st = p.lstat()
    if not stat.S_ISREG(st.st_mode):
        raise ValueError("Unsafe file type: " + str(p))

def fsync_dir(p):
    fd = os.open(p, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def atomic_json(path, obj):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "x", encoding="utf8") as f:
        json.dump(obj, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fsync_dir(path.parent)

def prepare(root):
    root = checked(root)
    src, dst = root / "source", root / "installed"
    if any(x.is_symlink() for x in (src, dst)) or not src.is_dir() or not dst.is_dir():
        raise ValueError("Source and destination fixture dirs required")
    txn = root / JOURNAL
    if txn.exists() or txn.is_symlink():
        raise ValueError("Outstanding transaction: recover first")
    names = sorted(x.name for x in src.iterdir())
    if not names:
        raise ValueError("Source fixture empty")
    for name in names:
        if "/" in name or name in (".", ".."): raise ValueError("Invalid name")
        ensure_regular(src / name)
        target = dst / name
        if target.exists() or target.is_symlink(): ensure_regular(target)
    txn.mkdir(mode=0o700)
    backups = txn / "backups"
    backups.mkdir(mode=0o700)
    staged = txn / "staged"
    staged.mkdir(mode=0o700)
    entries = []
    for n, name in enumerate(names):
        target = dst / name
        prior = target.exists()
        if prior:
            shutil.copy2(target, backups / str(n))
            with open(backups / str(n), "rb") as f: os.fsync(f.fileno())
        shutil.copy2(src / name, staged / str(n))
        with open(staged / str(n), "rb") as f: os.fsync(f.fileno())
        entries.append({"name": name, "id": n, "existed": prior})
    fsync_dir(backups)
    fsync_dir(staged)
    atomic_json(txn / "manifest.json", {"format": 1, "entries": entries, "state": "prepared"})
    fsync_dir(txn)
    return len(entries)

def apply_partial(root, count):
    root = checked(root)
    txn = root / JOURNAL
    m = json.loads((txn / "manifest.json").read_text())
    if m["state"] != "prepared": raise ValueError("Fixture transaction not prepared")
    entries = m["entries"]
    if count < 1 or count > len(entries): raise ValueError("Invalid operation count")
    for entry in entries[:count]:
        target = root / "installed" / entry["name"]
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError("Unsafe target")
        # Recovery manifest and backup already persisted before writes.
        os.replace(txn / "staged" / str(entry["id"]), target)
        fsync_dir(target.parent)
    return count

def recover(root):
    root = checked(root)
    txn = root / JOURNAL
    if txn.is_symlink() or not txn.is_dir(): raise ValueError("No transaction to recover")
    m = json.loads((txn / "manifest.json").read_text())
    if m.get("format") != 1 or m.get("state") != "prepared": raise ValueError("Invalid journal")
    entries = m.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Invalid journal entries")
    seen_names, seen_ids = set(), set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Invalid journal entry")
        name, number, existed = entry.get("name"), entry.get("id"), entry.get("existed")
        if (not isinstance(name, str) or not name or
                Path(name).name != name or name in (".", "..") or
                name in seen_names):
            raise ValueError("Invalid or duplicate journal name")
        if type(number) is not int or number < 0 or number in seen_ids:
            raise ValueError("Invalid or duplicate journal ID")
        if type(existed) is not bool:
            raise ValueError("Invalid journal prior-state flag")
        seen_names.add(name)
        seen_ids.add(number)
        target = root / "installed" / name
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError("Unsafe recovery target")
        if entry["existed"]:
            prior = txn / "backups" / str(entry["id"])
            if not prior.is_file() or prior.is_symlink(): raise ValueError("Missing recovery backup")
    for entry in reversed(entries):
        target = root / "installed" / entry["name"]
        if entry["existed"]:
            prior = txn / "backups" / str(entry["id"])
            # Keep the original backup intact until ALL recovery steps finish.
            # A subsequent recover() can replay an interrupted restore.
            temp = target.with_name(".mc-restore-" + str(entry["id"]) + ".tmp")
            if temp.is_symlink() or temp.exists():
                raise ValueError("Unexpected restoration temporary path")
            shutil.copy2(prior, temp)
            with open(temp, "rb") as handle:
                os.fsync(handle.fileno())
            os.replace(temp, target)
        elif target.exists():
            target.unlink()
        fsync_dir(target.parent)
    shutil.rmtree(txn)
    fsync_dir(root)
    return len(entries)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("prepare", "apply-partial", "recover"))
    p.add_argument("--sandbox", required=True)
    p.add_argument("--count", type=int)
    args = p.parse_args()
    out = (prepare(args.sandbox) if args.action == "prepare" else
           apply_partial(args.sandbox, args.count) if args.action == "apply-partial" and args.count is not None else
           recover(args.sandbox) if args.action == "recover" else None)
    if out is None: p.error("--count required")
    print(json.dumps({"action": args.action, "files": out, "fixture_only": True}))

if __name__ == "__main__":
    main()
