# Updating the repository from an existing Cockpit installation

The development host may contain newer code than GitHub. **Do not copy the
whole /usr/local directory or push your live Cockpit configuration.**

Run the allowlisted inventory tool on the Ubuntu machine:

```bash
python3 tools/collect-live-source.py
```

On the development host, if you don't have a fresh checkout, download only
the collector from the reviewed feature branch:

```bash
curl -fL --proto '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/DarkEchoo/cockpit-minecraft-manager/feature/fresh-install-readiness/tools/collect-live-source.py \
  -o /tmp/collect-live-source.py
python3 /tmp/collect-live-source.py
```

The output lists paths and SHA-256 hashes of application code only. To
prepare a **local review archive**, after checking the script itself:

```bash
python3 /tmp/collect-live-source.py --export "$HOME/Downloads/cockpit-source-review.zip"
```

The export refuses flagged suspicious source lines; **do not disable the checks
just to create an archive**. The checker is not proof that a source file is
free of private information. Before sharing or publishing, inspect all
exported files manually for hostnames, addresses, credentials, local paths,
API keys, and identifiers. Never upload or commit live secrets.

Share the reviewed archive privately for a comparison against the release
branch. Merge only the portable application changes after tests. Source
collector **never runs Git, writes to GitHub, reads server.properties, or
modifies services**.

This only covers the allowlisted application source. Additional dynamically
installed add-ons must be audited individually and added deliberately.
