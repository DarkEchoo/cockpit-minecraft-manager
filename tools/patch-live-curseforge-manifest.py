#!/usr/bin/env python3
"""Create a minimally modified Cockpit package manifest enabling approved images."""
import argparse
import json
from pathlib import Path

MEDIA_HOSTS = (
    "https://media.forgecdn.net",
    "https://mediafilez.forgecdn.net",
    "https://edge.forgecdn.net",
    "https://media.curseforge.com",
    "https://static-cdn.jtvnw.net",
)

def patch_manifest(raw):
    data=json.loads(raw)
    if not isinstance(data,dict):
        raise ValueError("Cockpit manifest must be an object")
    csp=data.get("content-security-policy","")
    if csp and not isinstance(csp,str):
        raise ValueError("Unexpected Cockpit CSP type")
    parts=[p.strip() for p in csp.split(';') if p.strip()]
    image_directives=[p for p in parts if p.split()[0]=='img-src']
    if image_directives:
        # Never override an existing custom image restriction automatically.
        # It might be the administrator's deliberate security boundary.
        if len(image_directives)!=1 or any(host not in image_directives[0].split() for host in MEDIA_HOSTS):
            raise ValueError("Existing custom img-src policy; manual review required")
    else:
        parts.append("img-src 'self' "+' '.join(MEDIA_HOSTS))
    data["content-security-policy"]='; '.join(parts)+';'
    return json.dumps(data,indent=2,ensure_ascii=False)+'\n'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    if args.source.is_symlink() or not args.source.is_file():
        raise ValueError('Unsafe or missing manifest')
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Output file already exists')
    args.output.write_text(patch_manifest(args.source.read_text(encoding='utf-8')),encoding='utf-8')

if __name__=='__main__':
    main()
