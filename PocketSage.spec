# -*- mode: python ; coding: utf-8 -*-

import importlib
import sys
from pathlib import Path

block_cipher = None

project_root = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()

sys.path.insert(0, str(project_root))

pocketsage_pkg = project_root / "pocketsage"

blueprint_modules = [
    "pocketsage.blueprints.admin",
    "pocketsage.blueprints.habits",
    "pocketsage.blueprints.home",
    "pocketsage.blueprints.ledger",
    "pocketsage.blueprints.liabilities",
    "pocketsage.blueprints.portfolio",
]


def iter_blueprint_template_dirs(modules: list[str]):
    """Yield (source, destination) tuples for blueprint template folders."""

    seen = set()
    for module_name in modules:
        module = importlib.import_module(module_name)
        blueprint = getattr(module, "bp", None)
        template_folder = getattr(blueprint, "template_folder", None) if blueprint else None
        if not template_folder:
            continue

        template_dir = (Path(blueprint.root_path) / template_folder).resolve()
        if not template_dir.is_dir() or template_dir in seen:
            continue

        seen.add(template_dir)
        try:
            rel_dest = template_dir.relative_to(pocketsage_pkg)
        except ValueError:
            continue

        yield (str(template_dir), f"pocketsage/{rel_dest.as_posix()}")


shared_template_files = sorted(
    path
    for path in (pocketsage_pkg / "templates").iterdir()
    if path.is_file()
)


data_files = [
    *sorted(iter_blueprint_template_dirs(blueprint_modules), key=lambda entry: entry[1]),
    *(
        (str(path), f"pocketsage/templates/{path.name}")
        for path in shared_template_files
    ),
]

static_dir = pocketsage_pkg / "static"
if static_dir.is_dir():
    data_files.append((str(static_dir), "pocketsage/static"))

hidden_imports = [
    "pocketsage.blueprints.admin",
    "pocketsage.blueprints.habits",
    "pocketsage.blueprints.home",
    "pocketsage.blueprints.ledger",
    "pocketsage.blueprints.liabilities",
    "pocketsage.blueprints.portfolio",
]

analysis = Analysis(
    [str(project_root / "run.py")],
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
