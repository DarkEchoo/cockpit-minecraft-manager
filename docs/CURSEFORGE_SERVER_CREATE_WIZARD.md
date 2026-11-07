# Create Server from a CurseForge release — review-stage wizard

The **Modpacks** tab now displays **Create Minecraft server…** after choosing a release under **Details / versions → Load release versions**.

The wizard collects:
- Unique server ID, absolute installation directory, and port (0 means choose later)
- Maximum Java heap in GiB, and a requested CPU-equivalent core count
- An existing Restic backup repository, schedule (Off / hourly / every 6 or 12 hours / daily / weekly / custom) and custom interval
- Optional restore export directory and Minecraft EULA acknowledgement

**Current status: planning only.** The **Review server setup** button validates the selected CurseForge project/file ID pairing and the requested settings, checks for existing destinations and managed-server name collisions, and reports whether the selected release advertises an associated server-pack file. It does not create directories, download modpacks, execute launchers, register or start systemd services, or change backups.

The plan is deliberately not treated as a successful install. A CurseForge modpack release frequently represents a client archive rather than a runnable server. NeoForge/Forge packs may require version-specific installers and launch arguments, and plugin-managed worlds must not be overwritten. No automatic `Create` operation is exposed until these steps have a separately tested and permission-gated transaction with rollback. For installed servers, CPU limits in the existing manager are runtime systemd quotas (100% per CPU equivalent), not guaranteed dedicated pinned physical cores; this wizard's CPU choice is a **proposed limit**, not a currently applied setting.

For existing servers, continue using the current server-management, backup, and resource controls. To install only browser updates on the user's customized Cockpit environment:

```bash
cd ~/Documents/cockpit-minecraft-manager
git pull --ff-only
sudo bash tools/upgrade-curseforge-search-icons-live.sh --apply
```

The incremental updater backs up `modpacks.js`, `styles.css`, the independent CurseForge browser helper and `manifest.json`, and preserves unrelated custom pages and installed Minecraft helpers. Do **not** use the incomplete full v1.2 installer for this change.
