# CurseForge browser in v1.2

The Modpack tab's CurseForge discovery panel now has artwork cards, author/download summaries, a Minecraft version dropdown fetched from CurseForge's Core API, a detailed project view with a plain-text description, and a list of the most recent 50 release files. Selecting a release populates the existing project/file ID fields used by **Add compatible file to planning manifest**.

The browser works for both **Modpacks** and **Individual mods**. A selection is metadata-only and does not install any mod, modpack, server, or loader. Server installation continues to require a compatible validated server package.

## Key setup

Obtain an approved **CurseForge Core API** key from the developer portal. **Never post the key in a chat, shell command, or repository.** If a key has been shared, rotate it before installation.

The backend reads only `/etc/cockpit-minecraft/curseforge-api-key`, which must be a regular root-controlled file with permission `0600`. Keep the key out of the Cockpit HTML, JavaScript, Git repository, and service command lines.

The independent helper `/usr/local/libexec/cockpit-minecraft-curseforge-browser` handles all new remote searches and returns only selected public project metadata to the interface. It makes no filesystem changes or downloads, and it does not expose the key.

The separate helper is deliberate: existing hosts may have customized `cockpit-minecraft-modpacks` functionality that the installer must preserve. The browser does not replace that helper.

Images are permitted only from a short HTTPS CurseForge media-domain allowlist. Descriptions are shown as text rather than inserting API HTML into the Cockpit page. Browser availability also depends on the local Cockpit content-security policy permitting CurseForge media images.

## API behavior

Uses the CurseForge Core API endpoints:

- `GET /v1/minecraft/version` for version choices.
- `GET /v1/mods/search` for pack/mod search with category and optional version.
- `GET /v1/mods/{id}` and `GET /v1/mods/{id}/description?stripped=true` for details.
- `GET /v1/mods/{id}/files` for recent release metadata.

Version lists in project details are computed from recent file metadata; they are **not** guaranteed to represent all historical Minecraft versions or compatible modloader combinations. The user must verify loader, required dependencies, client/server suitability, and file permissions before any install.
