# Host permissions and upgrade acceptance

Verified on Ubuntu 26.04 host (2026-10-16):

- `/usr/local/libexec` is root-owned with mode `0700`. Unprivileged inventory correctly returns `PermissionError`; it must not classify inaccessible files as missing.
- Root inspection confirms all 11 repository backend helpers are already installed at their intended paths.
- A single canonical Cockpit Minecraft Manager manifest was found at `/usr/local/share/cockpit/minecraft-manager/manifest.json`.
- The seven read-only inventory tests passed. Neither this observation nor the tests authorizes applying an upgrade.

## Installer requirements

The future `--check` command should explicitly differentiate privileged and unprivileged inspections. `--apply` requires root, but the installer should not chmod privileged helper directories to make inventory convenient.

Before any write, it must verify source revision, complete dependencies, path boundaries, symlink/TOCTOU protections, a durable transaction backup, reversible file manifest, and staged tests. Preserve server state, worlds, credentials, backup data, existing timer state and other Cockpit modules. Refuse changes when a transaction cannot be rolled back.

Never automatically delete a Cockpit module just because its name looks old. The canonical module is an upgrade-in-place target; other modules require evidence of ownership and an explicit action.

## Tests still required

- Transaction engine against isolated temporary directories (failure injection + rollback verification).
- Clean disposable Ubuntu VM dependency and first-install test.
- Installed-host upgrade staging with full installed files, not sanitized repository snapshots.
- Idempotency, power interruption recovery, permission denial, and symlink replacement tests.
- Functional Cockpit UI validation and independent backup-restore drill.

Do not publish a production-ready release or unblock root `install.sh --apply` before these tests pass.
