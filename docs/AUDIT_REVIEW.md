# Review of 11 backend helpers (development snapshot)

All 11 Python files passed AST parsing. Identifiable machine-specific values were found in the main helper, `cockpit-minecraft-join-control`, and the Restic integration for `cockpit-minecraft-records`. They were replaced or made configurable in this review copy. The CurseForge code reads an API key from a path; it does **not** contain a key value.

This review is **not** a complete security audit, penetration test, working installer, or promise of runtime compatibility. In particular, the project still relies on system-specific service names and external helper binaries; the source does not include all unit files or a reviewed deployment procedure. Some code paths perform privileged operations.

Do not deploy this bundle over an existing host, force-push over Git history, or publish it without independent review of source and history. Original public commit metadata, previously accessible to others, cannot be guaranteed erased by rewriting Git history.
