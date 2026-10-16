# Minecraft Backup Manager add-on v1.1.1

Repo-ready **backup and scheduling add-on** for an existing Cockpit Minecraft Manager installation. This is **not** a standalone installer for Cockpit or a complete Minecraft server manager. It bundles the previously separate v0.8 backup engine, v0.9 backup center, v1.0 scheduler runner and templates, and v1.1 timer controls.

## Requirements

- Ubuntu/Linux, systemd, Python 3.10+, `findmnt` (util-linux), `tar` functionality via Python, existing Cockpit Minecraft Manager with **exactly one** `mp09-panel` and corresponding backup UI script.
- An existing modpack workspace with `modpack.json` and corresponding systemd service in the `mc-managed-<workspace>.service` naming scheme.
- A mounted separate physical backup volume with UUID and an existing backup directory. Requires privileged installer access. `node` is optional for JS validation.
- Existing service must be stopped for backups. This add-on **does not** coordinate live-server saves or install mod loaders.

## Upgrade an existing installation

Keep your current mount and workspace unchanged. For example, edit these values to match your system:

```bash
sudo bash install.sh --check --backup-dir /mnt/backup-disk/Minecraft-Backups --workspace-root /opt/minecraft/modpack-workspaces --workspace test-world
sudo bash install.sh --apply --backup-dir /mnt/backup-disk/Minecraft-Backups --workspace-root /opt/minecraft/modpack-workspaces --workspace test-world
```

The installer discovers the backup filesystem UUID with `findmnt` and saves configuration to `/etc/cockpit-minecraft/backup-manager.json` (root-only). Subsequent upgrades can use `sudo bash install.sh --check` and `--apply` without repeating flags.

No installed Minecraft services are started, stopped, or modified. Installed backup and interface files are copied to a timestamped `/var/backups/cockpit-public-backup-manager-*` directory. The systemd snapshot unit is upgraded in place; its timer remains disabled. **Do not run with an enabled existing timer.**

## Verify

```bash
sudo /usr/local/libexec/cockpit-mc-snapshot check test-world
sudo /usr/local/libexec/cockpit-mc-schedule status test-world
systemctl is-enabled cockpit-mc-snapshot@test-world.timer
```

Run a test backup only after a successful preflight:

```bash
sudo systemctl start cockpit-mc-snapshot@test-world.service
sudo journalctl -u cockpit-mc-snapshot@test-world.service -n 40 --no-pager
```

## Security notes

- Configuration values are **never included in the public archive**. Backup mount identity is checked against a detected UUID. Read-only parent mount options inside `ProtectSystem=strict` are expected; the backup directory is explicitly writable via `ReadWritePaths`.
- Directories are checked for symlinks, service inactivity, and separate filesystems. Automatic deletion and live-server backups remain disabled.
- The scheduler is deliberately restricted to the workspace selected during installation. Other workspaces can be supported in a future release after dedicated validation.
- Do not include `/etc/cockpit-minecraft`, worlds, archives, secrets, actual logs, or local backup files in a Git commit.
- The installer uses your **existing** Cockpit Backup Center as prerequisite. For a first-time complete manager installation, install and configure the main Cockpit Minecraft Manager and Backup Center first. No promise of unattended greenfield installation is made.
