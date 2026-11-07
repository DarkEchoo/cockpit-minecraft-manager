#!/usr/bin/env bash
# Deploy ONLY the new read-only CurseForge browser to an existing Cockpit module.
# Deliberately does not run the unified installer or change server services/worlds.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
FRONTEND=/usr/local/share/cockpit/minecraft-manager
BACKEND=/usr/local/libexec
BACKUP_BASE=/var/backups
declare -a SOURCES=(
  "cockpit/minecraft-manager/index.html"
  "cockpit/minecraft-manager/modpacks.js"
  "cockpit/minecraft-manager/styles.css"
  "backend/cockpit-minecraft-curseforge-browser"
  "cockpit/minecraft-manager/manifest.json"
)
declare -a TARGETS=(
  "$FRONTEND/index.html"
  "$FRONTEND/modpacks.js"
  "$FRONTEND/styles.css"
  "$BACKEND/cockpit-minecraft-curseforge-browser"
  "$FRONTEND/manifest.json"
)
EXPECTED_ORIGINAL_JS="3754c04816c1ee20ad363105db864ef8e6f80a0a88099c98cbb68a4274771911"
EXPECTED_ORIGINAL_CSS="45879d318245ee335d6baa79fdb59961270a2eafbd0ed9afbc7ba7f1bea94c4d"

die(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage(){
  echo "Usage: sudo bash tools/deploy-curseforge-browser-live.sh --apply"
  echo "       sudo bash tools/deploy-curseforge-browser-live.sh --rollback /var/backups/cockpit-minecraft-browser.XXXXXXXX"
}
(( EUID == 0 )) || die 'Run with sudo.'
[[ $# -ge 1 ]] || { usage; exit 2; }
command -v python3 >/dev/null || die 'python3 is required'
command -v sha256sum >/dev/null || die 'sha256sum is required'
for targetdir in "$FRONTEND" "$BACKEND"; do
  [[ -d "$targetdir" && ! -L "$targetdir" ]] || die "Unsafe or missing target directory: $targetdir"
done
[[ -f "$FRONTEND/manifest.json" && ! -L "$FRONTEND/manifest.json" ]] || die 'Installed Cockpit Minecraft module not found'
[[ ! -e /usr/share/cockpit/minecraft-manager/manifest.json ]] || die 'Duplicate Cockpit Minecraft module found; investigate manually'
exec 9>/run/lock/cockpit-minecraft-browser-deploy.lock
flock -n 9 || die 'Another CurseForge browser deployment is running'

function rollback_dir(){
  local dir="$1" meta="$1/manifest.txt" rel dest status i=0
  [[ "$dir" == /var/backups/cockpit-minecraft-browser.* && -d "$dir" && ! -L "$dir" ]] || die 'Invalid backup directory'
  [[ -f "$meta" && ! -L "$meta" ]] || die 'Backup manifest missing'
  while IFS='|' read -r rel status; do
    (( i++ )) || true
    case "$rel" in
      index.html|modpacks.js|styles.css|manifest.json) dest="$FRONTEND/$rel";;
      cockpit-minecraft-curseforge-browser) dest="$BACKEND/$rel";;
      *) die 'Unexpected backup entry';;
    esac
    [[ ! -L "$dest" ]] || die "Refusing symlink: $dest"
    case "$status" in
      existing)
        [[ -f "$dir/$rel" && ! -L "$dir/$rel" ]] || die "Missing backup: $rel"
        install -o root -g root -m "$(stat -c %a "$dir/$rel")" "$dir/$rel" "$dest"
        ;;
      absent) rm -f -- "$dest";;
      *) die 'Invalid backup state';;
    esac
  done < "$meta"
  echo "Original browser files restored. No Minecraft service was changed."
}

case "$1" in
  --rollback)
    [[ $# -eq 2 ]] || { usage; exit 2; }
    rollback_dir "$2"
    exit 0
    ;;
  --apply)
    [[ $# -eq 1 ]] || { usage; exit 2; }
    ;;
  *) usage;exit 2;;
esac

# Preserve a customized index.html with a surgical patch, but refuse to
# replace unrecognized JavaScript or CSS: those may have live-only features.
for i in 1 2; do
  src="$ROOT/${SOURCES[$i]}"
  dest="${TARGETS[$i]}"
  [[ -f "$src" && ! -L "$src" ]] || die "Missing local package: $src"
  [[ -f "$dest" && ! -L "$dest" ]] || die "Unexpected installed file: $dest"
  case "$i" in
    1) expected="$EXPECTED_ORIGINAL_JS";;
    2) expected="$EXPECTED_ORIGINAL_CSS";;
  esac
  old="$(sha256sum "$dest" | cut -d' ' -f1)"
  new="$(sha256sum "$src" | cut -d' ' -f1)"
  if [[ "$old" != "$expected" && "$old" != "$new" ]]; then
    die "Customized file $dest (SHA256 $old); refusing to overwrite it."
  fi
