# CurseForge API key configuration

**Each installer should use their own CurseForge API key.** Never embed,
obfuscate, base64-encode, or ship an author's private API key inside a public
Cockpit module, Python helper, frontend bundle, installer, or Git repository.
Obfuscation is reversible by anyone who installs the code.

The backend already reads the key from:
`/etc/cockpit-minecraft/curseforge-api-key`.

## Set up a key on your own Ubuntu host

Review the configuration tool before running it. From a trusted checkout:

```bash
sudo python3 tools/configure-curseforge-key.py
```

The key prompt hides input and does not put the secret in shell history or
a command-line argument. The resulting file is owned by root and permissioned
`0600`; the existing privileged backend reads the file locally and sends
the key only to the official CurseForge API in an HTTPS request header.

If you already have a working key, **do nothing**. The setup utility refuses
to overwrite it without explicit `--replace`.

To rotate a key you control:

```bash
sudo python3 tools/configure-curseforge-key.py --replace
```

Restart only a service that actually caches the key if necessary; current
request-time helper reads need no service restart.

If the key is absent, CurseForge API-backed browsing is unavailable; manual
modpack ZIP import may still be available. A key is not needed to install
Cockpit Minecraft Manager's code.

Do not paste a key into chat, GitHub issues, or test fixtures. Do not include
the key file when exporting source, publishing release archives, or running
repository synchronization.

## Security reminders

- Root-readable means people who have root access to the host can read the key.
- Frontend JavaScript must not read, print, embed, or receive the API key.
- Avoid printing request headers or API error payloads that could contain
  credentials; errors sent to users should be sanitized.
- A file permission check alone does not replace application-level access
  review of Cockpit's privileged bridge.
- If you suspect the key was ever committed or exposed, revoke it at
  CurseForge and provision a fresh one. Removing it from the latest commit
  alone does not erase Git history or copies made by other users.
- A shared public proxy with a hidden author's key would require a separate
  operated backend with authentication, rate limits, abuse prevention,
  monitoring, and approval under the API provider's terms. This repository
  does **not** include such a service.

The file-only release installer does not automatically install this key.
