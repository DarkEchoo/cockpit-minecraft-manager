# Cockpit Minecraft Manager v1.2 installation and recovery

> Release-candidate workflow. Do not install on a critical server without verifying the inventory, backups, and rollback on a disposable Ubuntu host first.

## Prerequisites

- Ubuntu with Cockpit installed and `cockpit.socket` active
- Python 3, Bash, and standard system utilities
- Root privileges for modifying `/usr/local`
- The **entire** extracted source/release folder (the installer cannot run as an isolated file)

The installer derives all source paths from `install.sh`, never from the shell's current working directory. For example, this works even when invoked from a different directory:

```bash
sudo bash "/home/youruser/Downloads/Minecraft Console/install.sh" --plan
```

## Deployment

Run the read-only checks first:

```bash
bash "/path/to/extracted/install.sh" --check --host
sudo bash "/path/to/extracted/install.sh" --plan
```

After evaluating the plan and creating your own external backup, the explicit opt-in installation command is:

```bash
sudo bash "/path/to/extracted/install.sh" --apply --accept
```

The installer validates Cockpit, creates a SHA-256-verified staging package, backs up every existing application file it will replace, and atomically installs application files in:

- `/usr/local/share/cockpit/minecraft-manager`
- `/usr/local/libexec`

It refuses symbolic-link destinations, unrelated data locations, competing installer processes, and an outstanding installation journal. Application files are restored with their previous mode and ownership on rollback.

**The installer does not stop, restart, start, or enable any Minecraft service or timer.** It does not overwrite existing systemd unit files or touch server worlds, Restic repositories, credentials, Minecraft server configuration or backup schedules.

Host-customized default-port proxies, join announcers and manual-backup helpers are preserved if already installed.

## Post-install verification and recovery

The installer retains its on-disk backup journal after installing. Inspect the console and verify all enabled features before committing the update:

```bash
sudo bash "/path/to/extracted/install.sh" --finalize
```

To roll back application files to their previous state instead:

```bash
sudo bash "/path/to/extracted/install.sh" --rollback
```

Retain the same installer folder until verification is complete. If the process is interrupted, **do not delete** `/var/lib/cockpit-minecraft-manager/installer/pending`; use rollback to recover. Recovery refuses unrecognized subsequent file modifications rather than overwriting them silently. Make a separate system backup before a major upgrade.

## Fresh-install limitations

A freshly installed console does not automatically create a Minecraft server, user account, server-specific systemd units, Restic repository, mount point, RCON password, or monitoring config. Advanced controls work only after those supported per-host prerequisites are configured.

Optional unit examples live under `addons/service-reference/`, and backup unit templates under `addons/backup-manager/systemd/`. They are **not installed or enabled automatically**. Review users, command paths, expected permissions and secret/config file locations before enabling any template.

Manual Restic backups require the root-owned configuration file `/etc/minecraft-backup/manual-backup.conf`; the supplied helper refuses to stop a server unless `MC_BACKUP_ALLOW_STOP=yes` is explicitly set. Never commit a populated configuration file or secret to GitHub.

For a server with existing custom services, preserve the original unit definitions and settings rather than replacing them with generic examples.
