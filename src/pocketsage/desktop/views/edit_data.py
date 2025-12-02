"""Unified edit page for ledger, habits, and portfolio records."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

import flet as ft

from ...devtools import dev_log
from ...logging_config import get_logger
from ...models.account import Account
from ...models.category import Category
from ...models.habit import Habit, HabitEntry
from ...models.liability import Liability
from ...models.portfolio import Holding
from ...models.transaction import Transaction
from ...services import ledger_service
from .. import controllers
from ..components import build_app_bar, build_main_layout, show_confirm_dialog, show_error_dialog
from ..constants import (
    DEFAULT_CATEGORY_SEED,
    DEFAULT_INCOME_CATEGORY_NAMES,
    HABIT_CADENCE_OPTIONS,
)

if TYPE_CHECKING:
    from ..context import AppContext

logger = get_logger(__name__)


def _ensure_categories(ctx: AppContext, user_id: int) -> list:
    """Ensure baseline categories exist before editing transactions."""
    categories = ctx.category_repo.list_all(user_id=user_id)
    if categories:
        return categories
    for seed in DEFAULT_CATEGORY_SEED:
        ctx.category_repo.upsert_by_slug(
            Category(
                name=seed["name"],
                slug=seed.get("slug", seed["name"].lower().replace(" ", "-")),
                category_type=seed.get("category_type")
                or ("income" if seed["name"] in DEFAULT_INCOME_CATEGORY_NAMES else "expense"),
                user_id=user_id,
            ),
            user_id=user_id,
        )
    return ctx.category_repo.list_all(user_id=user_id)


def build_edit_data_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the unified edit view and route to the appropriate form."""

    uid = ctx.require_user_id()
    target = getattr(ctx, "pending_edit", None) or {}
    kind = str(target.get("kind") or "").lower()
    record_id = target.get("id")
    return_route = target.get("return_route") or "/dashboard"

    def _clear_target():
        ctx.pending_edit = None

    def _finish(message: str | None = None, *, refresh: bool = True):
        if message:
            page.snack_bar = ft.SnackBar(content=ft.Text(message), show_close_icon=True)
            page.snack_bar.open = True
        if refresh:
            ctx.pending_refresh_route = return_route
        _clear_target()
        controllers.navigate(page, return_route)

    def _back(_=None):
        _finish(None, refresh=False)

    if not kind or record_id is None:
        fallback = ft.Column(
            controls=[
                ft.Text("Nothing to edit", size=22, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "Select an item in Ledger, Habits, or Portfolio and tap Edit.",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.FilledButton("Back", icon=ft.Icons.ARROW_BACK, on_click=_back),
            ],
            spacing=12,
        )
        content = build_main_layout(
            ctx,
            page,
            "/edit-data",
            ft.Column([fallback], expand=True, alignment=ft.MainAxisAlignment.CENTER),
            use_menu_bar=True,
        )
        return ft.View(
            route="/edit-data",
            appbar=build_app_bar(ctx, "Edit", page),
            controls=content,
            padding=0,
        )

    def _transaction_editor() -> ft.Control:
        tx = ctx.transaction_repo.get_by_id(int(record_id), user_id=uid)
        if not tx:
            return ft.Text(f"Transaction #{record_id} not found.")

        categories = _ensure_categories(ctx, uid)
        accounts = ctx.account_repo.list_all(user_id=uid)
        if not accounts:
            accounts = [
                ctx.account_repo.create(
                    Account(name="Cash", account_type="cash", balance=0.0, user_id=uid),
                    user_id=uid,
                )
            ]

        txn_type = "income" if tx.amount >= 0 else "expense"
        type_group = ft.RadioGroup(
            value=txn_type,
            content=ft.Row(
                controls=[
                    ft.Radio(value="income", label="Income"),
                    ft.Radio(value="expense", label="Expense"),
                    ft.Radio(value="transfer", label="Transfer"),
                ],
                spacing=12,
            ),
        )
        amount_field = ft.TextField(
            label="Amount",
            value=f"{abs(tx.amount):.2f}",
            helper_text="Income stays positive; expenses flip sign automatically.",
            width=200,
        )
        date_picker = ft.DatePicker()
        if page.overlay is None:
            page.overlay = [date_picker]
        else:
            page.overlay.append(date_picker)
        date_field = ft.TextField(
            label="Date",
            value=tx.occurred_at.strftime("%Y-%m-%d"),
            width=180,
            read_only=True,
            on_click=lambda _: setattr(date_picker, "open", True),
        )

        def _on_date_change(e: ft.DatePickerResultEvent):
            if e.control.value:
                selected = e.control.value.date() if hasattr(e.control.value, "date") else e.control.value
                date_field.value = str(selected)
                if getattr(date_field, "page", None):
                    date_field.update()

        date_picker.on_change = _on_date_change

        def _options_for_type(target_type: str):
            filtered = [
                c
                for c in categories
                if target_type == "income" and getattr(c, "category_type", "") == "income"
            ] + [
                c
                for c in categories
                if target_type == "expense" and getattr(c, "category_type", "") == "expense"
            ]
            if target_type == "transfer":
                filtered = categories
            opts = [ft.dropdown.Option("all", "No category")]
            opts += [ft.dropdown.Option(str(c.id), c.name) for c in filtered if getattr(c, "id", None)]
            return opts

        category_dd = ft.Dropdown(
            label="Category",
            options=_options_for_type(txn_type),
            value=str(tx.category_id) if tx.category_id else "all",
            width=240,
        )
        account_dd = ft.Dropdown(
            label="Account",
            options=[ft.dropdown.Option(str(a.id), a.name) for a in accounts if a.id],
            value=str(tx.account_id) if tx.account_id else (str(accounts[0].id) if accounts else ""),
            width=240,
        )
        description_field = ft.TextField(
            label="Description",
            value=tx.memo or "",
            multiline=True,
            min_lines=1,
            max_lines=3,
            expand=True,
        )
        notes_field = ft.TextField(
            label="Notes (optional)",
            value="",
            multiline=True,
            min_lines=1,
            max_lines=3,
            expand=True,
        )

        def _on_type_change(_):
            category_dd.options = _options_for_type(type_group.value or "expense")
            if getattr(category_dd, "page", None):
                category_dd.update()

        type_group.on_change = _on_type_change

        def _save(_):
            try:
                raw_amount = float(amount_field.value or 0)
                if raw_amount == 0:
                    raise ValueError("Amount cannot be zero")
                txn_kind = type_group.value or "expense"
                amount = abs(raw_amount)
                if txn_kind == "expense":
                    amount = -amount
                date_value = (date_field.value or "").strip()
                occurred_at = datetime.fromisoformat(date_value) if date_value else datetime.now()
                category_id = ledger_service.normalize_category_value(category_dd.value)
                account_id = ledger_service.normalize_category_value(account_dd.value)
                memo = description_field.value or ""
                if notes_field.value:
                    memo = f"{memo} - {notes_field.value.strip()}" if memo else notes_field.value.strip()

                saved = ledger_service.save_transaction(
                    ctx.transaction_repo,
                    existing=tx,
                    amount=amount,
                    memo=memo,
                    occurred_at=occurred_at,
                    category_id=category_id,
                    account_id=account_id,
                    currency="USD",
                    user_id=uid,
                )
                dev_log(ctx.config, "Transaction edited", context={"id": saved.id})
                _finish("Transaction updated")
            except Exception as exc:
                dev_log(ctx.config, "Transaction edit failed", exc=exc)
                show_error_dialog(page, "Save failed", str(exc))

        def _delete():
            try:
                ctx.transaction_repo.delete(int(record_id), user_id=uid)
                dev_log(ctx.config, "Transaction deleted", context={"id": record_id})
                _finish("Transaction deleted")
            except Exception as exc:
                dev_log(ctx.config, "Transaction delete failed", exc=exc)
                show_error_dialog(page, "Delete failed", str(exc))

        return ft.Card(
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text(f"Editing transaction #{tx.id}", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Update any field, then save to return to the ledger.",
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            size=12,
                        ),
                        type_group,
                        ft.Row([amount_field, date_field], spacing=12),
                        ft.Row([category_dd, account_dd], spacing=12, wrap=True, run_spacing=8),
                        description_field,
                        notes_field,
                        ft.Row(
                            [
                                ft.FilledButton("Save changes", icon=ft.Icons.SAVE, on_click=_save),
                                ft.TextButton(
                                    "Delete",
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    style=ft.ButtonStyle(color=ft.Colors.RED),
                                    on_click=lambda _: show_confirm_dialog(
                                        page,
                                        "Delete transaction",
                                        "This will permanently remove the transaction.",
                                        _delete,
                                    ),
                                ),
                                ft.TextButton("Cancel", icon=ft.Icons.CLOSE, on_click=_back),
                            ],
                            spacing=12,
                        ),
                    ],
                    spacing=12,
                ),
            ),
            elevation=2,
        )

    def _habit_editor() -> ft.Control:
        habit = ctx.habit_repo.get_by_id(int(record_id), user_id=uid)
        if not habit:
            return ft.Text(f"Habit #{record_id} not found.")

        name_field = ft.TextField(label="Name", value=habit.name, width=260)
        desc_field = ft.TextField(
            label="Description",
            value=habit.description or "",
            width=320,
            multiline=True,
            max_lines=3,
        )
        cadence_dd = ft.Dropdown(
            label="Cadence",
            options=[ft.dropdown.Option(key, label) for key, label in HABIT_CADENCE_OPTIONS],
            value=habit.cadence,
            width=200,
        )
        reminder_field = ft.TextField(
            label="Reminder (HH:MM)",
            value=habit.reminder_time or "",
            width=160,
            hint_text="08:00",
        )
        active_switch = ft.Switch(label="Active", value=habit.is_active)

        window_days = 21
        today = date.today()
        start = today - timedelta(days=window_days - 1)
        existing_entries = {
            entry.occurred_on
            for entry in ctx.habit_repo.get_entries_for_habit(habit.id, start, today, user_id=uid)
            if entry.value > 0
        }
        checkboxes: list[ft.Checkbox] = []
        day_lookup: dict[date, ft.Checkbox] = {}
        for offset in range(window_days):
            day = start + timedelta(days=offset)
            cb = ft.Checkbox(label=day.strftime("%b %d"), value=day in existing_entries, width=110)
            day_lookup[day] = cb
            checkboxes.append(cb)

        def _validate_reminder(raw: str | None) -> str | None:
            if not raw:
                return None
            try:
                datetime.strptime(raw.strip(), "%H:%M")
                return raw.strip()
            except ValueError:
                return None

        def _save(_):
            try:
                if not (name_field.value or "").strip():
                    raise ValueError("Name is required")
                reminder_value = _validate_reminder(reminder_field.value)
                if reminder_field.value and not reminder_value:
                    raise ValueError("Reminder must use HH:MM")

                habit.name = name_field.value.strip()
                habit.description = desc_field.value or ""
                habit.cadence = cadence_dd.value or habit.cadence
                habit.reminder_time = reminder_value
                habit.is_active = bool(active_switch.value)
                ctx.habit_repo.update(habit, user_id=uid)

                selected_days = {day for day, cb in day_lookup.items() if cb.value}
                to_add = selected_days - existing_entries
                to_remove = existing_entries - selected_days
                for day in to_add:
                    ctx.habit_repo.upsert_entry(
                        HabitEntry(habit_id=habit.id, occurred_on=day, value=1, user_id=uid),
                        user_id=uid,
                    )
                for day in to_remove:
                    ctx.habit_repo.delete_entry(habit.id, day, user_id=uid)

                current_streak = ctx.habit_repo.get_current_streak(habit.id, user_id=uid)
                longest_streak = ctx.habit_repo.get_longest_streak(habit.id, user_id=uid)
                dev_log(
                    ctx.config,
                    "Habit edited",
                    context={
                        "id": habit.id,
                        "current_streak": current_streak,
                        "longest_streak": longest_streak,
                    },
                )
                _finish("Habit updated")
            except Exception as exc:
                dev_log(ctx.config, "Habit edit failed", exc=exc)
                show_error_dialog(page, "Save failed", str(exc))

        def _delete():
            try:
                entries = ctx.habit_repo.get_entries_for_habit(habit.id, date.min, date.max, user_id=uid)
                for entry in entries:
                    ctx.habit_repo.delete_entry(habit.id, entry.occurred_on, user_id=uid)
                ctx.habit_repo.delete(habit.id, user_id=uid)
                dev_log(ctx.config, "Habit deleted", context={"id": habit.id})
                _finish("Habit deleted")
            except Exception as exc:
                dev_log(ctx.config, "Habit delete failed", exc=exc)
                show_error_dialog(page, "Delete failed", str(exc))

        return ft.Card(
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text(f"Editing habit #{habit.id}", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Update details and tweak recent completions to adjust streaks.",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Row([name_field, cadence_dd, active_switch], spacing=12, wrap=True, run_spacing=8),
                        ft.Row([desc_field, reminder_field], spacing=12, wrap=True, run_spacing=8),
                        ft.Text("Recent completion history", weight=ft.FontWeight.BOLD),
                        ft.Row(controls=checkboxes, wrap=True, spacing=8, run_spacing=8),
                        ft.Row(
                            [
                                ft.FilledButton("Save changes", icon=ft.Icons.SAVE, on_click=_save),
                                ft.TextButton(
                                    "Delete",
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    style=ft.ButtonStyle(color=ft.Colors.RED),
                                    on_click=lambda _: show_confirm_dialog(
                                        page,
                                        "Delete habit",
                                        "This will remove the habit and its recent entries.",
                                        _delete,
                                    ),
                                ),
                                ft.TextButton("Cancel", icon=ft.Icons.CLOSE, on_click=_back),
                            ],
                            spacing=12,
                        ),
                    ],
                    spacing=12,
                ),
            ),
            elevation=2,
        )

    def _holding_editor() -> ft.Control:
        holding = ctx.holding_repo.get_by_id(int(record_id), user_id=uid)
        if not holding:
            return ft.Text(f"Holding #{record_id} not found.")

        accounts = ctx.account_repo.list_all(user_id=uid)
        if not accounts:
            accounts = [
                ctx.account_repo.create(
                    Account(name="Brokerage", account_type="investment", balance=0.0, user_id=uid),
                    user_id=uid,
                )
            ]
        account_dd = ft.Dropdown(
            label="Account",
            options=[ft.dropdown.Option(str(a.id), a.name) for a in accounts if a.id],
            value=str(holding.account_id) if holding.account_id else (str(accounts[0].id) if accounts else ""),
            width=220,
        )
        symbol_field = ft.TextField(label="Symbol", value=holding.symbol, width=160)
        qty_field = ft.TextField(
            label="Quantity",
            value=str(holding.quantity),
            width=140,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        avg_price_field = ft.TextField(
            label="Average price",
            value=str(holding.avg_price),
            width=160,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        market_price_field = ft.TextField(
            label="Market price",
            value=str(getattr(holding, "market_price", holding.avg_price) or ""),
            width=160,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def _save(_):
            try:
                updated = Holding(
                    id=holding.id,
                    symbol=(symbol_field.value or "").upper(),
                    quantity=float(qty_field.value or 0),
                    avg_price=float(avg_price_field.value or 0),
                    market_price=float(market_price_field.value or 0),
                    account_id=int(account_dd.value) if account_dd.value else None,
                    currency=holding.currency or "USD",
                    user_id=uid,
                )
                ctx.holding_repo.update(updated, user_id=uid)
                dev_log(ctx.config, "Holding edited", context={"id": holding.id})
                _finish("Holding updated")
            except Exception as exc:
                dev_log(ctx.config, "Holding edit failed", exc=exc)
                show_error_dialog(page, "Save failed", str(exc))

        def _delete():
            try:
                ctx.holding_repo.delete(int(record_id), user_id=uid)
                dev_log(ctx.config, "Holding deleted", context={"id": record_id})
                _finish("Holding deleted")
            except Exception as exc:
                dev_log(ctx.config, "Holding delete failed", exc=exc)
                show_error_dialog(page, "Delete failed", str(exc))

        return ft.Card(
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text(f"Editing holding #{holding.id}", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Adjust quantity, cost basis, market price, or account.",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Row([symbol_field, account_dd], spacing=12, wrap=True, run_spacing=8),
                        ft.Row([qty_field, avg_price_field, market_price_field], spacing=12, wrap=True, run_spacing=8),
                        ft.Row(
                            [
                                ft.FilledButton("Save changes", icon=ft.Icons.SAVE, on_click=_save),
                                ft.TextButton(
                                    "Delete",
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    style=ft.ButtonStyle(color=ft.Colors.RED),
                                    on_click=lambda _: show_confirm_dialog(
                                        page,
                                        "Delete holding",
                                        "This will remove the holding from your portfolio.",
                                        _delete,
                                    ),
                                ),
                                ft.TextButton("Cancel", icon=ft.Icons.CLOSE, on_click=_back),
                            ],
                            spacing=12,
                        ),
                    ],
                    spacing=12,
                ),
            ),
            elevation=2,
        )

    def _liability_editor() -> ft.Control:
        liability = ctx.liability_repo.get_by_id(int(record_id), user_id=uid)
        if not liability:
            return ft.Text(f"Liability #{record_id} not found.")

        name_field = ft.TextField(label="Name", value=liability.name, width=220)
        balance_field = ft.TextField(
            label="Balance",
            value=str(liability.balance),
            width=180,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        apr_field = ft.TextField(
            label="APR (%)",
            value=str(liability.apr),
            width=160,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        min_payment_field = ft.TextField(
            label="Minimum payment",
            value=str(liability.minimum_payment),
            width=180,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        due_day_field = ft.TextField(
            label="Due day (1-28)",
            value=str(getattr(liability, "due_day", 1) or 1),
            width=140,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def _save(_):
            try:
                updated = Liability(
                    id=liability.id,
                    name=name_field.value or liability.name,
                    balance=float(balance_field.value or 0),
                    apr=float(apr_field.value or 0),
                    minimum_payment=float(min_payment_field.value or 0),
                    due_day=max(1, min(28, int(due_day_field.value or 1))),
                    payoff_strategy=getattr(liability, "payoff_strategy", "snowball"),
                    user_id=uid,
                )
                ctx.liability_repo.update(updated, user_id=uid)
                dev_log(ctx.config, "Liability edited", context={"id": liability.id})
                _finish("Liability updated")
            except Exception as exc:
                dev_log(ctx.config, "Liability edit failed", exc=exc)
                show_error_dialog(page, "Save failed", str(exc))

        def _delete():
            try:
                related = ctx.transaction_repo.list_by_liability(int(record_id), user_id=uid)
                for txn in related:
                    if txn.id:
                        ctx.transaction_repo.delete(txn.id, user_id=uid)
                ctx.liability_repo.delete(int(record_id), user_id=uid)
                dev_log(ctx.config, "Liability deleted", context={"id": record_id})
                _finish("Liability deleted")
            except Exception as exc:
                dev_log(ctx.config, "Liability delete failed", exc=exc)
                show_error_dialog(page, "Delete failed", str(exc))

        return ft.Card(
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text(f"Editing liability #{liability.id}", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Keep balances in sync with debts and payoff schedules.",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Row(
                            [name_field, balance_field, apr_field],
                            spacing=12,
                            wrap=True,
                            run_spacing=8,
                        ),
                        ft.Row([min_payment_field, due_day_field], spacing=12, wrap=True, run_spacing=8),
                        ft.Row(
                            [
                                ft.FilledButton("Save changes", icon=ft.Icons.SAVE, on_click=_save),
                                ft.TextButton(
                                    "Delete",
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    style=ft.ButtonStyle(color=ft.Colors.RED),
                                    on_click=lambda _: show_confirm_dialog(
                                        page,
                                        "Delete liability",
                                        "This will remove the liability and its payoff projections.",
                                        _delete,
                                    ),
                                ),
                                ft.TextButton("Cancel", icon=ft.Icons.CLOSE, on_click=_back),
                            ],
                            spacing=12,
                        ),
                    ],
                    spacing=12,
                ),
            ),
            elevation=2,
        )

    builders = {
        "transaction": _transaction_editor,
        "habit": _habit_editor,
        "holding": _holding_editor,
        "liability": _liability_editor,
    }
    builder = builders.get(kind)
    panel = builder() if builder else ft.Text(f"Unsupported edit type: {kind}")

    content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=_back, tooltip="Back"),
                    ft.Text(f"Edit {kind}", size=26, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=8,
            ),
            panel,
        ],
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    return ft.View(
        route="/edit-data",
        appbar=build_app_bar(ctx, "Edit", page),
        controls=build_main_layout(ctx, page, "/edit-data", content, use_menu_bar=True),
        padding=0,
        scroll=ft.ScrollMode.HIDDEN,
    )
