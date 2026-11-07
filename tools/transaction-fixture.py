#!/usr/bin/env python3
"""v1.2 transactional file copier — fixture-only development harness.

This program intentionally refuses production paths. It supports isolated
test fixtures under a caller-provided sandbox, not live upgrades.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"Not a regular file: {path}")
    return info


def transact(sandbox, source, destination, fail_after=None):
    sandbox = Path(sandbox).resolve(strict=True)
    source = Path(source).absolute()
    destination = Path(destination).absolute()
    # Never allow the sandbox to be '/', and refuse symlink components.
    if sandbox == Path("/") or sandbox.is_symlink():
        raise ValueError("Unsafe sandbox")
    for p in (source, destination):
        if not p.is_relative_to(sandbox) or p == sandbox:
            raise ValueError("All fixture paths must be beneath the sandbox")
        q = p
        while q != sandbox:
            if q.is_symlink():
                raise ValueError(f"Symlink component refused: {q}")
            q = q.parent
    if source == destination or destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("Source and destination must be disjoint")
    if not source.is_dir() or not destination.is_dir():
        raise ValueError("Existing fixture directories required")
    inputs = sorted(source.iterdir())
    if not inputs:
        raise ValueError("Empty source fixture")
    for file in inputs:
        regular(file)
        target = destination / file.name
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError(f"Unsafe target: {target}")
        if target.exists():
            regular(target)
    # A temporary transaction root is on the same filesystem as the sandbox.
    tx = Path(tempfile.mkdtemp(prefix=".mc-tx-", dir=sandbox))
    backups = tx / "previous"
    backups.mkdir()
    journal = []
    staged = []
    preserve_recovery = False
    try:
        # Stage all file data and original copies BEFORE touching destinations.
        for index, file in enumerate(inputs):
            target = destination / file.name
            stage = tx / f"new-{index}"
            shutil.copy2(file, stage)
            if digest(stage) != digest(file):
                raise IOError("Staged source checksum mismatch")
            if target.exists():
                previous = backups / f"old-{index}"
                shutil.copy2(target, previous)
                if digest(previous) != digest(target):
                    raise IOError("Original backup checksum mismatch")
            else:
                previous = None
            staged.append((stage, target, previous))
        for index, (stage, target, previous) in enumerate(staged):
            os.replace(stage, target)
            journal.append((target, previous))
            if fail_after is not None and len(journal) >= fail_after:
                raise RuntimeError("Injected transaction failure")
        return {"ok": True, "installed": len(journal), "rolled_back": False}
    except Exception:
        failures = []
        for target, previous in reversed(journal):
            try:
                if previous is None:
                    target.unlink()
                else:
                    os.replace(previous, target)
            except OSError as error:
                failures.append(f"{target}: {error}")
        if failures:
            # Preserve tx backups for manual recovery; never discard them.
            preserve_recovery = True
            raise RuntimeError("Rollback incomplete; recovery material at "
                               + str(tx) + ": " + "; ".join(failures))
        raise
    finally:
        # Keep recovery files if any rollback operation failed.
        if not preserve_recovery:
            shutil.rmtree(tx, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sandbox", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--fail-after", type=int)
    args = parser.parse_args()
    if args.fail_after is not None and args.fail_after < 1:
        parser.error("--fail-after must be >= 1")
    print(json.dumps(transact(args.sandbox, args.source, args.destination, args.fail_after), indent=2))


if __name__ == "__main__":
    main()
