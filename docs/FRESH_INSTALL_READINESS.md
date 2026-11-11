# Clean Ubuntu installation: release-readiness gate

This repository currently has a **file-only transactional updater**, not a
complete first-install provisioning system. A successful `install.sh --check`
or `--plan` does **not** mean the app can run on a blank host.

## Read-only assessment

From the complete repository checkout:

```bash
python3 tools/fresh-install-audit.py
python3 tools/fresh-install-audit.py --host
python3 tools/fresh-install-audit.py --host --json
bash install.sh --check --host
sudo bash install.sh --plan
```

The fresh-install audit exits **2** when its basic checks pass but first-install
support is still incomplete. It exits **1** if required files or tools are
missing. This is intentional: do not treat its failure as permission to
skip a check.

## Requirements before publishing an install-for-anyone release

1. Create a dedicated non-login `minecraft` account/group with safe ownership.
2. Package a least-privilege authorization path for the privileged helper.
3. Replace hard-coded development-host paths and provide secure host setup.
4. Validate and provision required systemd units without touching user services.
5. Provide a supported game-server directory, never overwrite existing worlds.
6. Gate optional features on their dependencies and host configuration.
7. Test clean install, upgrade, failure recovery, rollback, and uninstall in a
   disposable supported Ubuntu VM.

**Do not commit** server.properties, RCON passwords, Restic password files,
CurseForge tokens, host-specific mounts, service credentials, logs, worlds,
backups, or home-directory exports. Keep API tokens in protected on-host files.

## Existing installations

`sudo bash install.sh --apply --accept` is an opt-in **application-file**
transaction. It deliberately preserves several host-customized files and does
not create users, services, secret files, storage, or Minecraft servers.
It is not a substitute for a fresh-host installer. Read
[INSTALL_V12.md](INSTALL_V12.md) before applying it to an existing machine.

Do not merge the release branch into `main` or advertise one-command general
installation until clean-host verification passes.
