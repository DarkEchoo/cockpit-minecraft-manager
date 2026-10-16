# Local configuration for development

The source code accepts some runtime environment variables. This is **not yet an installer-ready release**. Privileged Cockpit processes do not automatically inherit ordinary shell environment variables. Configure them through a reviewed service/launch mechanism for your deployment. Do not commit local settings or password files.

- `COCKPIT_MC_MANAGED_BASE`: managed server directory.
- `COCKPIT_MC_EXISTING_SERVER`: NeoForge server directory.
- `COCKPIT_MC_BACKUP_REPO`: existing Restic repository (required for legacy backup verification).
- `COCKPIT_MC_BACKUP_MOUNT`: expected mounted filesystem.
- `COCKPIT_MC_BACKUP_UUID`: expected filesystem UUID. Do not disable the UUID check.
- `COCKPIT_MC_RESTIC_PASSWORD_FILE`: password file path, **not** the password.
- `COCKPIT_MC_JOIN_UNIT`: allowed join-announcer server unit; explicit selection required.
- `COCKPIT_MC_JOIN_PROPERTIES`: allowed properties file; explicit selection required.

The project currently has fixed assumptions about `minecraft-26.service`, `/opt/minecraft`, systemd paths, and other locally supplied services. Generalizing these and providing a safe first-time installer remain open work.
