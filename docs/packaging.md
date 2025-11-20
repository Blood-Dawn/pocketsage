# PocketSage Packaging Guide

## Desktop builds (Flet Pack)
- Use `make package` to run `flet pack run_desktop.py` with product metadata; binaries land in `dist/`.
- Platform scripts: `bash scripts/build_desktop.sh` (Linux/macOS) or `scripts\build_desktop.bat` (Windows). They create a venv, install deps, run tests, and call `flet pack`.
- Outputs: Windows `dist\PocketSage\PocketSage.exe`, macOS `dist/PocketSage.app`, Linux `dist/PocketSage/PocketSage`.

## Packaging checklist
- [ ] Ensure dependencies (including `flet`) are installed in the active environment.
- [ ] Run `make test` (or let the build scripts run pytest) before packaging.
- [ ] Verify `POCKETSAGE_DATA_DIR` points to a writable location; the packager will embed the current default.
- [ ] Smoke test the produced binary to confirm it launches and reads/writes the SQLite DB under the resolved data dir.
