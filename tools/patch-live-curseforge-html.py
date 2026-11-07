#!/usr/bin/env python3
"""Produce a narrowly patched copy of an installed Cockpit HTML file.

Do not replace other markup or embedded feature panels, and never write
to the source file. Ambiguous or already partially modified markup is refused.
"""
import argparse
from pathlib import Path
import re

REQUIRED_IDS = ("mp-key", "mp-query", "mp-category", "mp-search",
                "mp-results", "mp-search-version")
SELECT_HTML = '<select id="mp-search-version"><option value="">All Minecraft versions</option></select>'
DETAIL_HTML = '<div id="mp-project-detail" class="sub-panel" hidden></div>'

def patch_html(source):
    for name in REQUIRED_IDS:
        if len(re.findall(r'\bid\s*=\s*["\']' + re.escape(name) + r'["\']', source)) != 1:
            raise ValueError("Missing or duplicated browser element: " + name)
    if '<script src="modpacks.js"></script>' not in source:
        raise ValueError("Existing Modpack frontend script not found; manual review required")
    # Refuse if the page already contains partially deployed new markup.
    if "mp-project-detail" in source:
        raise ValueError("Project detail marker already exists; review before re-applying")
    input_tag = re.compile(r'<input\b[^>]*\bid\s*=\s*["\']mp-search-version["\'][^>]*>', re.I)
    matches = list(input_tag.finditer(source))
    if len(matches) != 1:
        raise ValueError("Expected exactly one original Minecraft version input")
    source = source[:matches[0].start()] + SELECT_HTML + source[matches[0].end():]
    results = re.compile(r'<div\b[^>]*\bid\s*=\s*["\']mp-results["\'][^>]*>\s*</div>', re.I)
    matches = list(results.finditer(source))
    if len(matches) != 1:
        raise ValueError("Expected exactly one empty CurseForge results container")
    # Keep all other custom live console markup byte-for-byte unchanged.
    return source[:matches[0].end()] + DETAIL_HTML + source[matches[0].end():]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.source.is_symlink() or not args.source.is_file():
        raise ValueError("Unsafe input HTML")
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("Output exists")
    original = args.source.read_text(encoding="utf-8")
    updated = patch_html(original)
    args.output.write_text(updated, encoding="utf-8")

if __name__ == "__main__":
    main()
