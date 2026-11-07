#!/usr/bin/env python3
"""Read-only repo-to-installed Cockpit frontend compatibility inventory.

Run with --installed pointing at the actual installed canonical module.
No files are copied, changed, or deleted. Only relative names and digests
are reported, never file contents.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[1] / "cockpit/minecraft-manager"
DEFAULT_INSTALLED = Path("/usr/local/share/cockpit/minecraft-manager")

def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def collect(directory):
    files, problems = {}, []
    if directory.is_symlink() or not directory.is_dir():
        return {}, ["Module directory unavailable or is a symlink: " + str(directory)]
    for item in directory.rglob("*"):
        rel = item.relative_to(directory).as_posix()
        try:
            mode = item.lstat().st_mode
            if stat.S_ISLNK(mode):
                problems.append("Symlink entry: " + rel)
            elif stat.S_ISDIR(mode):
                continue
            elif stat.S_ISREG(mode):
                files[rel] = hash_file(item)
            else:
                problems.append("Nonregular entry: " + rel)
        except OSError as exc:
            problems.append("Cannot inspect " + rel + ": " + type(exc).__name__)
    return files, problems

def compare(repo_dir=ROOT, installed_dir=DEFAULT_INSTALLED):
    repo_files, repo_problems = collect(Path(repo_dir))
    installed_files, installed_problems = collect(Path(installed_dir))
    common = set(repo_files) & set(installed_files)
    result = {
        "read_only": True,
        "repository_module": str(repo_dir),
        "installed_module": str(installed_dir),
        "repository_file_count": len(repo_files),
        "installed_file_count": len(installed_files),
        "installed_only": sorted(set(installed_files) - set(repo_files)),
        "repository_only": sorted(set(repo_files) - set(installed_files)),
        "different": sorted(name for name in common if repo_files[name] != installed_files[name]),
        "identical": sorted(name for name in common if repo_files[name] == installed_files[name]),
        "blockers": repo_problems + installed_problems,
        "safe_to_upgrade": False,
        "note": "Differences require human compatibility review; never delete installed-only assets automatically."
    }
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-dir", default=str(ROOT))
    parser.add_argument("--installed", default=str(DEFAULT_INSTALLED))
    args = parser.parse_args()
    print(json.dumps(compare(args.repo_dir, args.installed), indent=2))
