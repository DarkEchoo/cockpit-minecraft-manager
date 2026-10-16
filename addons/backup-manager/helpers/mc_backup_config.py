#!/usr/bin/env python3
"""Central runtime settings. Never embed host values in public source."""
import json,pathlib,re,subprocess
CONFIG=pathlib.Path('/etc/cockpit-minecraft/backup-manager.json')
def load():
 d=json.loads(CONFIG.read_text())
 for key in ('workspace_root','backup_mount','backup_directory','filesystem_uuid'):
  if not isinstance(d.get(key),str) or not d[key]: raise RuntimeError('Missing config: '+key)
 for k in ('workspace_root','backup_mount','backup_directory'):
  p=pathlib.Path(d[k]);
  if not p.is_absolute() or '..' in p.parts:raise RuntimeError('Invalid config path: '+k)
 if not re.fullmatch(r'[a-fA-F0-9-]{8,64}',d['filesystem_uuid']): raise RuntimeError('Invalid filesystem UUID')
 return d
def mount_check(d):
 m=pathlib.Path(d['backup_mount']); dest=pathlib.Path(d['backup_directory'])
 if m.is_symlink() or dest.is_symlink() or not dest.is_dir() or not dest.is_relative_to(m):raise RuntimeError('Unsafe backup destination')
 p=subprocess.run(['findmnt','-rn','-M',str(m),'-o','UUID,FSTYPE'],capture_output=True,text=True,timeout=10)
 fields=p.stdout.split()
 if p.returncode or len(fields)!=2 or fields[0].upper()!=d['filesystem_uuid'].upper():raise RuntimeError('Backup volume UUID mismatch or not mounted')
 if fields[1].lower() not in ('ext4','xfs','btrfs','ntfs','ntfs3','exfat'):raise RuntimeError('Unsupported backup filesystem')
 return fields[1]
