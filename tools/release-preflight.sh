#!/usr/bin/env bash
# Release-readiness audit only. Makes no system changes and prints no secrets.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0; WARNINGS=0
ok(){ printf 'PASS  %s\n' "$*"; }
warn(){ printf 'WARN  %s\n' "$*"; WARNINGS=$((WARNINGS+1)); }
fail(){ printf 'FAIL  %s\n' "$*"; ERRORS=$((ERRORS+1)); }
echo "Cockpit Minecraft Manager v1.2 release preflight (read-only)"
for file in README.md SECURITY.md cockpit/minecraft-manager/manifest.json cockpit/minecraft-manager/index.html cockpit/minecraft-manager/app.js backend/cockpit-minecraft-helper addons/backup-manager/install.sh; do
  if [[ -f "$ROOT/$file" ]]; then ok "Source present: $file"; else fail "Missing source: $file"; fi
done
for bin in bash python3 systemctl findmnt tar sha256sum; do
  if command -v "$bin" >/dev/null 2>&1; then ok "Tool available: $bin"; else warn "Tool unavailable: $bin"; fi
done
if command -v node >/dev/null 2>&1; then
  bad=0
  while IFS= read -r -d '' path; do
    if ! node --check "$path" >/dev/null 2>&1; then fail "JavaScript parse failed: ${path#"$ROOT/"}"; bad=1; fi
  done < <(find "$ROOT/cockpit" "$ROOT/addons/backup-manager/cockpit" -name '*.js' -type f -print0 2>/dev/null)
  [[ $bad == 1 ]] || ok "JavaScript syntax"
else warn "Node.js absent: JavaScript validation skipped"; fi
if python3 - "$ROOT" <<'PY'
import ast,pathlib,sys
root=pathlib.Path(sys.argv[1])
paths=list((root/'backend').glob('*'))+list((root/'addons/backup-manager/helpers').glob('*'))
errors=[]
for path in paths:
 if not path.is_file():continue
 try:ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
 except (SyntaxError,UnicodeError) as e:errors.append(f'{path.relative_to(root)}: {e}')
for e in errors:print(e)
sys.exit(bool(errors))
PY
then ok "Backend Python syntax";else fail "Backend Python parse failure";fi
if [[ -f "$ROOT/LICENSE" || -f "$ROOT/COPYING" ]]; then ok "License file exists";else fail "No LICENSE/COPYING: do not call this a redistributable open-source release";fi
if [[ ! -f "$ROOT/install.sh" ]]; then fail "No unified root installer; backup add-on requires pre-existing manager"; else ok "Root installer exists (requires functional test)"; fi
if command -v rg >/dev/null 2>&1; then
  if rg -n -i 'development snapshot|not a ready-to-install release' "$ROOT/README.md" >/dev/null;then warn "README still labels repository a development snapshot";fi
fi
if [[ "${1:-}" == "--host" ]];then
  echo "Installed-host inspection (read-only)"
  for dir in /usr/local/share/cockpit/minecraft-manager /usr/share/cockpit/minecraft-manager /etc/cockpit/minecraft-manager /usr/local/share/cockpit/minecraft /usr/share/cockpit/minecraft;do
    if [[ -f "$dir/manifest.json" ]];then
      printf 'FOUND Cockpit manifest: %s\n' "$dir/manifest.json"
    fi
  done
  echo "Inspect any duplicates manually; do NOT delete modules by name alone."
fi
printf '\nAudit: %d failure(s), %d warning(s)\n' "$ERRORS" "$WARNINGS"
((ERRORS == 0))
