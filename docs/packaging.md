# PocketSage Packaging Guide

## PyInstaller data files

PyInstaller bundles HTML templates and static assets so the packaged
application can render blueprints without accessing the source tree. The
`PocketSage.spec` file automatically gathers the template directories from
registered blueprints:

- `pocketsage/templates/admin`
- `pocketsage/templates/habits`
- `pocketsage/templates/home`
- `pocketsage/templates/ledger`
- `pocketsage/templates/liabilities`
- `pocketsage/templates/portfolio`

Shared layout files such as `_flash.html`, `_nav.html`, and `base.html`
are included individually from the `pocketsage/templates/` root directory.

Static assets are copied via the `pocketsage/static/` directory. Add new
blueprints to both the Flask app and `blueprint_modules` list inside
`PocketSage.spec` so their templates are bundled during packaging.
