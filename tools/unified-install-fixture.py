#!/usr/bin/env python3
"""Fixture-only unified installer integration test harness.

Uses the real staged release files, installs them into a disposable tree, and
rolls back both Cockpit and libexec files on a simulated failure. Production
paths and systemd are never accessed.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("mc_release_stage",HERE/"build-release-stage.py")
stage_mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage_mod)

def install_fixture(repo, root, fail_after=None):
 root=Path(root).resolve(strict=True)
 if not root.is_relative_to("/tmp") and not root.is_relative_to("/var/tmp"):
  raise ValueError("Fixture-only: root must be in /tmp or /var/tmp")
 if not (root/".mc-fixture-only").is_file():
  raise ValueError("Fixture marker required")
 target=root/"installed"
 if target.is_symlink() or not target.is_dir():
  raise ValueError("Existing non-symlink installed fixture required")
 stage_dir=root/"release-stage"
 if stage_dir.exists() or stage_dir.is_symlink():
  raise ValueError("Existing staging directory: refuse")
 manifest=stage_mod.stage(repo,stage_dir)
 for item in manifest["files"]:
  p=target/item["path"]
  ancestor=p
  while ancestor != target:
   if ancestor.is_symlink():
    raise ValueError("Symlink in destination path refused: "+str(ancestor))
   ancestor=ancestor.parent
  if p.is_symlink():
   raise ValueError("Symlink destination refused")
  if p.exists() and not p.is_file():
   raise ValueError("Non-regular destination refused")
 # One complete original-file snapshot covers all components.
 snapshot=root/"original-snapshot"
 if snapshot.exists() or snapshot.is_symlink():
  raise ValueError("Previous snapshot exists")
 snapshot.mkdir()
 records=[]
 installed=[]
 try:
  for entry in manifest["files"]:
   relative=Path(entry["path"])
   dest=target/relative
   dest.parent.mkdir(parents=True,exist_ok=True)
   if dest.exists():
    prev=snapshot/relative
    prev.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(dest,prev)
   else:
    prev=None
   records.append((dest,prev))
  for entry in manifest["files"]:
   relative=Path(entry["path"])
   dest=target/relative
   # Record the target BEFORE writing: copy errors must also roll back.
   installed.append(dest)
   shutil.copy2(stage_dir/relative,dest)
   if hashlib.sha256(dest.read_bytes()).hexdigest()!=entry["sha256"]:
    raise RuntimeError("Checksum mismatch after fixture copy")
   if fail_after is not None and len(installed)>=fail_after:
    raise RuntimeError("Injected install failure")
  return {"ok":True,"files":len(installed),"production_apply_enabled":False}
 except Exception:
  failures=[]
  for dest,prev in reversed(records):
   if dest in installed or (dest.exists() and prev is None):
    try:
     if prev is None:
      dest.unlink(missing_ok=True)
     else:
      shutil.copy2(prev,dest)
    except OSError as err:
     failures.append(f"{dest}: {err}")
  if failures:
   # Recovery snapshot MUST survive a failed rollback.
   raise RuntimeError("Rollback incomplete; original backups preserved at "
                      +str(snapshot)+": "+"; ".join(failures))
  raise
 finally:
  shutil.rmtree(stage_dir,ignore_errors=True)
  if not snapshot.exists() or not locals().get("failures"):
   shutil.rmtree(snapshot,ignore_errors=True)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--repo",default=str(HERE.parent))
 p.add_argument("--sandbox",required=True)
 p.add_argument("--fail-after",type=int)
 a=p.parse_args()
 print(json.dumps(install_fixture(a.repo,a.sandbox,a.fail_after),indent=2))
if __name__=="__main__":main()
