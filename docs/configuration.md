# Configuration Guide

PocketSage centralizes runtime settings in `pocketsage/config.py`, exposing
helpers for environment toggles and SQLAlchemy engine setup. The following
sections document how to enable SQLCipher support and what to expect from the
current implementation.

## SQLCipher Environment Flags

PocketSage reads configuration from `.env` files and process environment
variables. SQLCipher-specific behavior is controlled by the following keys:

| Variable | Purpose |
| --- | --- |
| `POCKETSAGE_USE_SQLCIPHER` | Enables SQLCipher-specific URL building and engine tweaks when set to `true`. |
| `POCKETSAGE_DATABASE_URL` | Overrides the computed SQLite or SQLCipher URL entirely. |
| `POCKETSAGE_DATA_DIR` | Redirects where generated database files live. |
| `POCKETSAGE_SQLCIPHER_KEY` | Holds key material that future SQLCipher handshakes will consume. |

`BaseConfig` exposes these toggles via helper constants. `SQLCIPHER_FLAG`
points to `POCKETSAGE_USE_SQLCIPHER`, `_env_bool()` resolves it into the boolean
`USE_SQLCIPHER`, and `SQLCIPHER_KEY_ENV` signals where to load optional key
material.

## `_build_sqlite_url`

`BaseConfig._build_sqlite_url()` produces a SQLite database URL from the
resolved data directory. In the default mode the function returns a simple
`sqlite:///` path. When `USE_SQLCIPHER` evaluates to `True`, the method switches
into SQLCipher mode and appends query parameters so that SQLAlchemy treats the
URL as a SQLCipher-ready URI. Follow-up TODOs in the method document the pending
swap to the SQLCipher driver package and connection PRAGMAs once dependencies
land.

## `sqlalchemy_engine_options`

`BaseConfig.sqlalchemy_engine_options()` always disables SQLite's same-thread
check to accommodate background jobs. When SQLCipher mode is active it also:

- Forces `uri=True` so SQLAlchemy parses the URL as a full URI with query
  options.
- Prepares an `execution_options` dictionary for future SQLCipher handshake
  hooks.
- Notes that the key stored in `POCKETSAGE_SQLCIPHER_KEY` will eventually be
  injected via PRAGMA statements once the SQLCipher integration is complete.

Together these toggles ensure that enabling `POCKETSAGE_USE_SQLCIPHER` sets up
the database URL and engine with the expected SQLCipher scaffolding while the
remaining TODO items track the final encryption handshake.
