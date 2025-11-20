# Troubleshooting Matrix

Use this quick-reference matrix to diagnose common configuration hiccups. Each row links to the
relevant implementation so you can double-check the underlying behavior before diving deeper into
logs or interactive debugging sessions.

| Symptom | Checks | Notes |
| --- | --- | --- |
| SQLCipher connection fails or the SQLite URL is treated as a file path instead of a URI | 1. Confirm `POCKETSAGE_USE_SQLCIPHER=true` in the environment.<br>2. Instantiate `BaseConfig().sqlalchemy_engine_options()` during startup to verify `uri=True`.<br>3. Ensure your SQLCipher key material is available via `POCKETSAGE_SQLCIPHER_KEY` (once the handshake TODO is implemented). | `BaseConfig.sqlalchemy_engine_options()` flips `connect_args["uri"]` to `True` when SQLCipher mode is enabled so SQLAlchemy treats the database URL (with cipher query params) as a URI. The method also exposes a top-level `execution_options` mapping that future SQLCipher pragma handshakes will populate with key negotiation details without polluting the SQLite `connect_args`. |

## SQLCipher Engine Option Details

`BaseConfig.sqlalchemy_engine_options()` always returns a dictionary compatible with `SQLModel.create_engine`. The default path
keeps `connect_args["uri"] = False` for plain SQLite files. When `POCKETSAGE_USE_SQLCIPHER` is true, the method performs two
important adjustments:

1. **URI toggle** – `connect_args["uri"]` switches to `True`, signalling SQLAlchemy to respect the full SQLite URI string (including the `?cipher=sqlcipher` query string) instead of collapsing it to a filesystem path.
2. **Execution options scaffold** – An empty `execution_options` dictionary is created alongside the connect args so that upcoming SQLCipher integrations can inject pragma/key handshake options without interfering with the low-level SQLite connection parameters.

## Verifying at Runtime

To confirm these settings while the desktop app (or tests) are running:

- Add a one-time log statement during startup:
  ```python
  from pocketsage.config import BaseConfig

  cfg = BaseConfig()
  print("Engine options:", cfg.sqlalchemy_engine_options())
  ```
  With SQLCipher toggled on, the output should include `{"connect_args": {"check_same_thread": False, "uri": True}, "execution_options": {}}`.

These quick checks keep the SQLCipher pathway verifiable even before the full key exchange TODOs are implemented.
