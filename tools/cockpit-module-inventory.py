#!/usr/bin/env python3
"""Read-only Cockpit module inventory for the v1.2 installer.
Never removes modules, follows no symlinks and does not expose host secrets.
"""
import argparse
import json
import os
import pathlib

ROOTS = (
    "/usr/local/share/cockpit",
    "/usr/share/cockpit",
    "/etc/cockpit",
)
CANONICAL = "minecraft-manager"

def inventory(roots):
    result = []
    for root_text in roots:
        root = pathlib.Path(root_text)
        if not root.is_dir() or root.is_symlink():
            continue
        try:
            children = sorted(root.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_symlink() or not child.is_dir():
                continue
            manifest = child / "manifest.json"
            if manifest.is_symlink() or not manifest.is_file():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                tools = data.get("tools", {})
                if not isinstance(tools, dict):
                    tools = {}
                names = sorted(str(t) for t in tools)
                minecraft_related = (child.name == CANONICAL
                                     or "minecraft" in child.name.lower()
                                     or any("minecraft" in n.lower() for n in names))
                if not minecraft_related:
                    continue
                result.append({
                    "module_dir": str(child),
                    "manifest": str(manifest),
                    "tools": names,
                    "canonical_name": child.name == CANONICAL,
                    "valid_manifest": True,
                    "classification": "canonical-name-candidate" if child.name == CANONICAL else "review-required",
                    "safe_to_delete_automatically": False,
                })
            except (OSError, UnicodeError, ValueError) as exc:
                if "minecraft" in child.name.lower():
                    result.append({
                        "module_dir": str(child),
                        "valid_manifest": False,
                        "classification": "review-required",
                        "safe_to_delete_automatically": False,
                        "error_type": type(exc).__name__,
                    })
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--root", action="append", help="override roots for safe fixture tests; repeatable")
    args = parser.parse_args()
    entries = inventory(args.root if args.root else ROOTS)
    duplicate_names = {}
    for item in entries:
        for tool in item.get("tools", []):
            duplicate_names.setdefault(tool, []).append(item["module_dir"])
    duplicates = {name: paths for name, paths in duplicate_names.items() if len(paths) > 1}
    result = {
        "read_only": True,
        "modules": entries,
        "duplicate_tool_ids": duplicates,
        "auto_cleanup_permitted": False,
        "note": "Manifest IDs alone cannot establish that any entry is obsolete.",
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Cockpit module inventory (read-only)")
        if not entries:
            print("No matching manifests in scanned locations")
        for item in entries:
            print(f"  {item['classification']}: {item['module_dir']} / tools={','.join(item.get('tools', []))}")
        for key, paths in duplicates.items():
            print(f"  DUPLICATE tool id {key}: {len(paths)} manifests")
        print("No modules were modified. Deletion is not authorized.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
