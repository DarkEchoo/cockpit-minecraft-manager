#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
usage(){ echo 'Usage: sudo bash install.sh --check|--apply --backup-dir ABS_PATH --workspace-root ABS_PATH --workspace ID'; }
MODE="${1:---check}"; shift || :
[[ "$MODE" == --check || "$MODE" == --apply ]] || { usage;exit 2; }
[[ $EUID == 0 ]] || { echo 'Use sudo';exit 1; }
BACKUP_DIR='' ROOT='' WS=''
while (($#)); do case "$1" in --backup-dir) BACKUP_DIR="${2:-}";shift 2;; --workspace-root) ROOT="${2:-}";shift 2;; --workspace) WS="${2:-}";shift 2;; *) usage;exit 2;; esac; done
CONFIG=/etc/cockpit-minecraft/backup-manager.json
if [[ -f "$CONFIG" ]]; then
 mapfile -t prev < <(python3 - "$CONFIG" <<'PY'
import json,sys
j=json.load(open(sys.argv[1]))
for key in ('backup_directory','workspace_root','scheduled_workspace'):print(j.get(key,''))
PY
 )
 BACKUP_DIR="${BACKUP_DIR:-${prev[0]}}";ROOT="${ROOT:-${prev[1]}}";WS="${WS:-${prev[2]}}"
fi
[[ -n "$BACKUP_DIR" && -n "$ROOT" && "$WS" =~ ^[a-z][a-z0-9-]{1,34}$ ]] || { usage; echo 'Supply workspace, source root and backup directory (first installation).';exit 1; }
[[ "$BACKUP_DIR" == /* && "$ROOT" == /* && "$BACKUP_DIR" != *..* && "$ROOT" != *..* ]] || { echo 'Invalid paths';exit 1; }
[[ -d "$BACKUP_DIR" && -d "$ROOT/$WS" && ! -L "$BACKUP_DIR" && ! -L "$ROOT/$WS" ]] || { echo 'Backup directory or workspace missing / symlink';exit 1; }
MOUNT=$(findmnt -rn -T "$BACKUP_DIR" -o TARGET)
UUID=$(findmnt -rn -M "$MOUNT" -o UUID)
[[ -n "$UUID" && "$MOUNT" != '/' && "$BACKUP_DIR" == "$MOUNT"/* ]] || { echo 'Backup directory must be on a separately mounted UUID-identifiable volume';exit 1; }
[[ "$(stat -c %d "$BACKUP_DIR")" != "$(stat -c %d "$ROOT/$WS")" ]] || { echo 'Backup target must be on separate filesystem';exit 1; }
LIVE=/usr/local/share/cockpit/minecraft-manager
[[ -f "$LIVE/index.html" && ! -L "$LIVE/index.html" ]] || { echo 'Existing Cockpit Minecraft Manager required. This is an add-on installer.';exit 1; }
command -v systemctl >/dev/null;command -v findmnt >/dev/null;command -v python3 >/dev/null
python3 - "$ROOT" "$WS" <<'PY'
import json,sys,pathlib
p=pathlib.Path(sys.argv[1])/sys.argv[2]/'modpack.json'
if not p.is_file():raise SystemExit('Required workspace manifest missing: '+str(p))
json.loads(p.read_text())
PY
python3 - "$PWD" <<'PY'
import sys,ast,pathlib
p=pathlib.Path(sys.argv[1])
for x in (p/'helpers').glob('*.py'):ast.parse(x.read_text())
for x in (p/'helpers').iterdir():
 if x.name=='mc_backup_config.py':continue
 ast.parse(x.read_text())
PY
if command -v node >/dev/null;then node --check cockpit/modpack-schedule-ui.js;fi
# Avoid conflicting with enabled backup timers when changing unit definition.
if systemctl is-enabled "cockpit-mc-snapshot@${WS}.timer" 2>/dev/null | grep -qx enabled;then
 echo 'Stop: timer enabled. Disable explicitly before upgrading.';exit 1
fi
# Requires v0.9 panel for DOM update; no duplicate injection.
python3 - "$LIVE/index.html" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text()
assert s.count('id="mp09-panel"')==1, 'Backup Center panel missing or duplicated; resolve before installing'
assert s.count('id="mp11-panel"')<=1, 'Scheduler panel duplicated; resolve before installing'
assert s.count('<script src="modpack-backup-ui.js"></script>')==1, 'Backup Center script missing or duplicated'
assert s.count('<script src="modpack-schedule-ui.js"></script>')<=1, 'Scheduler script duplicated'
PY
printf 'PASS: source files, mount, workspace, prerequisites and DOM anchors\n'
printf 'Configuration: root=%s destination=%s volume=%s UUID=%s workspace=%s\n' "$ROOT" "$BACKUP_DIR" "$MOUNT" "$UUID" "$WS"
if [[ "$MODE" == --check ]];then echo 'DRY RUN: no files changed.';exit 0;fi
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
SAVE="/var/backups/cockpit-public-backup-manager-$STAMP-$$"
install -d -m 0700 "$SAVE" /etc/cockpit-minecraft /usr/local/libexec
for p in "$CONFIG" "$LIVE/index.html" "$LIVE/modpack-schedule-ui.js" /usr/local/libexec/cockpit-minecraft-backup /usr/local/libexec/cockpit-minecraft-backup-center /usr/local/libexec/cockpit-mc-snapshot /usr/local/libexec/cockpit-mc-schedule /usr/local/libexec/mc_backup_config.py /etc/systemd/system/cockpit-mc-snapshot@.service /etc/systemd/system/cockpit-mc-snapshot@.timer; do
 if [[ -f "$p" ]];then mkdir -p "$SAVE$(dirname "$p")"; cp -a "$p" "$SAVE$p";fi
done
python3 - "$CONFIG" "$ROOT" "$BACKUP_DIR" "$MOUNT" "$UUID" "$WS" <<'PY'
import json,pathlib,sys,os
path=pathlib.Path(sys.argv[1]);root,dest,mount,uuid,ws=sys.argv[2:]
tmp=path.with_name('.backup-manager.json.tmp')
tmp.write_text(json.dumps(dict(workspace_root=root,backup_mount=mount,backup_directory=dest,filesystem_uuid=uuid,scheduled_workspace=ws),indent=2)+'\n')
os.chmod(tmp,0o600);tmp.replace(path)
PY
for p in helpers/*;do install -o root -g root -m 0755 "$p" /usr/local/libexec/;done
python3 - 'systemd/cockpit-mc-snapshot@.service.in' "$BACKUP_DIR" "$MOUNT" '/etc/systemd/system/cockpit-mc-snapshot@.service' <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text().replace('@@BACKUP_DIR@@',sys.argv[2]).replace('@@BACKUP_MOUNT@@',sys.argv[3])
Path(sys.argv[4]).write_text(s)
PY
chmod 644 /etc/systemd/system/cockpit-mc-snapshot@.service
install -m 0644 systemd/cockpit-mc-snapshot@.timer /etc/systemd/system/cockpit-mc-snapshot@.timer
install -m 0644 cockpit/modpack-schedule-ui.js "$LIVE/modpack-schedule-ui.js"
python3 - "$LIVE/index.html" cockpit/panel.html <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text();panel=Path(sys.argv[2]).read_text()
if 'id="mp11-panel"' not in s:
 pos=s.index('id="mp09-panel"');end=s.index('</section>',pos)
 s=s[:end]+panel+'\n'+s[end:]
if '<script src="modpack-schedule-ui.js"></script>' not in s:
 s=s.replace('<script src="modpack-backup-ui.js"></script>','<script src="modpack-backup-ui.js"></script>\n<script src="modpack-schedule-ui.js"></script>')
p.write_text(s)
PY
systemctl daemon-reload
printf 'SUCCESS. Previous files backed up to: %s\n' "$SAVE"
echo 'NO timers enabled, backups launched, Minecraft services touched, or worlds modified.'
