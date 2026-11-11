# Live-source comparison — 2026-11-11

Source: explicitly reviewed development-host archive `cockpit-source-review.zip`,
compared by Git blob SHA against this feature branch. **The archive itself
has not been committed**.

## Diff summary

- **16 unchanged** application files.
- **9 modified**:
  - `backend/cockpit-minecraft-helper`
  - `backend/cockpit-minecraft-join-control`
  - `backend/cockpit-minecraft-modpacks`
  - `backend/cockpit-minecraft-records`
  - `backend/minecraft-default-proxy`
  - `backend/minecraft-join-announcer`
  - `cockpit/minecraft-manager/app.js`
  - `cockpit/minecraft-manager/index.html`
  - `cockpit/minecraft-manager/manifest.json`
- **1 new**: `backend/mc-console-aio.py`.
- `backend/minecraft-manual-backup` exists in GitHub but was not in the host
  archive: **retain** the repository version.

## Publication blockers found during review

The live application files contain development-machine-specific data.
**Do not commit the raw archive.**

- A hardcoded private LAN address and Tailscale address in frontend text.
- A hardcoded external-disk backup repository/mount path in helper and
  frontend defaults, plus a development-drive UUID.
- Development-specific user-agent branding and site URL.
- Several assumptions about a pre-existing NeoForge installation, unit
  names, backup configuration, and mount points.

A regex search finding no password literals does **not** guarantee absence of
secrets or privacy-sensitive strings. Each changed helper also requires
code review, portable defaults, and syntax/integration tests.

## Import procedure

Use the allowlisted source-review collector in `tools/collect-live-source.py`.
Make a reviewed candidate with host-specific paths/IPs/identifiers replaced
with portable configuration. Compare each changed source against its base
version; do not overwrite unrelated files and do not delete files missing
from the host snapshot.

Push the sanitized source on a review branch, run existing project tests,
then review the draft PR before merging into the release branch. Never
run an unverified candidate against the production Minecraft host.

This is a release engineering log, not a claim that the live code has
already been published.
