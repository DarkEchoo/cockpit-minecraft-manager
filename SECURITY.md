# Security

This project includes a Cockpit UI and a privileged local helper. Treat security defects as potentially serious.

- Never store credentials in frontend code or git history.
- Restrict privileged helper input and access; review all changes before deploying.
- Do not run arbitrary modpack install scripts or downloaded JARs as root.
- Verify archive paths and refuse symlinks and path traversal before extraction.
- Keep server files, logs, backup repositories, passwords, and API keys outside Git.
- Report potential vulnerabilities privately to the repository maintainer through GitHub if security advisories are enabled.

This snapshot has not had a complete independent security audit.
