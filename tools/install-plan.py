#!/usr/bin/env python3
"""Read-only install planner. No changes to Cockpit, services or worlds."""
import argparse
import importlib.util
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("mc_inventory", HERE / "cockpit-module-inventory.py")
inventory_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory_module)

def plan(roots, source_root):
    modules = inventory_module.inventory(roots)
    canonical = [m for m in modules if m["canonical_name"] and m["valid_manifest"]]
    noncanonical = [m for m in modules if not m["canonical_name"]]
    known = source_root / "cockpit/minecraft-manager/manifest.json"
    blockers = []
    if not known.is_file():
        blockers.append("Repository is missing the canonical Cockpit manifest")
    if len(canonical) > 1:
        blockers.append("Multiple canonical Minecraft module installations need manual selection")
    if noncanonical:
        blockers.append("Additional Minecraft-related modules require explicit manual review; no automatic cleanup")
    mode = "upgrade" if canonical else "fresh"
    if mode == "fresh":
        blockers.append("Fresh-install dependency, user, unit and permission provisioning is not implemented")
    else:
        blockers.append("Transactional backup, safe upgrade and rollback are not implemented")
    return {
        "mode": mode,
        "read_only": True,
        "install_ready": False,
        "canonical_target": canonical[0]["module_dir"] if len(canonical) == 1 else None,
        "existing_modules": modules,
        "blockers": blockers,
        "will_start_services": False,
        "will_enable_timers": False,
        "will_delete_modules": False,
        "will_modify_worlds": False,
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", action="append", help="Override scanned Cockpit root(s) for fixtures")
    p.add_argument("--source-root", default=str(HERE.parent))
    args = p.parse_args()
    result = plan(args.root or inventory_module.ROOTS, pathlib.Path(args.source_root))
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
