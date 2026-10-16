#!/usr/bin/env python3
"""Read-only unified installer destination/ownership plan.

No paths are written. Per-host backup configuration is intentionally excluded.
"""
import argparse
import json
from pathlib import Path
import stat

ROOT=Path(__file__).resolve().parents[1]
GROUPS={
 "frontend":("cockpit/minecraft-manager","/usr/local/share/cockpit/minecraft-manager"),
 "core_helpers":("backend","/usr/local/libexec"),
 "backup_helpers":("addons/backup-manager/helpers","/usr/local/libexec"),
}
CONFIG="/etc/cockpit-minecraft/backup-manager.json"
UNIT_FILES=("cockpit-mc-snapshot@.service","cockpit-mc-snapshot@.timer")

def plan(root=ROOT, frontend="/usr/local/share/cockpit/minecraft-manager", libexec="/usr/local/libexec"):
 root=Path(root)
 destinations={"frontend":Path(frontend),"core_helpers":Path(libexec),"backup_helpers":Path(libexec)}
 files=[]
 blockers=[]
 for group,(relative,_) in GROUPS.items():
  srcdir=root/relative
  if not srcdir.is_dir() or srcdir.is_symlink():
   blockers.append("Missing or unsafe source directory: "+relative);continue
  for src in sorted(srcdir.iterdir()):
   if src.is_symlink() or not src.is_file():
    blockers.append("Unsafe source file: "+str(src));continue
   target=destinations[group]/src.name
   action="create"
   try:
    meta=target.lstat()
   except FileNotFoundError:
    pass
   except OSError as exc:
    blockers.append("Unable to inspect target "+str(target)+": "+str(exc));continue
   else:
    if not stat.S_ISREG(meta.st_mode):
     blockers.append("Unsafe existing target: "+str(target));continue
    action="replace-with-backup"
   files.append({"component":group,"source":str(src.relative_to(root)),
                 "destination":str(target),"operation":action})
 duplicate_destinations=set()
 seen=set()
 for item in files:
  if item["destination"] in seen:duplicate_destinations.add(item["destination"])
  seen.add(item["destination"])
 if duplicate_destinations:
  blockers.append("Conflicting package destinations: "+", ".join(sorted(duplicate_destinations)))
 return {"read_only":True,"files":files,"blockers":blockers,
         "configuration_policy":"preserve-existing; configure separately on fresh installations",
         "excluded_from_transaction":[CONFIG,*("/etc/systemd/system/"+f for f in UNIT_FILES),
                                      "Minecraft servers/worlds","backup volumes","systemd timer state"],
         "production_apply_enabled":False}

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--repo",default=str(ROOT))
 p.add_argument("--frontend",default="/usr/local/share/cockpit/minecraft-manager")
 p.add_argument("--libexec",default="/usr/local/libexec")
 a=p.parse_args()
 print(json.dumps(plan(a.repo,a.frontend,a.libexec),indent=2))
