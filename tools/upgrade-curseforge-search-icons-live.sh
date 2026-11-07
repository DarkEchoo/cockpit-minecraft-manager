#!/usr/bin/env bash
# Incremental patch for a live Cockpit module already running enhanced CurseForge UI.
# Only replaces its browser helper and modpacks.js; minimally patches manifest CSP.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
FRONT=/usr/local/share/cockpit/minecraft-manager
BACK=/usr/local/libexec
BR=cockpit-minecraft-curseforge-browser
declare -a TARGETS=("$FRONT/modpacks.js" "$BACK/$BR" "$FRONT/manifest.json" "$FRONT/styles.css")
declare -a NAMES=("modpacks.js" "$BR" "manifest.json" "styles.css")
die(){ echo "ERROR: $*" >&2; exit 1; }
(( EUID == 0 )) || die 'Run this script with sudo'
[[ $# -eq 1 || ($# -eq 2 && "$1" == '--rollback') ]] || die 'Usage: --apply OR --rollback /var/backups/cockpit-minecraft-search-icons.XXXXXXXX'
[[ -d "$FRONT" && ! -L "$FRONT" && -d "$BACK" && ! -L "$BACK" ]] || die 'Unsafe or missing installation directory'
[[ -f "$FRONT/index.html" && ! -L "$FRONT/index.html" ]] || die 'Minecraft Console not installed'
exec 9>/run/lock/cockpit-minecraft-browser-deploy.lock
flock -n 9 || die 'Another CurseForge deployment is running'

rollback(){
 local folder="$1" i entry status
 [[ "$folder" == /var/backups/cockpit-minecraft-search-icons.* && -d "$folder" && ! -L "$folder" ]] || die 'Invalid rollback location'
 [[ -f "$folder/manifest.txt" && ! -L "$folder/manifest.txt" ]] || die 'Missing backup manifest'
 for i in "${!TARGETS[@]}"; do
   entry="${TARGETS[$i]}"
   status="$(sed -n "$((i+1))p" "$folder/manifest.txt")"
   [[ ! -L "$entry" ]] || die "Symlink destination: $entry"
   case "$status" in
    existing)
      [[ -f "$folder/${NAMES[$i]}" && ! -L "$folder/${NAMES[$i]}" ]] || die 'Missing backup file'
      cp -p -- "$folder/${NAMES[$i]}" "$entry"
      ;;
    absent) rm -f -- "$entry";;
    *) die 'Invalid rollback manifest';;
   esac
 done
 echo 'Original CurseForge browser files and Cockpit manifest restored.'
}
if [[ "$1" == '--rollback' ]]; then rollback "$2";exit 0;fi
[[ "$1" == '--apply' ]] || die 'Usage: --apply'
for target in "${TARGETS[@]}"; do
  [[ -f "$target" && ! -L "$target" ]] || die "Missing or unsafe installed file: $target"
done
[[ -f "$ROOT/cockpit/minecraft-manager/styles.css" ]] || die "Missing packaged CSS"
[[ -f "$ROOT/cockpit/minecraft-manager/modpacks.js" ]] || die 'Missing packaged JavaScript'
[[ -f "$ROOT/backend/$BR" ]] || die 'Missing packaged helper'
[[ -f "$ROOT/tools/patch-live-curseforge-manifest.py" ]] || die 'Missing manifest patcher'
grep -q 'mp-project-detail' "$FRONT/index.html" || die 'Enhanced browser HTML not yet installed'
grep -q 'cockpit-minecraft-curseforge-browser' "$FRONT/modpacks.js" || die 'Installed JS is not the known enhanced browser version; manual review required'
if command -v node >/dev/null; then node --check "$ROOT/cockpit/minecraft-manager/modpacks.js";fi
python3 - "$ROOT/backend/$BR" <<'PY'
import ast,sys,pathlib
ast.parse(pathlib.Path(sys.argv[1]).read_text())
PY
stage="$(mktemp -d /tmp/mc-curseforge-upgrade.XXXXXXXX)"
trap 'rm -rf -- "$stage"' EXIT
python3 "$ROOT/tools/patch-live-curseforge-manifest.py" "$FRONT/manifest.json" "$stage/manifest.json" ||
  die 'Custom Cockpit image policy requires manual review; no changes made'
backup="$(mktemp -d /var/backups/cockpit-minecraft-search-icons.XXXXXXXX)"
chmod 700 "$backup"
: > "$backup/manifest.txt"
chmod 600 "$backup/manifest.txt"
for i in "${!TARGETS[@]}"; do
  if [[ -f "${TARGETS[$i]}" ]];then
    cp -p -- "${TARGETS[$i]}" "$backup/${NAMES[$i]}"
    echo existing >> "$backup/manifest.txt"
  else
    echo absent >> "$backup/manifest.txt"
  fi
done
echo "Backup created: $backup"
failed(){ rc=$?;trap - ERR;echo 'Deployment failed; restoring backups' >&2;rollback "$backup" || true;exit "$rc"; }
trap failed ERR
install -o root -g root -m 644 "$ROOT/cockpit/minecraft-manager/modpacks.js" "$FRONT/modpacks.js"
install -o root -g root -m 755 "$ROOT/backend/$BR" "$BACK/$BR"
install -o root -g root -m 644 "$stage/manifest.json" "$FRONT/manifest.json"
install -o root -g root -m 644 "$ROOT/cockpit/minecraft-manager/styles.css" "$FRONT/styles.css"
trap - ERR
echo 'CurseForge browser, inline detail styling and image permissions updated; no Minecraft services changed.'
echo "Rollback: sudo bash '$ROOT/tools/upgrade-curseforge-search-icons-live.sh' --rollback '$backup'"
