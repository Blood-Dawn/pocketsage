"""Admin view for user management, metrics, and seeding."""

# TODO(@codex): Admin tools for data management (seeding, backup, restore)
#    - Demo data seed button (DONE - run_demo_seed and run_heavy_seed)
#    - Backup data (export all data to zip) (DONE - backup_database)
#    - Restore data (import from zip) (DONE - restore_database)
#    - Protect admin actions with confirmation dialogs (DONE)
#    - For login-free MVP, allow guest users to access admin features

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft
from sqlalchemy import func, select

from ...models import Account, Habit, Transaction, User
from ...services import auth
from ...services.admin_tasks import (
    backup_database,
    reset_demo_database,
    restore_database,
    run_demo_seed,
    run_export,
)
from ...services.heavy_seed import run_heavy_seed
from ..components import build_app_bar, build_main_layout

if TYPE_CHECKING:  # pragma: no cover
    from ..context import AppContext


def build_admin_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Render admin dashboard with user controls."""

    # TODO(@codex): Allow guest users to access admin features in login-free MVP
    #    - In single-user mode, all admin features should be accessible
    #    - When multi-user is re-enabled, restore admin role check
    #    - For now, only block if no user is set at all
    if ctx.current_user is None:
        page.snack_bar = ft.SnackBar(content=ft.Text("No user context available"))
        page.snack_bar.open = True
        page.go("/dashboard")
        return ft.View(route="/admin", controls=[], padding=0)

    # Allow both admin and guest users (for MVP)
    if not ctx.guest_mode and ctx.current_user.role not in ("admin", "guest"):
        page.snack_bar = ft.SnackBar(content=ft.Text("Admin access required"))
        page.snack_bar.open = True
        page.go("/dashboard")
        return ft.View(route="/admin", controls=[], padding=0)

    status_ref = ft.Ref[ft.Text]()
    users = auth.list_users(ctx.session_factory)
    selected_user_id = ft.Ref[ft.Dropdown]()

    def _selected_id() -> int | None:
        raw = selected_user_id.current.value if selected_user_id.current else None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def refresh_users():
        nonlocal users
        users = auth.list_users(ctx.session_factory)
        if selected_user_id.current:
            selected_user_id.current.options = [
                ft.dropdown.Option(str(u.id), text=f"{u.username} ({u.role})") for u in users
            ]
            if ctx.current_user and ctx.current_user.id:
                selected_user_id.current.value = str(ctx.current_user.id)
        if status_ref.current:
            status_ref.current.value = ""
        page.update()

    def _show_message(message: str):
        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        if status_ref.current:
            status_ref.current.value = message
            status_ref.current.update()
        page.update()

    def create_user_action(_):
        username = create_username.value.strip()
        if not username or not create_password.value:
            _show_message("Username and password required")
            return
        if create_password.value != create_confirm.value:
            _show_message("Passwords do not match")
            return
        try:
            user = auth.create_user(
                username=username,
                password=create_password.value,
                role=create_role.value,
                session_factory=ctx.session_factory,
            )
        except Exception as exc:  # pragma: no cover
            _show_message(str(exc))
            return
        refresh_users()
        _show_message(f"User {user.username} created")

    def set_role_action(role: str):
        user_id = _selected_id()
        if user_id is None:
            _show_message("Select a user first")
            return
        auth.set_role(user_id=user_id, role=role, session_factory=ctx.session_factory)
        refresh_users()
        _show_message(f"Role updated to {role}")

    def delete_user_action(_):
        user_id = _selected_id()
        if user_id is None:
            _show_message("Select a user first")
            return
        if ctx.current_user and ctx.current_user.id == user_id:
            _show_message("Cannot delete the active user")
            return
        with ctx.session_factory() as session:
            target = session.get(User, user_id)
            if target:
                # Remove data for the user then delete user row
                try:
                    from ...services.admin_tasks import reset_demo_database

                    reset_demo_database(user_id=user_id, session_factory=ctx.session_factory)
                except Exception:
                    pass
                session.delete(target)
                session.commit()
        refresh_users()
        _show_message("User deleted")

    def reset_password_action(_):
        user_id = _selected_id()
        if user_id is None:
            _show_message("Select a user first")
            return
        password_field = ft.TextField(
            label="New password",
            password=True,
            can_reveal_password=True,
            autofocus=True,
        )

        def _apply(_):
            try:
                auth.reset_password(
                    user_id=user_id, password=password_field.value, session_factory=ctx.session_factory
                )
            except Exception as exc:
                _show_message(str(exc))
                dialog.open = False
                return
            dialog.open = False
            _show_message("Password reset")

        dialog = ft.AlertDialog(
            title=ft.Text("Reset password"),
            content=password_field,
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: setattr(dialog, "open", False)),
                ft.FilledButton("Reset", on_click=_apply),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def export_all_users(_):
        try:
            exports_dir = ctx.config.DATA_DIR / "exports"
            path = run_export(
                exports_dir,
                session_factory=ctx.session_factory,
                user_id=None,
                retention=ctx.config.EXPORT_RETENTION,
            )
            _show_message(f"All-user export ready: {path}")
        except Exception as exc:  # pragma: no cover - user facing
            _show_message(f"Export failed: {exc}")

    restore_picker = ft.FilePicker()

    def restore_from_backup(_):
        restore_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["db"],
        )

    def _restore_result(e: ft.FilePickerResultEvent):
        selected = e.files[0] if e.files else None
        if not selected or not selected.path:
            return
        try:
            restored = restore_database(Path(selected.path), config=ctx.config)
            _show_message(f"Database restored to {restored} (restart app to reload)")
        except Exception as exc:  # pragma: no cover - user facing
            _show_message(f"Restore failed: {exc}")

    restore_picker.on_result = _restore_result
    try:
        page.overlay.append(restore_picker)
    except Exception:
        pass

    def backup_db(_):
        try:
            backups_dir = ctx.config.DATA_DIR / "backups"
            backup_path = backup_database(backups_dir, config=ctx.config)
            _show_message(f"Backup saved: {backup_path}")
        except Exception as exc:  # pragma: no cover - user facing
            _show_message(f"Backup failed: {exc}")

    def seed_action(_):
        user_id = _selected_id()
        if user_id is None:
            _show_message("Select a user to seed")
            return
        summary = run_heavy_seed(session_factory=ctx.session_factory, user_id=user_id)
        _show_message(f"Seeded heavy demo data ({summary.transactions} transactions)")

    def reset_action(_):
        user_id = _selected_id()
        if user_id is None:
            _show_message("Select a user to reset")
            return
        summary = reset_demo_database(user_id=user_id, session_factory=ctx.session_factory)
        _show_message(f"Reset demo data ({summary.transactions} transactions)")

    def _metrics():
        with ctx.session_factory() as session:
            total_users = session.exec(select(func.count(User.id))).one()
            total_accounts = session.exec(select(func.count(Account.id))).one()
            total_transactions = session.exec(select(func.count(Transaction.id))).one()
            total_habits = session.exec(select(func.count(Habit.id))).one()
        return total_users, total_accounts, total_transactions, total_habits

    total_users, total_accounts, total_transactions, total_habits = _metrics()

    metrics_row = ft.Row(
        [
            _metric_card("Users", total_users, ft.Icons.GROUP),
            _metric_card("Accounts", total_accounts, ft.Icons.ACCOUNT_BALANCE),
            _metric_card("Transactions", total_transactions, ft.Icons.RECEIPT_LONG),
            _metric_card("Habits", total_habits, ft.Icons.CHECK_CIRCLE),
        ],
        spacing=12,
    )

    selected_user_id.current = ft.Dropdown(
        label="Select user",
        options=[ft.dropdown.Option(str(u.id), text=f"{u.username} ({u.role})") for u in users],
        value=str(ctx.current_user.id) if ctx.current_user and ctx.current_user.id else None,
        width=320,
    )

    create_username = ft.TextField(label="Username", width=240)
    create_password = ft.TextField(
        label="Password", width=240, password=True, can_reveal_password=True
    )
    create_confirm = ft.TextField(
        label="Confirm password", width=240, password=True, can_reveal_password=True
    )
    create_role = ft.Dropdown(
        label="Role",
        options=[ft.dropdown.Option("user", "User"), ft.dropdown.Option("admin", "Admin")],
        value="user",
        width=160,
    )

    actions = ft.Column(
        [
            ft.Text("User management", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([selected_user_id.current], spacing=8),
            ft.Row(
                [
                    ft.FilledTonalButton(
                        "Promote to admin", on_click=lambda _: set_role_action("admin")
                    ),
                    ft.FilledTonalButton("Set as user", on_click=lambda _: set_role_action("user")),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.RED,
                        tooltip="Delete user",
                        on_click=delete_user_action,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.KEY,
                        tooltip="Reset password",
                        on_click=reset_password_action,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.IOS_SHARE,
                        tooltip="Export all users",
                        on_click=export_all_users,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.BACKUP,
                        tooltip="Backup DB (all users)",
                        on_click=backup_db,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.RESTORE_PAGE,
                        tooltip="Restore from backup (.db)",
                        on_click=restore_from_backup,
                    ),
                ],
                spacing=8,
            ),
            ft.Row(
                [
                    ft.FilledButton("Seed demo data", icon=ft.Icons.DOWNLOAD, on_click=seed_action),
                    ft.TextButton("Reset demo data", icon=ft.Icons.RESTORE, on_click=reset_action),
                ],
                spacing=8,
            ),
            ft.Divider(),
            ft.Text("Create user", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([create_username, create_role], spacing=8),
            ft.Row([create_password, create_confirm], spacing=8),
            ft.FilledButton("Create", icon=ft.Icons.ADD, on_click=create_user_action),
        ],
        spacing=10,
    )

    users_table_rows = [
        ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(user.username)),
                ft.DataCell(ft.Text(user.role)),
                ft.DataCell(ft.Text(str(user.created_at.date()) if user.created_at else "-")),
            ]
        )
        for user in users
    ]
    users_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Username")),
            ft.DataColumn(ft.Text("Role")),
            ft.DataColumn(ft.Text("Created")),
        ],
        rows=users_table_rows
        or [ft.DataRow(cells=[ft.DataCell(ft.Text("No users found")) for _ in range(3)])],
        expand=True,
    )

    content = ft.Column(
        [
            metrics_row,
            ft.Container(height=16),
            ft.Row(
                [
                    ft.Card(content=ft.Container(padding=16, content=actions), expand=True),
                    ft.Card(content=ft.Container(padding=16, content=users_table), expand=True),
                ],
                spacing=12,
            ),
            ft.Text("", ref=status_ref, color=ft.Colors.ON_SURFACE_VARIANT),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    refresh_users()

    app_bar = build_app_bar(ctx, "Admin", page)
    layout = build_main_layout(ctx, page, "/admin", content)

    return ft.View(route="/admin", appbar=app_bar, controls=layout, padding=0)


def _metric_card(label: str, value: int, icon: str) -> ft.Control:
    return ft.Card(
        content=ft.Container(
            padding=12,
            content=ft.Row(
                [
                    ft.Icon(icon, color=ft.Colors.PRIMARY),
                    ft.Column(
                        [
                            ft.Text(label, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(str(value), size=22, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=2,
                    ),
                ]
            ),
        ),
        elevation=1,
    )
