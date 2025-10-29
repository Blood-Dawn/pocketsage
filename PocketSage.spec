# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

block_cipher = None

project_root = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()

# Mirror the local runner entry point used by `python run.py`.
entry_script = project_root / "run.py"

pocketsage_pkg = project_root / "pocketsage"

data_files = [
    (str(pocketsage_pkg / "templates"), "pocketsage/templates"),
    (str(pocketsage_pkg / "static"), "pocketsage/static"),
]

hidden_imports = [
    "pocketsage.blueprints.admin",
    "pocketsage.blueprints.habits",
    "pocketsage.blueprints.ledger",
    "pocketsage.blueprints.liabilities",
    "pocketsage.blueprints.portfolio",
]

analysis = Analysis(
    [str(entry_script)],
    pathex=[str(project_root)],
    binaries=[],
    datas=data_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="PocketSage",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PocketSage",
)
