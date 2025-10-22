# Operations Guide

## Secure export directory handling

PocketSage writes CSV and PNG artifacts to a staging directory before bundling them into downloadable ZIP archives. The `_ensure_secure_directory` helper ensures this directory exists before writing:

* The function always creates the directory (and any missing parents) before exports begin.
* After creation, it attempts to set permissions to `0700`, restricting read, write, and execute access to the PocketSage process owner only. 【F:pocketsage/pocketsage/blueprints/admin/tasks.py†L43-L55】

### Platform caveats

`os.chmod` is a best-effort operation. On Windows hosts or filesystems that do not support POSIX-style permission bits, `_ensure_secure_directory` silently ignores `NotImplementedError` and `PermissionError`. In those environments, administrators should fall back to the host's native access control mechanisms (e.g., NTFS ACLs) to restrict export directories. 【F:pocketsage/pocketsage/blueprints/admin/tasks.py†L51-L55】

## Troubleshooting export permission issues

If exports fail or files are missing from the expected directory:

1. **Validate directory ownership** – Confirm that the PocketSage service account owns the export directory. Adjust with `chown` (Linux/macOS) or the appropriate Windows ACL tooling.
2. **Inspect permissions** – Ensure the directory grants write and execute permissions to the service account. On POSIX systems `chmod 700 <dir>` matches the default expectation. On Windows, grant `Full Control` to the service identity via the Security tab or `icacls`.
3. **Check parent directories** – When exports target a mounted volume or shared folder, verify each parent directory allows traversal (`+x` bit) for the service account.
4. **Recreate the directory** – Delete and allow `_ensure_secure_directory` to recreate the path. This reapplies the secure defaults where supported.
5. **Review application logs** – Permission failures surface as `PermissionError` or `OSError` entries during export. Inspect logs to confirm the failure mode and adjust permissions accordingly.

After correcting permissions, rerun the export task to confirm that ZIP archives are generated in the configured output directory.
