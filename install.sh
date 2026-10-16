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
    if [[ "${HOST:-}" != "" ]]; then usage; exit 2; fi
    echo 'BLOCKED: v1.2 requires explicit --accept for a host installation.' >&2
    echo 'The repository still lacks a complete dependency/unit manifest and tested fresh-install/upgrade/rollback procedures.' >&2
    echo 'No files, Cockpit modules, services, timers, or worlds have been modified.' >&2
    echo 'Use --check to review the release blockers.' >&2
    exit 3
    ;;
  --rollback|--finalize)
    if (( EUID != 0 )); then echo 'Root required.' >&2; exit 2; fi
    ACTION="${MODE#--}"
    if [[ "$ACTION" == "rollback" ]]; then ACTION="recover"; fi
    exec python3 "$ROOT/tools/production-transaction.py" "$ACTION" --repo "$ROOT" --root /
    ;;
  *) usage;exit 2;;
esac
