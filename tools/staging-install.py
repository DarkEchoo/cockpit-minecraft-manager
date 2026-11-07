#!/usr/bin/env python3
"""Test-only staging deployment of actual repository files into disposable directories.

This is NOT a production installer. --sandbox must be an existing temporary fixture
directory explicitly marked with .mc-fixture-only. Never uses system installation paths.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("mc_tx", HERE / "transaction-fixture.py")
TX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TX)
MARKER = ".mc-fixture-only"

def deploy(repo, sandbox, fail_after=None):
    repo = Path(repo).resolve(strict=True)
    sandbox = Path(sandbox).resolve(strict=True)
    if not sandbox.is_dir() or not (sandbox / MARKER).is_file():
        raise ValueError("Refusing unmarked sandbox; create .mc-fixture-only in an isolated test directory")
    # Marked directories outside temp space must never be treated as deployment fixtures.
    if not sandbox.is_relative_to(Path("/tmp")) and not sandbox.is_relative_to(Path("/var/tmp")):
        raise ValueError("Fixtures must be inside /tmp or /var/tmp")
    front = repo / "cockpit/minecraft-manager"
    back = repo / "backend"
    if not (front / "manifest.json").is_file() or not (back / "cockpit-minecraft-helper").is_file():
        raise ValueError("Incomplete repository source")
    # Copy only the app files into sandbox staging. No privileged host paths.
    stages = sandbox / "stage"
    target = sandbox / "installed"
    if stages.exists() or target.exists():
        raise ValueError("Fresh fixture required: stage/installed already exists")
    stages.mkdir()
    target.mkdir()
    for label, original in (("frontend", front), ("backend", back)):
        staged = stages / label
        staged.mkdir()
        for item in original.iterdir():
            if item.is_symlink() or not item.is_file():
                raise ValueError("Unexpected repository item")
            shutil.copy2(item, staged / item.name)
    results = {}
    # Isolated transaction fixture is invoked separately per directory.
    # A cross-directory production transaction remains unimplemented.
    for label in ("frontend", "backend"):
        dst = target / label
        dst.mkdir()
        results[label] = TX.transact(sandbox, stages / label, dst, fail_after=fail_after)
    return {"ok": True, "fixture_only": True, "results": results,
            "production_apply_enabled": False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=str(HERE.parent))
    p.add_argument("--sandbox", required=True)
    p.add_argument("--fail-after", type=int)
    args = p.parse_args()
    print(json.dumps(deploy(args.repo, args.sandbox, args.fail_after), indent=2))

if __name__ == "__main__":
    main()
