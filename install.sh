#!/usr/bin/env bash
# Cockpit Minecraft Manager v1.2 release-candidate entry point.
# Intentionally DOES NOT install incomplete sources.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
usage(){
  echo 'Usage: bash install.sh --check [--host]'
  echo '       sudo bash install.sh --apply  (blocked until full install/upgrade acceptance tests pass)'
}
MODE="${1:---check}"; shift || true
HOST=''
if [[ "${1:-}" == '--host' ]]; then HOST='--host';shift;fi
if (($#));then usage;exit 2;fi
case "$MODE" in
  --check)
    echo 'v1.2 pre-install validation; no host changes will be made.'
    bash "$ROOT/tools/release-preflight.sh" $HOST
    ;;
  --apply)
    echo 'BLOCKED: v1.2 is a release candidate, not a tested full installer.' >&2
    echo 'The repository still lacks a complete dependency/unit manifest and tested fresh-install/upgrade/rollback procedures.' >&2
    echo 'No files, Cockpit modules, services, timers, or worlds have been modified.' >&2
    echo 'Use --check to review the release blockers.' >&2
    exit 3
    ;;
  *) usage;exit 2;;
esac
