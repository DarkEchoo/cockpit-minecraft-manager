#!/usr/bin/env python3
"""Persistent cross-component transaction engine, restricted to disposable fixtures.

Transaction backups remain on disk until explicit finalize. On interrupted
installation run 'recover'. Production path support is intentionally absent.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

JOURNAL = ".mc-install-transaction"
MARKER = ".mc-fixture-only"

def syncdir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(1048576), b""):
            h.update(data)
    return h.hexdigest()

def safe_root(sandbox):
    root = Path(sandbox).resolve(strict=True)
    if root == Path("/tmp") or root == Path("/var/tmp") or not (root.is_relative_to("/tmp/") or root.is_relative_to("/var/tmp/")):
        raise ValueError("Requires a nested disposable /tmp or /var/tmp fixture")
    if not (root / MARKER).is_file() or (root / MARKER).is_symlink():
        raise ValueError("Missing fixture marker")
    return root

def verify_target(root, rel):
    if not isinstance(rel, str) or not rel or any(x in ("", ".", "..") for x in rel.split("/")) or rel.startswith("/"):
        raise ValueError("Invalid relative target")
    target = root / "installed" / rel
    cur = target
    while cur != root:
        if cur.is_symlink():
            raise ValueError("Symlink target path refused")
        cur = cur.parent
    if target.exists() and not stat.S_ISREG(target.lstat().st_mode):
        raise ValueError("Nonregular target")
    return target

def save_json(path, obj):
    temp = path.with_name(path.name + ".new")
    with temp.open("x") as f:
        json.dump(obj, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)
    syncdir(path.parent)

def prepare(root):
    root = safe_root(root)
    tx = root / JOURNAL
    if tx.exists() or tx.is_symlink():
        raise ValueError("Existing transaction: recover or finalize first")
    stage = root / "release-stage"
    source_manifest = json.loads((stage / "release-manifest.json").read_text())
    files = source_manifest["files"]
    if not files or not isinstance(files, list):
        raise ValueError("Empty manifest")
    entries, seen = [], set()
    for record in files:
        rel = record["path"]
        if rel in seen: raise ValueError("Duplicate destination")
        seen.add(rel)
        target = verify_target(root, rel)
        src = stage / rel
        if src.is_symlink() or not src.is_file() or digest(src) != record["sha256"]:
            raise ValueError("Invalid staged source checksum")
        entries.append({"path": rel, "before": digest(target) if target.exists() else None,
                        "after": record["sha256"]})
    tx.mkdir(mode=0o700)
    backup = tx / "backups"
    backup.mkdir()
    for entry in entries:
        if entry["before"]:
            original = verify_target(root, entry["path"])
            saved = backup / entry["path"]
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, saved)
            with saved.open("rb") as f: os.fsync(f.fileno())
            if digest(saved) != entry["before"]: raise OSError("Backup checksum mismatch")
    for directory, dirs, filenames in os.walk(backup):
        syncdir(directory)
    save_json(tx / "manifest.json", {"version": 1, "state": "prepared", "files": entries})
    syncdir(tx)
    return len(entries)

def read_transaction(root):
    tx = root / JOURNAL
    if tx.is_symlink() or not tx.is_dir(): raise ValueError("No transaction journal")
    doc = json.loads((tx / "manifest.json").read_text())
    if doc.get("version") != 1 or doc.get("state") != "prepared" or not isinstance(doc.get("files"), list):
        raise ValueError("Invalid transaction state")
    entries = doc["files"]
    seen = set()
    for entry in entries:
        rel = entry.get("path")
        if rel in seen: raise ValueError("Duplicate transaction path")
        seen.add(rel)
        verify_target(root, rel)
        before = entry.get("before")
        after = entry.get("after")
        for checksum in (before, after):
            if checksum is not None and (not isinstance(checksum, str) or len(checksum)!=64 or any(c not in "0123456789abcdef" for c in checksum)):
                raise ValueError("Bad checksum")
        if before:
            saved = tx / "backups" / rel
            if saved.is_symlink() or not saved.is_file() or digest(saved) != before:
                raise ValueError("Missing or damaged backup")
    return tx, entries

def apply(root, fail_after=None):
    root = safe_root(root)
    tx, entries = read_transaction(root)
    # Refuse second apply after any staged replacement; recovery must be explicit.
    for entry in entries:
        dest = verify_target(root, entry["path"])
        if dest.exists() and digest(dest) == entry["after"] and entry["after"] != entry["before"]:
            raise ValueError("Possible partial apply: run recover first")
    for index, entry in enumerate(entries, 1):
        src = root / "release-stage" / entry["path"]
        if src.is_symlink() or digest(src) != entry["after"]:
            raise ValueError("Staged file changed")
        dst = verify_target(root, entry["path"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Copy to temporary sibling, then atomically replace individual file.
        temp = dst.with_name(".mc-stage-" + str(index))
        if temp.exists() or temp.is_symlink(): raise ValueError("Temp path conflict")
        shutil.copy2(src, temp)
        with temp.open("rb") as handle: os.fsync(handle.fileno())
        os.replace(temp, dst)
        syncdir(dst.parent)
        if fail_after == index:
            raise RuntimeError("Simulated interruption")
    return len(entries)

def recover(root):
    root = safe_root(root)
    tx, entries = read_transaction(root)
    # Backups are kept intact for repeatable recovery; no unrelated assets touched.
    for index, entry in enumerate(reversed(entries), 1):
        dst = verify_target(root, entry["path"])
        temp = dst.with_name(".mc-recover-" + str(index))
        if temp.exists() or temp.is_symlink():
            temp.unlink() if temp.is_file() and not temp.is_symlink() else (_ for _ in ()).throw(ValueError("Unsafe recovery temp"))
        if entry["before"] is None:
            dst.unlink(missing_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tx / "backups" / entry["path"], temp)
            with temp.open("rb") as f: os.fsync(f.fileno())
            os.replace(temp, dst)
        syncdir(dst.parent)
    shutil.rmtree(tx)
    syncdir(root)
    return len(entries)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("prepare","apply","recover"))
    p.add_argument("--sandbox", required=True)
    p.add_argument("--fail-after", type=int)
    a=p.parse_args()
    result={"prepare":prepare,"apply":lambda root:apply(root,a.fail_after),"recover":recover}[a.action](a.sandbox)
    print(json.dumps({"fixture_only":True,"action":a.action,"files":result}))
if __name__=="__main__":main()