done
# Produce a minimal HTML patch in a disposable staging directory. The
# installed page is not overwritten with the repository's full index.html.
[[ -f "${TARGETS[0]}" && ! -L "${TARGETS[0]}" ]] || die 'Missing or unsafe installed index.html'
stage="$(mktemp -d /tmp/mc-browser-live-patch.XXXXXXXX)"
trap 'rm -rf -- "$stage"' EXIT
if ! python3 "$ROOT/tools/patch-live-curseforge-html.py" "${TARGETS[0]}" "$stage/index.html"; then
  die 'Existing HTML differs from the expected browser panel. No files changed; manual compatibility review required.'
fi
# Keep every existing manifest setting, changing only the image load policy.
# Allow only explicitly reviewed CurseForge image hosts; no broad HTTPS wildcard.
if ! python3 "$ROOT/tools/patch-live-curseforge-manifest.py" "$FRONTEND/manifest.json" "$stage/manifest.json"; then
  die 'Existing Cockpit manifest policy needs manual review. No files changed.'
fi
for src in "${SOURCES[@]}"; do
  [[ -f "$ROOT/$src" && ! -L "$ROOT/$src" ]] || die "Unsafe or missing package: $src"
done
[[ ! -L "${TARGETS[3]}" ]] || die 'Existing browser helper is a symlink'
if [[ -e "${TARGETS[3]}" && ! -f "${TARGETS[3]}" ]]; then
  die 'Existing browser helper is not a regular file'
fi

python3 - "$ROOT/backend/cockpit-minecraft-curseforge-browser" <<'PY'
import ast, pathlib, sys
ast.parse(pathlib.Path(sys.argv[1]).read_text())
PY
if command -v node >/dev/null; then node --check "$ROOT/cockpit/minecraft-manager/modpacks.js"; fi
if ! grep -q 'mp-project-detail' "$ROOT/cockpit/minecraft-manager/index.html"; then
  die 'New HTML missing CurseForge detail panel'
fi
mkdir -p "$BACKUP_BASE"
backup="$(mktemp -d "$BACKUP_BASE/cockpit-minecraft-browser.XXXXXXXX")"
chmod 700 "$backup"
touch "$backup/manifest.txt"
chmod 600 "$backup/manifest.txt"
for i in "${!TARGETS[@]}"; do
  target="${TARGETS[$i]}"
  name="${target##*/}"
  if [[ -f "$target" ]]; then
    cp -p -- "$target" "$backup/$name"
    printf '%s|existing\n' "$name" >> "$backup/manifest.txt"
  else
    printf '%s|absent\n' "$name" >> "$backup/manifest.txt"
  fi
done
echo "Backup created: $backup"
failed(){
  rc=$?
  trap - ERR
  echo 'Deployment encountered an error; restoring original application files.' >&2
  rollback_dir "$backup" || true
  exit "$rc"
}
trap failed ERR
for i in "${!SOURCES[@]}"; do
  target="${TARGETS[$i]}"
  mode=644
  [[ "$i" -eq 3 ]] && mode=755
  source_file="$ROOT/${SOURCES[$i]}"
  [[ "$i" -eq 0 ]] && source_file="$stage/index.html"
  [[ "$i" -eq 4 ]] && source_file="$stage/manifest.json"
  install -o root -g root -m "$mode" "$source_file" "$target"
done
trap - ERR
echo 'CurseForge browser and restricted image policy deployed. Existing Minecraft helper, services, worlds and backups were not touched.'
echo 'Refresh the Cockpit page with Ctrl+Shift+R, open Modpacks, and select a Minecraft version.'
echo "To undo ONLY this browser deployment: sudo bash '$ROOT/tools/deploy-curseforge-browser-live.sh' --rollback '$backup'"
