#!/usr/bin/env python3
"""Transactional Cockpit Minecraft Manager deployment.

Files only: never alters Minecraft worlds, configuration, services or timers.
All targets are fixed. An interrupted transaction must be recovered before retry.
Production use must be invoked by the outer, gated installer.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys

PROJECT = Path(__file__).resolve().parents[1]
PARTS = (("cockpit/minecraft-manager", "usr/local/share/cockpit/minecraft-manager"),
         ("backend", "usr/local/libexec"),
         ("addons/backup-manager/helpers", "usr/local/libexec"))
PRESERVE_EXISTING = frozenset((
    "minecraft-default-proxy", "minecraft-join-announcer", "minecraft-manual-backup",
    # Host compatibility review: live versions contain fixes/features not yet merged.
    "app.js", "cockpit-minecraft-helper", "cockpit-minecraft-join-control",
    "cockpit-minecraft-modpacks", "cockpit-minecraft-records",
))
TRANSACTION = "var/lib/cockpit-minecraft-manager/installer/pending"
STATE = "journal.json"

def checksum(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            sha.update(block)
    return sha.hexdigest()

def syncdir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def guarded_path(prefix, relative):
    if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Unsafe relative path")
    target = prefix / relative
    current = target
    while current != prefix:
        if current.is_symlink():
            raise ValueError("Symlink path refused: " + str(current))
        current = current.parent
    return target

def regular_or_missing(path):
    if path.exists() and not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("Unsafe target type: " + str(path))

def inventory(repo, prefix):
    records = []
    found = set()
    for source, target_dir in PARTS:
        source_dir = guarded_path(repo, source)
        if not source_dir.is_dir() or source_dir.is_symlink():
            raise ValueError("Missing safe package component " + source)
        for path in sorted(source_dir.iterdir()):
            if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.lstat().st_mode):
                raise ValueError("Invalid package file: " + str(path))
            relative = str(Path(target_dir) / path.name)
            if relative in found:
                raise ValueError("Duplicate destination: " + relative)
            found.add(relative)
            dest = guarded_path(prefix, relative)
            regular_or_missing(dest)
            if path.name in PRESERVE_EXISTING and dest.exists():
                # These helpers can contain host-specific behavior. Never replace live copies.
                continue
            old = dest.stat() if dest.exists() else None
            records.append({"path": relative, "source": str(path.relative_to(repo)),
                            "new_hash": checksum(path),
                            "old_hash": checksum(dest) if old else None,
                            "mode": stat.S_IMODE(old.st_mode) if old else None,
                            "uid": old.st_uid if old else None,
                            "gid": old.st_gid if old else None})
    if not records or not any(r["path"].endswith("/manifest.json") for r in records):
        raise ValueError("Incomplete frontend package")
    return records

def write_json(path, data):
    new = path.with_name(path.name + ".part")
    with new.open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(new, path)
    syncdir(path.parent)

def prepare(repo, prefix):
    tx = guarded_path(prefix, TRANSACTION)
    if tx.exists():
        raise ValueError("Outstanding install transaction; recover/finalize it first")
    records = inventory(repo, prefix)
    tx.mkdir(mode=0o700, parents=True)
    backups = tx / "backups"
    backups.mkdir(mode=0o700)
    try:
        for entry in records:
            if entry["old_hash"] is None:
                continue
            source = guarded_path(prefix, entry["path"])
            dest = guarded_path(backups, entry["path"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            with dest.open("rb") as stream: os.fsync(stream.fileno())
            if checksum(dest) != entry["old_hash"]:
                raise OSError("Backed-up file changed")
        for parent, _, _ in os.walk(backups):
            syncdir(Path(parent))
        write_json(tx / STATE, {"version": 1, "state": "prepared", "files": records})
    except BaseException:
        # A partially prepared transaction is retained and must be investigated.
        raise
    return records

def load(prefix):
    tx = guarded_path(prefix, TRANSACTION)
    file = guarded_path(tx, STATE)
    if not file.is_file() or file.is_symlink():
        raise ValueError("No complete transaction journal; do not delete backups")
    data = json.loads(file.read_text())
    if data.get("version") != 1 or data.get("state") != "prepared":
        raise ValueError("Unexpected transaction journal state")
    records = data.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("Empty transaction journal")
    seen = set()
    for entry in records:
        name = entry["path"]
        if name in seen or not any(name.startswith(t + "/") for _, t in PARTS):
            raise ValueError("Unexpected journal target")
        seen.add(name)
        guarded_path(prefix, name)
        if entry["old_hash"] is not None:
            backup = guarded_path(tx / "backups", name)
            if not backup.is_file() or backup.is_symlink() or checksum(backup) != entry["old_hash"]:
                raise ValueError("Backup missing or damaged: " + name)
    return tx, records

def apply(repo, prefix):
    records = prepare(repo, prefix)
    tx = guarded_path(prefix, TRANSACTION)
    try:
        for number, entry in enumerate(records):
            dest = guarded_path(prefix, entry["path"])
            src = guarded_path(repo, entry["source"])
            if checksum(src) != entry["new_hash"]:
                raise ValueError("Package source changed")
            if entry["old_hash"] is not None and (not dest.is_file() or checksum(dest) != entry["old_hash"]):
                raise ValueError("Target changed since preflight: " + entry["path"])
            if entry["old_hash"] is None and dest.exists():
                raise ValueError("New destination appeared: " + entry["path"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(".mc-install-" + str(number))
            if tmp.exists() or tmp.is_symlink():
                raise ValueError("Temporary install path occupied")
            shutil.copyfile(src, tmp)
            mode = entry["mode"] if entry["mode"] is not None else (0o755 if dest.parent == prefix / "usr/local/libexec" and src.suffix != ".py" else 0o644)
            os.chmod(tmp, mode)
            if os.geteuid() == 0:
                os.chown(tmp, entry["uid"] if entry["uid"] is not None else 0,
                         entry["gid"] if entry["gid"] is not None else 0)
            with tmp.open("rb") as stream: os.fsync(stream.fileno())
            os.replace(tmp, dest)
            syncdir(dest.parent)
            if checksum(dest) != entry["new_hash"]:
                raise OSError("Post-install checksum mismatch")
        return {"applied": len(records), "rollback_available": str(tx)}
    except Exception:
        # Keep the journal for explicit recovery; never discard backup on failure.
        raise

def recover(prefix):
    tx, records = load(prefix)
    # Validate all destinations before modifying any file.
    for entry in records:
        path = guarded_path(prefix, entry["path"])
        regular_or_missing(path)
        if path.exists() and checksum(path) not in (entry["old_hash"], entry["new_hash"]):
            raise ValueError("Target modified independently; manual intervention needed: " + entry["path"])
    for number, entry in enumerate(reversed(records)):
        dest = guarded_path(prefix, entry["path"])
        if entry["old_hash"] is None:
            dest.unlink(missing_ok=True)
            if dest.parent.is_dir(): syncdir(dest.parent)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            temp = dest.with_name(".mc-recover-" + str(number))
            if temp.is_symlink() or temp.exists():
                raise ValueError("Recovery temp occupied")
            shutil.copyfile(tx / "backups" / entry["path"], temp)
            os.chmod(temp, entry["mode"])
            if os.geteuid() == 0: os.chown(temp, entry["uid"], entry["gid"])
            with temp.open("rb") as stream: os.fsync(stream.fileno())
            os.replace(temp, dest)
            syncdir(dest.parent)
    for number, entry in enumerate(records):
        dest = guarded_path(prefix, entry["path"])
        install_temp = dest.with_name(".mc-install-" + str(number))
        if install_temp.exists() or install_temp.is_symlink():
            if install_temp.is_symlink() or not install_temp.is_file():
                raise ValueError("Unsafe leftover install staging path")
            install_temp.unlink()
    shutil.rmtree(tx)
    syncdir(tx.parent)
    return {"restored": len(records)}

def finalize(prefix):
    tx, records = load(prefix)
    for entry in records:
        path = guarded_path(prefix, entry["path"])
        if not path.is_file() or checksum(path) != entry["new_hash"]:
            raise ValueError("Cannot finalize inconsistent install: " + entry["path"])
    shutil.rmtree(tx)
    syncdir(tx.parent)
    return {"finalized": len(records)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("apply", "recover", "finalize", "inventory"))
    parser.add_argument("--repo", default=str(PROJECT))
    parser.add_argument("--root", default="/")
    parser.add_argument("--fixture-only", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve(strict=True)
    if args.fixture_only:
        if root == Path("/") or not root.is_relative_to("/tmp/") or not (root / ".mc-fixture-only").is_file():
            raise SystemExit("Fixture marker and nested /tmp directory required")
    elif root != Path("/") or os.geteuid() != 0:
        raise SystemExit("Production transactions require root and filesystem /")
    repo = Path(args.repo).resolve(strict=True)
    result = {"inventory":lambda:inventory(repo,root),"apply":lambda:apply(repo,root),
              "recover":lambda:recover(root),"finalize":lambda:finalize(root)}[args.action]()
    print(json.dumps(result,indent=2))
if __name__ == "__main__":
    main()
