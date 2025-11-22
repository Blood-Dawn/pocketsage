"""Controller helpers for desktop navigation and primary actions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

import flet as ft

from ..services import admin_tasks, auth, importers
from ..devtools import dev_log
from .navigation_helpers import handle_navigation_selection, resolve_shortcut_route

if TYPE_CHECKING:
    from .context import AppContext


def _show_snack(page: ft.Page, message: str) -> None:
    """Display a snack bar message."""

    page.snack_bar = ft.SnackBar(content=ft.Text(message))
    page.snack_bar.open = True
    page.update()


def _ctx_config(ctx: AppContext | object) -> object | None:
    """Return config attribute if present to keep dev logging resilient in tests."""

    return getattr(ctx, "config", None)


def navigate(page: ft.Page, route: str) -> None:
    """Navigate to a route and update the page."""

    clean = route if route.startswith("/") else f"/{route}"
    page.go(clean)
    page.update()


def handle_nav_selection(ctx: AppContext, page: ft.Page, selected_index: int) -> None:
    """Delegate navigation rail selection to the helpers and update."""

    is_admin = ctx.current_user is not None and ctx.current_user.role == "admin"
    handle_navigation_selection(page, selected_index, is_admin=is_admin)
    page.update()


def handle_shortcut(page: ft.Page, key: str, ctrl: bool, shift: bool) -> bool:
    """Resolve shortcut navigation; returns True when a route was triggered."""

    route = resolve_shortcut_route(key, ctrl, shift)
    if route:
        navigate(page, route)
        return True
    return False


def run_demo_seed(ctx: AppContext, page: ft.Page) -> None:
    """Seed demo data and surface a friendly summary."""

    try:
        from ..services.heavy_seed import run_heavy_seed

        summary = run_heavy_seed(
            session_factory=ctx.session_factory, user_id=ctx.require_user_id()
        )
        _show_snack(page, f"Demo data ready (heavy {summary.transactions} transactions)")
    except Exception:
        summary = admin_tasks.run_demo_seed(
            session_factory=ctx.session_factory, user_id=ctx.require_user_id()
        )
        _show_snack(page, f"Demo data ready ({summary.transactions} transactions)")


def reset_demo_data(ctx: AppContext, page: ft.Page) -> None:
    """Reset demo data to a known state (drop + reseed)."""

    summary = admin_tasks.reset_demo_database(
        user_id=ctx.require_user_id(), session_factory=ctx.session_factory
    )
    _show_snack(page, f"Demo data reset ({summary.transactions} transactions)")


def attach_file_picker(ctx: AppContext, page: ft.Page) -> ft.FilePicker:
    """Create and attach a shared file picker for imports."""

    def _import_result(e: ft.FilePickerResultEvent) -> None:
        selected = e.files[0] if e.files else None
        mode = ctx.file_picker_mode
        ctx.file_picker_mode = None
        if not selected or not selected.path:
            dev_log(_ctx_config(ctx), "File picker dismissed or missing path", context={"mode": mode})
            return

        csv_path = Path(selected.path)
        dev_log(
            _ctx_config(ctx),
            "Import picker selected",
            context={"mode": mode, "path": csv_path},
        )
        try:
            if mode == "ledger":
                created = importers.import_ledger_transactions(
                    csv_path=csv_path,
                    session_factory=ctx.session_factory,
                    user_id=ctx.require_user_id(),
                )
                dev_log(
                    _ctx_config(ctx),
                    "Ledger import completed",
                    context={"path": csv_path, "created": created},
                )
                msg = (
                    f"Imported {created} transactions"
                    if created
                    else "No new transactions imported (duplicates or invalid rows?)"
                )
                _show_snack(page, msg)
                navigate(page, "/ledger")
            elif mode == "portfolio":
                created = importers.import_portfolio_holdings(
                    csv_path=csv_path,
                    session_factory=ctx.session_factory,
                    user_id=ctx.require_user_id(),
                )
                dev_log(
                    _ctx_config(ctx),
                    "Portfolio import completed",
                    context={"path": csv_path, "created": created},
                )
                msg = (
                    f"Imported {created} holdings"
                    if created
                    else "No holdings imported (empty file or invalid rows)"
                )
                _show_snack(page, msg)
                navigate(page, "/portfolio")
            else:
                _show_snack(page, "No import action configured.")
        except Exception as exc:  # pragma: no cover - user-facing guard
            dev_log(
                _ctx_config(ctx),
                "Import failed",
                exc=exc,
                context={"path": csv_path, "mode": mode},
            )
            _show_snack(page, f"Import failed: {exc}")

    picker = ft.FilePicker(on_result=_import_result)
    ctx.file_picker = picker
    ctx.file_picker_mode = None
    if page.overlay is None:
        page.overlay = [picker]
    else:
        page.overlay.append(picker)
    page.update()
    return picker


def _ensure_picker(ctx: AppContext, page: ft.Page) -> Optional[ft.FilePicker]:
    """Ensure a file picker exists before attempting to use it."""

    if ctx.file_picker is None:
        _show_snack(page, "File picker is not available.")
        return None
    return ctx.file_picker


def start_ledger_import(ctx: AppContext, page: ft.Page) -> None:
    """Open the picker for ledger CSV import."""

    if _ensure_picker(ctx, page) is None:
        return
    ctx.file_picker_mode = "ledger"
    dev_log(_ctx_config(ctx), "Opening ledger import picker")
    ctx.file_picker.pick_files(
        allow_multiple=False,
        allowed_extensions=["csv"],
    )


def start_portfolio_import(ctx: AppContext, page: ft.Page) -> None:
    """Open the picker for portfolio CSV import."""

    if _ensure_picker(ctx, page) is None:
        return
    ctx.file_picker_mode = "portfolio"
    dev_log(_ctx_config(ctx), "Opening portfolio import picker")
    ctx.file_picker.pick_files(
        allow_multiple=False,
        allowed_extensions=["csv"],
    )


def go_to_help(page: ft.Page) -> None:
    """Navigate to the help route."""

    navigate(page, "/help")


def pick_export_destination(
    ctx: AppContext,
    page: ft.Page,
    *,
    on_path_selected: callable[[Path], None],
    suggested_name: str,
) -> None:
    """Let user pick a folder for exports and call the callback with a full file path."""

    picker = ctx.file_picker
    if picker is None:
        _show_snack(page, "File picker is not available.")
        return

    def _on_dir(e: ft.FilePickerResultEvent):
        selected = e.path if e and e.path else None
        picker.on_result = None  # detach temporary handler
        ctx.file_picker_mode = None
        if not selected:
            dev_log(_ctx_config(ctx), "Export destination canceled")
            return
        out_path = Path(selected) / suggested_name
        dev_log(_ctx_config(ctx), "Export destination selected", context={"path": out_path})
        on_path_selected(out_path)

    picker.on_result = _on_dir
    ctx.file_picker_mode = "export"
    picker.get_directory_path()


def logout(ctx: AppContext, page: ft.Page) -> None:
    """Clear session and return to login."""

    if ctx.guest_mode:
        try:
            auth.purge_guest_user(ctx.session_factory)
        except Exception:
            pass
    ctx.current_user = None
    ctx.guest_mode = False
    navigate(page, "/login")


__all__ = [
    "attach_file_picker",
    "go_to_help",
    "handle_nav_selection",
    "handle_shortcut",
    "navigate",
    "reset_demo_data",
    "run_demo_seed",
    "logout",
    "start_ledger_import",
    "start_portfolio_import",
]
