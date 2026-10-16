# Cockpit Minecraft Manager

A self-hosted Minecraft server-management interface for [Cockpit](https://cockpit-project.org/) on Linux, under active development.

> **v1.2 release candidate.** The unified installer supports an explicit opt-in file-only transaction with rollback, but has not yet passed final validation on a disposable Ubuntu host and the existing production installation. Advanced tools require per-host services, mounts, users and configuration. Do not install on a critical system without reviewing the change plan and keeping an independent backup.

## Screenshots

A tour of the current Cockpit Minecraft Manager interface. Select an image to view it full size. Some server labels and paths shown are examples from the development environment.

<a href="docs/screenshots/OverviewPage.png"><img src="docs/screenshots/OverviewPage.png" alt="Overview page" width="48%"></a>
<a href="docs/screenshots/FilePage.png"><img src="docs/screenshots/FilePage.png" alt="Files page" width="48%"></a>
<a href="docs/screenshots/BackupPage.png"><img src="docs/screenshots/BackupPage.png" alt="Backups page" width="48%"></a>
<a href="docs/screenshots/PlayersPage.png"><img src="docs/screenshots/PlayersPage.png" alt="Players page" width="48%"></a>
<a href="docs/screenshots/AdvancedControlCenterPage.png"><img src="docs/screenshots/AdvancedControlCenterPage.png" alt="Advanced Control page" width="48%"></a>
<a href="docs/screenshots/PlayerRecordsAndStoragePage.png"><img src="docs/screenshots/PlayerRecordsAndStoragePage.png" alt="Player Records & Storage page" width="48%"></a>
<a href="docs/screenshots/PerformancePage.png"><img src="docs/screenshots/PerformancePage.png" alt="Performance page" width="48%"></a>
<a href="docs/screenshots/RestartsAndResourcesPage.png"><img src="docs/screenshots/RestartsAndResourcesPage.png" alt="Restarts & Resources page" width="48%"></a>
<a href="docs/screenshots/CreateServerPage.png"><img src="docs/screenshots/CreateServerPage.png" alt="Create Server page" width="48%"></a>
<a href="docs/screenshots/ModPackPage.png"><img src="docs/screenshots/ModPackPage.png" alt="Modpacks page" width="48%"></a>

See the [complete screenshot gallery](docs/SCREENSHOTS.md).

## Current console functionality

- Browse and control independent managed Minecraft servers.
- Create Vanilla, Spigot, Paper, and Purpur instances (subject to upstream availability).
- View console logs and manage select configuration and backup tasks.
- Support additional server operations through optional locally installed helper programs.

## Modpack Center roadmap

- CurseForge catalog browsing and release metadata (subject to API approval).
- Import a supported Minecraft server-pack ZIP and inspect its contents.
- Forge, NeoForge, Fabric, and Quilt server provisioning after loader verification.
- Mod dependency checks, custom modpack manifests and RAM guidance.
- Pre-update backups, snapshots, rollback, mod management, and log inspection.

**Modpack automation is experimental and incomplete; it is not represented as ready for general installation.** CurseForge API access does not guarantee permission to download/rehost any particular file. Respect authors' permissions, license terms, and API restrictions.

## Repository layout

- `cockpit/minecraft-manager/`: Cockpit frontend source.
- `backend/cockpit-minecraft-helper`: existing privileged Python helper snapshot.
- `docs/`: application, security, and development notes.

## Installation

The installer finds its files relative to its own location, so you can run it from Downloads or another extracted directory (keep the complete folder intact). Cockpit must already be installed and active.\n\n```bash\nbash "/path/to/extracted/install.sh" --check --host\nsudo bash "/path/to/extracted/install.sh" --plan\n```\n\nSee [installation, recovery, and limitations](docs/INSTALL_V12.md) for the gated install, rollback and finalization commands. The installer does not modify existing systemd units, timers, world data, backup mounts or credentials.

### Run from any download location

The installer finds its project files relative to its own location; your working directory does not matter. Extract the **entire** release archive (not just `install.sh`) and invoke the script by its path:

```bash
bash "/path/to/extracted release/install.sh" --check
```

The v1.2 development branch currently supports read-only checks only. `--apply` is deliberately blocked until production upgrade and rollback validation is complete.

## Security and privacy

Do not commit API keys, RCON credentials, Restic password files, `server.properties`, worlds, server logs, hostnames/IPs, or real server archives. Store any future CurseForge API key in root-readable host configuration rather than frontend JavaScript. Review [SECURITY.md](SECURITY.md).

## Status

Personal, non-commercial educational project. Public GitHub repository is intended for development transparency and CurseForge API application review, not as a mod-file distribution service.

## License

This repository uses a [proprietary source-available license](LICENSE); it is not open source. Official unmodified releases can be downloaded, installed and evaluated privately as specified in that license.


> **Development-source warning:** This review snapshot includes all 11 examined Python helpers but is not a complete tested installer. Before any public release, verify runtime dependencies, credential handling, systemd units, platform portability, and all Git history. See `docs/AUDIT_REVIEW.md`.
