"""Dedicated debt/liability edit page."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import flet as ft

from ...devtools import dev_log
from ...logging_config import get_logger
from ...models.liability import Liability
from ...services.liabilities import build_payment_transaction
from .. import controllers
from ..components import build_app_bar, build_main_layout, show_confirm_dialog, show_error_dialog

if TYPE_CHECKING:
    from ..context import AppContext

logger = get_logger(__name__)


def build_edit_debt_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build a dedicated edit page for debts/liabilities."""

    uid = ctx.require_user_id()
    target = getattr(ctx, "pending_edit", None) or {}
    record_id = target.get("id")
    return_route = target.get("return_route") or "/debts"

    def _clear():
        ctx.pending_edit = None

    def _finish(message: str | None = None):
        if message:
            page.snack_bar = ft.SnackBar(content=ft.Text(message), show_close_icon=True)
            page.snack_bar.open = True
        ctx.pending_refresh_route = return_route
        _clear()
        controllers.navigate(page, return_route)

    def _back(_=None):
        _finish(None)

    liability = ctx.liability_repo.get_by_id(int(record_id or 0), user_id=uid) if record_id else None
    if not liability:
        fallback = ft.Column(
            [
                ft.Text("Select a debt to edit from the Debts page.", size=18, weight=ft.FontWeight.BOLD),
                ft.FilledButton("Back", icon=ft.Icons.ARROW_BACK, on_click=_back),
            ],
            spacing=12,
        )
        return ft.View(
            route="/edit-debt",
            appbar=build_app_bar(ctx, "Edit debt", page),
            controls=build_main_layout(
                ctx,
                page,
                "/edit-debt",
                ft.Column([fallback], expand=True, alignment=ft.MainAxisAlignment.CENTER),
                use_menu_bar=True,
            ),
            padding=0,
        )

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
    strategy_dd = ft.Dropdown(
        label="Payoff strategy",
        value=getattr(liability, "payoff_strategy", "snowball"),
        options=[
            ft.dropdown.Option("snowball", "Snowball (lowest balance first)"),
            ft.dropdown.Option("avalanche", "Avalanche (highest APR first)"),
        ],
        width=260,
    )

    payment_amount = ft.TextField(
        label="Payment amount",
        value=str(liability.minimum_payment),
        width=180,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    account_options = ctx.account_repo.list_all(user_id=uid)
    account_dd = ft.Dropdown(
        label="Account (optional)",
        options=[ft.dropdown.Option(str(a.id), a.name) for a in account_options if a.id],
        width=220,
    )
    category_options = [c for c in ctx.category_repo.list_all(user_id=uid) if c.id]
    category_dd = ft.Dropdown(
        label="Category (optional)",
        options=[ft.dropdown.Option(str(c.id), c.name) for c in category_options],
        width=220,
    )
    reconcile_switch = ft.Switch(label="Also add to ledger", value=True)

    def _save(_):
        try:
            updated = Liability(
                id=liability.id,
                name=name_field.value or liability.name,
                balance=float(balance_field.value or 0),
                apr=float(apr_field.value or 0),
                minimum_payment=float(min_payment_field.value or 0),
                due_day=max(1, min(28, int(due_day_field.value or 1))),
                payoff_strategy=strategy_dd.value or getattr(liability, "payoff_strategy", "snowball"),
                opened_on=getattr(liability, "opened_on", None),
                user_id=uid,
            )
            ctx.liability_repo.update(updated, user_id=uid)
            dev_log(ctx.config, "Liability edited (page)", context={"id": liability.id})
            _finish("Liability updated")
        except Exception as exc:
            dev_log(ctx.config, "Liability edit failed", exc=exc)
            show_error_dialog(page, "Save failed", str(exc))

    def _apply_payment(_):
        try:
            amt = float(payment_amount.value or 0)
            if amt <= 0:
                payment_amount.error_text = "Payment must be greater than 0"
                payment_amount.update()
                return
            current = ctx.liability_repo.get_by_id(liability.id or 0, user_id=uid)
            if current is None:
                raise ValueError("Liability not found")
            current.balance = max(0.0, current.balance - amt)
            ctx.liability_repo.update(current, user_id=uid)
            if reconcile_switch.value:
                txn = build_payment_transaction(
                    liability=current,
                    amount=amt,
                    account_id=int(account_dd.value) if account_dd.value else None,
                    category_id=int(category_dd.value) if category_dd.value else None,
                    user_id=uid,
                )
                ctx.transaction_repo.create(txn, user_id=uid)
            dev_log(
                ctx.config,
                "Payment applied (edit page)",
                context={"id": liability.id, "amount": amt},
            )
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Payment recorded; new balance ${current.balance:,.2f}"),
                show_close_icon=True,
            )
            page.snack_bar.open = True
            _finish(None)
        except Exception as exc:
            dev_log(ctx.config, "Payment apply failed", exc=exc)
            show_error_dialog(page, "Payment failed", str(exc))

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

    content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=_back, tooltip="Back"),
                    ft.Text("Edit debt", size=26, weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            ft.Card(
                content=ft.Container(
                    padding=16,
                    content=ft.Column(
                        controls=[
                            ft.Row([name_field, balance_field, apr_field], spacing=12, wrap=True, run_spacing=8),
                            ft.Row([min_payment_field, due_day_field, strategy_dd], spacing=12, wrap=True, run_spacing=8),
                            ft.Row(
                                [
                                    ft.FilledButton("Save changes", icon=ft.Icons.SAVE, on_click=_save),
                                    ft.TextButton(
                                        "Delete",
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        style=ft.ButtonStyle(color=ft.Colors.RED),
                                        on_click=lambda _: show_confirm_dialog(
                                            page,
                                            "Delete debt",
                                            "This will remove the liability and its payoff data.",
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
        ),
        ft.Card(
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text("Record payment", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Apply a payment and optionally mirror it in the ledger.",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Row([payment_amount, account_dd, category_dd], spacing=12, wrap=True, run_spacing=8),
                        reconcile_switch,
                        ft.Row(
                            controls=[
                                ft.FilledButton("Apply payment", icon=ft.Icons.PAYMENTS, on_click=_apply_payment),
                                ft.TextButton("Back to Debts", icon=ft.Icons.ARROW_BACK, on_click=_back),
                            ],
                            spacing=10,
                            run_spacing=8,
                            wrap=True,
                        ),
                    ],
                    spacing=10,
                ),
            ),
            elevation=2,
        ),
        ],
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    return ft.View(
        route="/edit-debt",
        appbar=build_app_bar(ctx, "Edit debt", page),
        controls=build_main_layout(ctx, page, "/edit-debt", content, use_menu_bar=True),
        padding=0,
    )
