#!/usr/bin/env python3
"""Read-only dependency audit for the public installer release gate.

Reports Python imports used by repository helpers and whether the current
interpreter can locate third-party modules. Never installs packages.
"""
import ast
import importlib.util
import json
import pathlib
import sys
import sysconfig

ROOT = pathlib.Path(__file__).resolve().parents[1]
STDLIB = set(sys.stdlib_module_names)
ALIASES = {"PIL": "Pillow", "yaml": "PyYAML", "psutil": "psutil",
           "requests": "requests", "cryptography": "cryptography"}

def inspect_imports(root=ROOT):
    found = {}
    errors = []
    for base in (root / "backend", root / "addons/backup-manager/helpers"):
        if not base.exists():
            errors.append("Missing source directory: " + str(base))
            continue
        for path in sorted(base.iterdir()):
            if not path.is_file() or path.name.startswith("."):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeError) as exc:
                errors.append(f"Cannot parse {path.relative_to(root)}: {type(exc).__name__}")
                continue
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                for name in names:
                    if name not in STDLIB:
                        found.setdefault(name, set()).add(str(path.relative_to(root)))
    bundled = {p.stem for base in (root / "backend", root / "addons/backup-manager/helpers") if base.is_dir() for p in base.glob("*.py") if p.is_file()}
    details = []
    for name, paths in sorted(found.items()):
        if name in bundled:
            details.append({"module": name, "classification": "bundled", "package_hint": None,
                            "importable": None, "used_by": sorted(paths)})
            continue
        # Do not execute imports during audit.
        try:
            available = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            available = False
        details.append({"module": name, "classification": "external", "package_hint": ALIASES.get(name, name),
                        "importable": available, "used_by": sorted(paths)})
    return {"read_only": True, "dependencies": details, "parse_errors": errors,
            "ready_for_public_install": False,
            "note": "Importability alone does not prove runtime compatibility or install dependencies."}

if __name__ == "__main__":
    print(json.dumps(inspect_imports(), indent=2))
