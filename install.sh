#!/usr/bin/env bash
# Cockpit Minecraft Manager v1.2 release-candidate entry point.
# Intentionally DOES NOT install incomplete sources.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
usage(){
  echo 'Usage: bash install.sh --check [--host]'
  echo '       sudo bash install.sh --plan (read-only file change inventory)'
  echo '       sudo bash install.sh --apply --accept (unverified host install; explicit opt-in required)'
  echo '       sudo bash install.sh --rollback | --finalize'
}
MODE="${1:---check}"; shift || true
HOST=''
if [[ "${1:-}" == '--host' ]]; then HOST='--host';shift;fi
ACCEPT=''
if [[ "$MODE" == '--apply' && "${1:-}" == '--accept' ]]; then ACCEPT=yes; shift; fi
if (($#));then usage;exit 2;fi
case "$MODE" in
  --check)
    echo 'v1.2 pre-install validation; no host changes will be made.'
    if [[ "$HOST" == "--host" ]]; then
      echo "Checking Cockpit installation and socket (read-only):"
      REPORT="$(python3 "$ROOT/tools/cockpit-prerequisite.py")"
      printf '%s\\n' "$REPORT"
      if ! python3 -c 'import json,sys;sys.exit(0 if json.loads(sys.argv[1])["ready"] else 1)' "$REPORT"; then
        echo 'Cockpit prerequisite check failed. Install Cockpit and activate cockpit.socket before deployment.' >&2
        echo 'On Ubuntu: sudo apt install cockpit && sudo systemctl enable --now cockpit.socket' >&2
        exit 4
      fi
    fi
    bash "$ROOT/tools/release-preflight.sh" $HOST
    ;;
  --plan)
    echo "Read-only proposed installation inventory; no files will be changed."
    python3 "$ROOT/tools/production-transaction.py" inventory --repo "$ROOT" --root /
    ;;
  --apply)
    if [[ -z "$ACCEPT" ]]; then
      echo 'BLOCKED: production apply requires --accept and final host review.' >&2
      exit 3
    fi
    if (( EUID != 0 )); then echo 'Root required for installation.' >&2; exit 2; fi
    # Cockpit is a hard requirement; nothing is installed automatically.
    REPORT="$(python3 "$ROOT/tools/cockpit-prerequisite.py")"
    if ! python3 -c 'import json,sys;sys.exit(0 if json.loads(sys.argv[1])["ready"] else 1)' "$REPORT"; then
      echo 'Cockpit is not installed/active; installation aborted.' >&2; exit 4
    fi
    # Never create a duplicate Cockpit menu module at the distro path.
    if [[ -e /usr/share/cockpit/minecraft-manager/manifest.json ]]; then
      echo 'A second Minecraft Cockpit module exists in /usr/share/cockpit; resolve before installing.' >&2
      exit 5
    fi
    exec 8>/run/lock/cockpit-minecraft-manager-installer.lock
    flock -n 8 || { echo 'Another installer is active.' >&2; exit 6; }
    STAGE_CHECK="$(mktemp -d /tmp/cockpit-minecraft-release-check.XXXXXXXX)"
    trap 'rm -rf -- "$STAGE_CHECK"' EXIT
    python3 "$ROOT/tools/build-release-stage.py" --repo "$ROOT" --output "$STAGE_CHECK/payload" >/dev/null
    echo 'Package validated. Installing app files only; existing services, backups, timers and configuration will not change.'
    python3 "$ROOT/tools/production-transaction.py" apply --repo "$ROOT" --root /
    echo 'Installed. Verify Cockpit functionality before running sudo bash install.sh --finalize.'
    echo 'To restore the previous files, run sudo bash install.sh --rollback.'
    ;;
  --rollback|--finalize)
    if (( EUID != 0 )); then echo 'Root required.' >&2; exit 2; fi
    ACTION="${MODE#--}"
    if [[ "$ACTION" == "rollback" ]]; then ACTION="recover"; fi
    exec python3 "$ROOT/tools/production-transaction.py" "$ACTION" --repo "$ROOT" --root /
    ;;
  *) usage;exit 2;;
esac
