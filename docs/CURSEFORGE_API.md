# CurseForge API integration plan

CurseForge API integration is being developed for catalog search, mod metadata, dependency checks, and permitted installations for self-managed Minecraft servers.

A key must be provided by an authorized API account holder and stored on the Linux host, outside files served by Cockpit. Respect file-author download permissions and API quotas. When a file is not authorized for automated download, direct the user to its official CurseForge page. Do not redistribute files or create a mirror.

Modpack client manifests are not by themselves runnable server packs. Server deployment must validate the corresponding installer/runtime and ensure a functional loader with an appropriate launch command.
