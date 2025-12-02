"""Settings view implementation."""
# TODO(@pocketsage-admin): Surface seed/reset progress and final row counts to the user.
# TODO(@pocketsage-settings): Expose instance path and backup status in the UI.

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from ...devtools import dev_log
from ...services import importers
from ...services.admin_tasks import backup_database, restore_database, run_export
from ...services.watcher import start_watcher
from .. import controllers
from ..components import build_app_bar, build_main_layout

if TYPE_CHECKING:
    from ..context import AppContext


def build_settings_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the settings/admin view."""

    def _notify(message: str):
        dev_log(ctx.config, "Settings notice", context={"message": message})
        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        page.update()

    # Theme toggle
    def toggle_theme(e):
        """Toggle between light and dark theme."""
        if page.theme_mode == ft.ThemeMode.DARK:
            page.theme_mode = ft.ThemeMode.LIGHT
            ctx.theme_mode = ft.ThemeMode.LIGHT
            theme_switch.value = False
            ctx.settings_repo.set("theme_mode", "light", "Preferred theme mode")
        else:
            page.theme_mode = ft.ThemeMode.DARK
            ctx.theme_mode = ft.ThemeMode.DARK
            theme_switch.value = True
            ctx.settings_repo.set("theme_mode", "dark", "Preferred theme mode")
        page.update()

    theme_switch = ft.Switch(
        label="Dark Mode",
        value=page.theme_mode == ft.ThemeMode.DARK,
        on_change=toggle_theme,
    )

    # Database info
    db_path = ctx.config.DATA_DIR / ctx.config.DB_FILENAME

    # Build settings sections
    appearance_section = ft.Card(
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Appearance", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(height=16),
                    theme_switch,
                ],
            ),
            padding=20,
        ),
        elevation=2,
    )

    def export_data(_):
        try:
            exports_dir = ctx.config.DATA_DIR / "exports"
            path = run_export(
                Path(exports_dir),
                session_factory=ctx.session_factory,
                user_id=ctx.require_user_id(),
                retention=ctx.config.EXPORT_RETENTION if hasattr(ctx.config, "EXPORT_RETENTION") else 5,
            )
            _notify(f"Export ready: {path}")
        except Exception as exc:
            dev_log(ctx.config, "Export failed", exc=exc)
            _notify(f"Export failed: {exc}")

    def backup_db(_):
        try:
            backups_dir = ctx.config.DATA_DIR / "backups"
            path = backup_database(backups_dir, config=ctx.config)
            _notify(f"Backup saved: {path}")
        except Exception as exc:
            dev_log(ctx.config, "Backup failed", exc=exc)
            _notify(f"Backup failed: {exc}")

    restore_picker = ft.FilePicker()

    def restore_db(_):
        restore_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["db", "zip"],
        )

    def _on_restore(e: ft.FilePickerResultEvent):
        selected = e.files[0] if e.files else None
        if not selected or not selected.path:
            return
        try:
            target = restore_database(Path(selected.path), config=ctx.config)
            _notify(f"Database restored to {target}; restart app to reload.")
        except Exception as exc:
            dev_log(ctx.config, "Restore failed", exc=exc, context={"path": selected.path})
            _notify(f"Restore failed: {exc}")

    restore_picker.on_result = _on_restore
    if page.overlay is None:
        page.overlay = []
    page.overlay.append(restore_picker)

    # Watched folder imports
    watcher_picker = ft.FilePicker()
    if page.overlay is None:
        page.overlay = []
    page.overlay.append(watcher_picker)
    watcher_label = ft.Ref[ft.Text]()
    watch_target: dict[str, str | None] = {"target": None, "filename": None}

    def _stop_watcher():
        if ctx.watcher_observer:
            try:
                ctx.watcher_observer.stop()
            except Exception:
                pass
            ctx.watcher_observer = None
            ctx.watched_folder = None
            watch_target["target"] = None
            watch_target["filename"] = None
        if watcher_label.current:
            watcher_label.current.value = "Watcher stopped"
            watcher_label.current.update()
        dev_log(ctx.config, "Watcher stopped")

    def _start_watcher(folder: Path):
        _stop_watcher()
        target_folder = folder if folder.is_dir() else folder.parent
        watch_filename = folder.name if folder.is_file() else None

        def _import_file(csv_path: Path):
            if watch_filename and csv_path.name != watch_filename:
                dev_log(
                    ctx.config,
                    "Watcher ignored file",
                    context={"expected": watch_filename, "seen": csv_path.name},
                )
                return
            try:
                created = importers.import_ledger_transactions(
                    csv_path=csv_path,
                    session_factory=ctx.session_factory,
                    user_id=ctx.require_user_id(),
                )
                dev_log(
                    ctx.config,
                    "Watcher imported file",
                    context={"path": csv_path, "created": created},
                )
            except Exception as exc:
                dev_log(ctx.config, "Watcher import failed", exc=exc, context={"path": csv_path})
                if ctx.dev_mode:
                    _notify(f"Auto-import failed: {exc}")

        try:
            observer = start_watcher(
                folder=target_folder, importer=_import_file, allowed_filename=watch_filename
            )
            ctx.watcher_observer = observer
            ctx.watched_folder = str(target_folder)
            watch_target["target"] = str(target_folder)
            watch_target["filename"] = watch_filename
            if watcher_label.current:
                watcher_label.current.value = (
                    f"Watching file {watch_filename} in {target_folder}"
                    if watch_filename
                    else f"Watching folder: {target_folder}"
                )
                watcher_label.current.update()
            _notify(
                f"Watching {'file' if watch_filename else 'folder'} for CSV imports: {folder}"
            )
        except Exception as exc:
            dev_log(ctx.config, "Watcher start failed", exc=exc, context={"folder": folder})
            _notify(f"Watcher failed: {exc}")

    def _on_watch_pick(e: ft.FilePickerResultEvent):
        selected = e.files[0] if e and e.files else None
        if selected and selected.path:
            _start_watcher(Path(selected.path))
        else:
            dev_log(ctx.config, "Watcher pick canceled or empty")

    watcher_picker.on_result = _on_watch_pick

    def choose_watch_target(_):
        watcher_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["csv"],
        )

    data_dir_field = ft.TextField(
        label="Current data directory",
        value=str(ctx.config.DATA_DIR),
        read_only=True,
        border=ft.InputBorder.UNDERLINE,
        expand=True,
    )

    encryption_switch = ft.Switch(
        label="Encrypt database (SQLCipher-ready)",
        value=bool(getattr(ctx.config, "USE_SQLCIPHER", False)),
        disabled=False,
        on_change=lambda _: _notify(
            "Configure POCKETSAGE_USE_SQLCIPHER and POCKETSAGE_SQLCIPHER_KEY then restart to enable encryption."
        ),
    )

    database_section = ft.Card(
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Database", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(height=16),
                    ft.Row(
                        controls=[
                            ft.Text("Database Path:", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(str(db_path), size=14, selectable=True),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=8),
                    data_dir_field,
                    ft.Container(height=8),
                    encryption_switch,
                    ft.Text(
                        "Encryption is optional; set SQLCipher env vars and restart to apply.",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Container(height=8),
                    ft.Row(
                        controls=[
                            ft.FilledButton(
                                "Backup Database",
                                icon=ft.Icons.BACKUP,
                                on_click=backup_db,
                            ),
                            ft.FilledButton(
                                "Export Data",
                                icon=ft.Icons.DOWNLOAD,
                                on_click=export_data,
                            ),
                            ft.TextButton(
                                "Restore from backup (.db)",
                                icon=ft.Icons.RESTORE,
                                on_click=restore_db,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Text(
                        "To change data directory, set POCKETSAGE_DATA_DIR and restart. Backups can be restored here.",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Text(
                        f"Export retention: {ctx.config.EXPORT_RETENTION} archives (configure in config).",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
            ),
            padding=20,
        ),
        elevation=2,
    )

    about_section = ft.Card(
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("About", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(height=16),
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.ACCOUNT_BALANCE_WALLET, size=48, color=ft.Colors.PRIMARY
                            ),
                            ft.Container(width=16),
                            ft.Column(
                                controls=[
                                    ft.Text("PocketSage", size=20, weight=ft.FontWeight.BOLD),
                                    ft.Text(
                                        "Version 0.1.0", size=14, color=ft.Colors.ON_SURFACE_VARIANT
                                    ),
                                    ft.Text(
                                        "Offline-first finance and habit tracking",
                                        size=14,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            padding=20,
        ),
        elevation=2,
    )

    # Data section
    data_section = ft.Card(
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Data Management", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(height=16),
                    ft.Text(
                        "Manage your data and imports",
                        size=14,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Container(height=16),
                    ft.Row(
                        controls=[
                            ft.FilledButton(
                                "Import Transactions",
                                icon=ft.Icons.UPLOAD_FILE,
                                on_click=lambda _: controllers.start_ledger_import(ctx, page),
                            ),
                            ft.FilledButton(
                                "Import Portfolio",
                                icon=ft.Icons.UPLOAD,
                                on_click=lambda _: controllers.start_portfolio_import(ctx, page),
                            ),
                            ft.TextButton(
                                "CSV Help",
                                icon=ft.Icons.HELP_OUTLINE,
                                on_click=lambda _: controllers.go_to_help(page),
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        controls=[
                            ft.Text("Watched CSV/file for auto-import:", size=13),
                            ft.Text("", ref=watcher_label, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        controls=[
                            ft.FilledButton(
                                "Choose file",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=choose_watch_target,
                            ),
                            ft.TextButton("Stop watcher", on_click=lambda _: _stop_watcher()),
                        ],
                        spacing=8,
                    ),
                ],
            ),
            padding=20,
        ),
        elevation=2,
    )

    # Build content
    content = ft.Column(
        controls=[
            ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
            ft.Container(height=16),
            appearance_section,
            ft.Container(height=16),
            database_section,
            ft.Container(height=16),
            data_section,
            ft.Container(height=16),
            about_section,
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Build main layout
    app_bar = build_app_bar(ctx, "Settings", page)
    main_layout = build_main_layout(ctx, page, "/settings", content, use_menu_bar=True)

    return ft.View(
        route="/settings",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )
