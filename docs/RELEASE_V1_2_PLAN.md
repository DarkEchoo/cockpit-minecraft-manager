# v1.2 unified installer — release candidate

Status: **not released**. Branch: `release/v1.2-unified-installer`.

## Verified baseline

- Main commit `f51438b` includes the configurable v1.1.1 backup-manager add-on.
- The root repository is a sanitized development snapshot, not a complete fresh-install distribution.
- The add-on currently requires an existing Cockpit Minecraft Manager, an existing modpack workspace, an independent backup mount, and systemd.
- Successful tests on one Ubuntu host do not establish safe behavior on a clean host.

## Public-release gates

1. Inventory *all* backend-to-backend and frontend-to-backend calls. Include missing scripts and systemd units; avoid hard-coded usernames, drive UUIDs, private paths, credentials, and active server IDs.
2. Publish a root installer with `--check` (non-mutating) and `--apply`, supporting **fresh installation** and **in-place upgrade**. Preserve current modules, worlds, server registry, RCON settings, timers, backup archives, and machine-local configuration.
3. Detect Cockpit modules by canonical manifests and known package signatures. Show duplicate candidates before cleanup; back up then remove *only* positively identified obsolete entries. Never delete arbitrary directories based on a similar name.
4. Handle dependencies, an unprivileged Minecraft account, systemd units, Cockpit package location, host permissions, and rollback explicitly. No service starts, timer enables, world changes, or destructive migrations by default.
5. Keep optional backup setup interactive/configurable. Verify mount UUID at install time, require an independent mounted volume, respect the systemd `ProtectSystem=strict` read-only parent view, and test writeability in the allowed destination.
6. Automated tests: disposable clean Ubuntu VM, in-place upgrade of a staged older installation, idempotent second install, deliberate duplicate-module scenario, failure/rollback injection, syntax/static validation, and archive restore drill.
7. Security review: sanitize repository and tag history; exclude API keys, RCON and Restic credentials, local config, personal paths, server archives, worlds, and logs. Review code execution through privileged helpers.
8. Pick and add an explicit LICENSE before inviting third-party redistribution. Don't describe incomplete loader provisioning as fully supported.
9. Produce signed/checksummed source archives, installation guide, upgrade/rollback notes, changelog, and GitHub Release *after* gates pass.

## Immediate commands

```bash
bash tools/release-preflight.sh
bash tools/release-preflight.sh --host
```

These are **read-only audits**. A failure is a release blocker, not permission to install or delete.

## User-facing policy

Use generic "Minecraft Manager" installer and status language. Existing named server types are retained as supported server features; do not modify/delete a user's configured servers just to remove installer branding.
