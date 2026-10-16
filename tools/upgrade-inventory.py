#!/usr/bin/env python3
"""Read-only transactional-upgrade inventory for Cockpit Minecraft Manager v1.2.

Reports exact application files that a future installer could back up/replace.
Never reads file contents, copies, modifies, deletes, or starts services.
"""
import argparse
import json
import pathlib
import stat

FRONTEND = pathlib.Path("cockpit/minecraft-manager")
BACKEND = pathlib.Path("backend")
TARGET_FRONTEND = pathlib.Path("/usr/local/share/cockpit/minecraft-manager")
TARGET_BACKEND = pathlib.Path("/usr/local/libexec")

def build_plan(source, frontend_target=TARGET_FRONTEND, backend_target=TARGET_BACKEND):
    candidates = []
    blockers = []
    for src_dir, dst_dir in ((source / FRONTEND, frontend_target),
                             (source / BACKEND, backend_target)):
        if not src_dir.is_dir() or src_dir.is_symlink():
            blockers.append(f"Source directory missing or symlink: {src_dir}")
            continue
        if dst_dir.is_symlink():
            blockers.append(f"Destination directory is symlink: {dst_dir}")
            continue
        for src in sorted(src_dir.iterdir()):
            if not src.is_file() or src.is_symlink():
                blockers.append(f"Unexpected source item (not regular file): {src}")
                continue
            dst = dst_dir / src.name
            if dst.is_symlink() or (dst.exists() and not dst.is_file()):
                blockers.append(f"Unsafe destination type: {dst}")
                continue
            candidates.append({
                "source": str(src),
                "destination": str(dst),
                "action": "replace-existing-file" if dst.exists() else "install-new-file",
                "backup_existing": dst.exists(),
                "source_bytes": src.stat().st_size,
            })
    return {
        "read_only": True,
        "mode": "proposed-upgrade",
        "safe_to_apply": False,
        "files": candidates,
        "blockers": blockers + [
            "Transactional apply/rollback and dependency verification are not yet implemented"
        ],
        "excluded_from_install": [
            "worlds and managed server directories", "systemd service state",
            "existing config and secrets", "backup archives", "existing timers",
        ],
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=pathlib.Path,
                        default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument("--frontend-target", type=pathlib.Path, default=TARGET_FRONTEND)
    parser.add_argument("--backend-target", type=pathlib.Path, default=TARGET_BACKEND)
    args = parser.parse_args()
    print(json.dumps(build_plan(args.source_root, args.frontend_target,
                                args.backend_target), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
