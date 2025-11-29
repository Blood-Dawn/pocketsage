"""Debts view implementation."""
# TODO(@pocketsage-debts): Integrate strategy modes (aggressive/balanced/lazy) into projections.

# TODO(@codex): Debts MVP features to implement/enhance:
#    - Liability CRUD (add/edit/delete debts) (DONE)
#    - Payoff strategy calculation (snowball/avalanche) (DONE)
#    - Payoff timeline chart showing balance reduction (DONE)
#    - Payment recording to update balances (DONE)
#    - Debt list with summary (total debt, weighted APR) (DONE)
#    - Edge case handling (tiny payments, infinite loops) (needs verification)
#    - Advanced: multiple budgets, custom payoff order, credit score impact (future)

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from .. import controllers
from ...devtools import dev_log
from ...models.liability import Liability
from ...services.debts import DebtAccount, avalanche_schedule, schedule_summary, snowball_schedule
from ...services.liabilities import build_payment_transaction
from ..charts import debt_payoff_chart_png
from ..components import (
    build_app_bar,
    build_main_layout,
    show_confirm_dialog,
    show_error_dialog,
)

if TYPE_CHECKING:
    from ..context import AppContext


def build_debts_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the debts/liabilities view."""

    uid = ctx.require_user_id()
    strategy_state = {"value": "snowball"}

    total_debt_text = ft.Ref[ft.Text]()
    weighted_apr_text = ft.Ref[ft.Text]()
    min_payment_text = ft.Ref[ft.Text]()
    payoff_text = ft.Ref[ft.Text]()
    interest_text = ft.Ref[ft.Text]()
    table_ref = ft.Ref[ft.DataTable]()
    schedule_ref = ft.Ref[ft.Column]()
    payoff_chart_ref = ft.Ref[ft.Image]()

    def _to_accounts(liabilities: list[Liability]) -> list[DebtAccount]:
        return [
            DebtAccount(
                id=lb.id or 0,
                balance=lb.balance,
                apr=lb.apr,
                minimum_payment=lb.minimum_payment,
                statement_due_day=getattr(lb, "due_day", 1) or 1,
            )
            for lb in liabilities
        ]

    def _run_projection(
        liabilities: list[Liability], *, mode: str = "balanced"
    ) -> tuple[list[dict], str | None, float, int]:
        debts = _to_accounts(liabilities)
        if not debts:
            return [], None, 0.0, 0
        surplus = 0.0
        if mode == "aggressive":
            surplus = 150.0
        elif mode == "lazy":
            surplus = 0.0
        else:
            surplus = 50.0
        if strategy_state["value"] == "avalanche":
            sched = avalanche_schedule(debts=debts, surplus=surplus)
        else:
            sched = snowball_schedule(debts=debts, surplus=surplus)
        payoff, total_interest, months = schedule_summary(sched)
        return sched, payoff, total_interest, months

    def _update_schedule(schedule: list[dict], payoff: str | None, total_interest: float) -> None:
        if payoff_text.current:
            payoff_text.current.value = f"Projected payoff: {payoff or 'N/A'}"
        if interest_text.current:
            interest_text.current.value = f"Projected interest: ${total_interest:,.2f}"
        rows: list[ft.Control] = []
        for entry in schedule[:6]:
            payments = entry.get("payments", {}) if isinstance(entry, dict) else {}
            remaining = sum(
                float(p.get("remaining_balance", 0.0) or 0.0) for p in payments.values()
            )
            total_payment = sum(float(p.get("payment_amount", 0.0) or 0.0) for p in payments.values())
            rows.append(
                ft.Row(
                    [
                        ft.Text(str(entry.get("date", "")), width=110),
                        ft.Text(f"Payment: ${total_payment:,.2f}", width=160),
                        ft.Text(f"Remaining: ${remaining:,.2f}", width=160),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )
        if schedule_ref.current is not None:
            if rows:
                schedule_ref.current.controls = rows
            else:
                schedule_ref.current.controls = [
                    ft.Text(
                        "Add a liability to see payoff steps.", color=ft.Colors.ON_SURFACE_VARIANT
                    )
                ]

        if payoff_chart_ref.current is not None:
            try:
                chart_path = debt_payoff_chart_png(schedule) if schedule else None
                payoff_chart_ref.current.src = str(chart_path) if chart_path else ""
                payoff_chart_ref.current.visible = bool(chart_path)
            except Exception as exc:
                dev_log(ctx.config, "Payoff chart render failed", exc=exc)
                payoff_chart_ref.current.visible = False

    def _refresh() -> None:
        liabilities = ctx.liability_repo.list_all(user_id=uid)
        total_debt = ctx.liability_repo.get_total_debt(user_id=uid)
        weighted_apr = ctx.liability_repo.get_weighted_apr(user_id=uid)
        total_min_payment = sum(li.minimum_payment for li in liabilities)

        if total_debt_text.current:
            total_debt_text.current.value = f"${total_debt:,.2f}"
        if weighted_apr_text.current:
            weighted_apr_text.current.value = f"{weighted_apr:.2f}%"
        if min_payment_text.current:
            min_payment_text.current.value = f"${total_min_payment:,.2f}"

        rows: list[ft.DataRow] = []
        for liab in liabilities:
            monthly_interest = liab.balance * (liab.apr / 100) / 12
            action_row = ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        tooltip="Edit",
                        on_click=lambda _, l=liab: _open_edit_dialog(l),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.PAID,
                        tooltip="Record payment",
                        on_click=lambda _, l=liab: _record_payment(l),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        tooltip="Delete",
                        icon_color=ft.Colors.RED,
                        on_click=lambda _, lid=liab.id: _confirm_delete(lid),
                    ),
                ],
                spacing=4,
            )
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(liab.name)),
                        ft.DataCell(ft.Text(f"${liab.balance:,.2f}")),
                        ft.DataCell(ft.Text(f"{liab.apr:.2f}%")),
                        ft.DataCell(ft.Text(f"${liab.minimum_payment:,.2f}")),
                        ft.DataCell(ft.Text(f"${monthly_interest:,.2f}")),
                        ft.DataCell(action_row),
                    ]
                )
            )

        if not rows:
            rows.append(
                ft.DataRow(
                    cells=[ft.DataCell(ft.Text("No liabilities found")) for _ in range(6)]
                )
            )

        if table_ref.current:
            table_ref.current.rows = rows

        try:
            schedule, payoff, total_interest, _months = _run_projection(
                liabilities, mode=strategy_state.get("mode", "balanced")
            )
            _update_schedule(schedule, payoff, total_interest)
        except ValueError as exc:
            show_error_dialog(page, "Payoff calculation failed", str(exc))
        page.update()

    def _open_edit_dialog(liability: Liability | None = None) -> None:
        editing = liability is not None
        title = "Edit liability" if editing else "Add liability"
        name = ft.TextField(label="Name", value=getattr(liability, "name", ""), width=220)
        balance = ft.TextField(
            label="Balance", value=str(getattr(liability, "balance", "") or ""), width=180
        )
        apr = ft.TextField(
            label="APR", value=str(getattr(liability, "apr", "") or ""), width=140, suffix_text="%"
        )
        minimum_payment = ft.TextField(
            label="Minimum payment",
            value=str(getattr(liability, "minimum_payment", "") or ""),
            width=180,
            helper_text="What you must pay each month.",
        )
        due_day = ft.TextField(
            label="Due day (1-28)",
            value=str(getattr(liability, "due_day", 1) or 1),
            width=140,
        )

        def _save(_):
            try:
                record = Liability(
                    id=getattr(liability, "id", None),
                    name=name.value or "Liability",
                    balance=float(balance.value or 0),
                    apr=float(apr.value or 0),
                    minimum_payment=float(minimum_payment.value or 0),
                    due_day=max(1, min(28, int(due_day.value or 1))),
                    user_id=uid,
                )
                if editing:
                    ctx.liability_repo.update(record, user_id=uid)
                else:
                    ctx.liability_repo.create(record, user_id=uid)
                dev_log(
                    ctx.config,
                    "Liability saved",
                    context={"id": getattr(record, "id", None), "editing": editing},
                )
                dialog.open = False
                _refresh()
            except Exception as exc:
                dev_log(ctx.config, "Liability save failed", exc=exc)
                show_error_dialog(page, "Save failed", str(exc))

        def _cancel(_e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Column(
                controls=[name, balance, apr, minimum_payment, due_day],
                tight=True,
                spacing=8,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel),
                ft.FilledButton("Save", on_click=_save),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    # TODO(@codex): Record payment action for a debt
    #    - Allow user to input payment amount (beyond minimum)
    #    - Update remaining balance when payment is recorded (DONE)
    #    - Adjust payoff schedule after payment (DONE - via _refresh)
    #    - Optionally create a transaction in the ledger (DONE - reconcile switch)
    #    - This addresses UR-17 (record payments) and FR-23 (update schedule)
    def _record_payment(liability: Liability) -> None:
        amount_field = ft.TextField(
            label="Payment amount",
            value=str(liability.minimum_payment),
            autofocus=True,
        )
        account_options = ctx.account_repo.list_all(user_id=uid)
        account_dd = ft.Dropdown(
            label="Account",
            options=[ft.dropdown.Option(str(a.id), a.name) for a in account_options if a.id],
            width=220,
        )
        category_options = [c for c in ctx.category_repo.list_all(user_id=uid) if c.id]
        category_dd = ft.Dropdown(
            label="Category",
            options=[ft.dropdown.Option(str(c.id), c.name) for c in category_options],
            width=220,
        )
        reconcile_switch = ft.Switch(label="Also add to ledger", value=True)

        def _apply(_):
            try:
                payment = float(amount_field.value or 0)
                current = ctx.liability_repo.get_by_id(liability.id or 0, user_id=uid)
                if current is None:
                    raise ValueError("Liability not found")
                current.balance = max(0.0, current.balance - payment)
                ctx.liability_repo.update(current, user_id=uid)
                if reconcile_switch.value:
                    txn = build_payment_transaction(
                        liability=current,
                        amount=payment,
                        account_id=int(account_dd.value) if account_dd.value else None,
                        category_id=int(category_dd.value) if category_dd.value else None,
                        user_id=uid,
                    )
                    ctx.transaction_repo.create(txn, user_id=uid)
                dev_log(
                    ctx.config,
                    "Payment applied",
                    context={"liability": liability.id, "amount": payment},
                )
                payment_dialog.open = False
                _refresh()
            except Exception as exc:
                dev_log(ctx.config, "Payment failed", exc=exc, context={"liability": liability.id})
                show_error_dialog(page, "Payment failed", str(exc))

        def _cancel_payment(_e):
            payment_dialog.open = False
            page.update()

        payment_dialog = ft.AlertDialog(
            title=ft.Text(f"Record payment for {liability.name}"),
            content=ft.Column(controls=[amount_field, account_dd, category_dd, reconcile_switch], spacing=8),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel_payment),
                ft.FilledButton("Apply", on_click=_apply),
            ],
        )
        page.dialog = payment_dialog
        payment_dialog.open = True
        page.update()

    def _confirm_delete(liability_id: int | None) -> None:
        if liability_id is None:
            return

        def _delete():
            ctx.liability_repo.delete(liability_id, user_id=uid)
            dev_log(ctx.config, "Liability deleted", context={"id": liability_id})
            _refresh()

        show_confirm_dialog(page, "Delete liability", "Are you sure?", _delete)

    def _on_strategy_change(e):
        strategy_state["value"] = e.control.value
        _refresh()

    summary = ft.Row(
        [
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Total Debt", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text("", size=28, weight=ft.FontWeight.BOLD, ref=total_debt_text),
                        ],
                    ),
                    padding=20,
                ),
                expand=True,
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Weighted APR", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text("", size=28, weight=ft.FontWeight.BOLD, ref=weighted_apr_text),
                        ],
                    ),
                    padding=20,
                ),
                expand=True,
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Min. Payment", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text("", size=28, weight=ft.FontWeight.BOLD, ref=min_payment_text),
                        ],
                    ),
                    padding=20,
                ),
                expand=True,
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "Projected Interest",
                                size=14,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Text("", size=28, weight=ft.FontWeight.BOLD, ref=interest_text),
                        ],
                    ),
                    padding=20,
                ),
                expand=True,
            ),
        ],
        spacing=16,
    )

    table = ft.DataTable(
        ref=table_ref,
        columns=[
            ft.DataColumn(ft.Text("Name")),
            ft.DataColumn(ft.Text("Balance")),
            ft.DataColumn(ft.Text("APR")),
            ft.DataColumn(ft.Text("Min. Payment")),
            ft.DataColumn(ft.Text("Interest/mo")),
            ft.DataColumn(ft.Text("Actions")),
        ],
        rows=[],
        expand=True,
    )

    schedule_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("Payoff schedule (first 6 months)", weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            ft.Text("Month", width=110, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text("Payment", width=130, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text("Remaining", width=150, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Column(controls=[], ref=schedule_ref, spacing=6),
                ],
                spacing=8,
            ),
            padding=12,
        )
    )

    strategy_row = ft.Row(
        [
            ft.Column(
                [
                    ft.Text("Strategy", weight=ft.FontWeight.BOLD),
                    ft.RadioGroup(
                        content=ft.Row(
                            controls=[
                                ft.Radio(value="snowball", label="Snowball"),
                                ft.Radio(value="avalanche", label="Avalanche"),
                            ]
                        ),
                        value=strategy_state["value"],
                        on_change=_on_strategy_change,
                    ),
                ]
            ),
            ft.Column(
                [
                    ft.Text("Payment mode", weight=ft.FontWeight.BOLD),
                    ft.Dropdown(
                        width=200,
                        value=strategy_state.get("mode", "balanced"),
                        options=[
                            ft.dropdown.Option("aggressive", "Aggressive (+$150/mo)"),
                            ft.dropdown.Option("balanced", "Balanced (+$50/mo)"),
                            ft.dropdown.Option("lazy", "Lazy (minimums only)"),
                        ],
                        on_change=lambda e: (
                            strategy_state.update({"mode": e.control.value or "balanced"}),
                            _refresh(),
                        ),
                    ),
                ]
            ),
            ft.Column(
                [
                    ft.Text("", ref=payoff_text),
                    ft.Text(
                        "Snowball: smallest balance first. Avalanche: highest APR first. Payment mode adds surplus toward the current focus debt.",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                width=320,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.START,
        wrap=True,
    )

    content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text("Debts & Liabilities", size=24, weight=ft.FontWeight.BOLD),
                    ft.FilledButton("Add liability", icon=ft.Icons.ADD, on_click=lambda _: controllers.navigate(page, '/add-data')),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                wrap=True,
                run_spacing=8,
            ),
            ft.Container(height=16),
            summary,
            ft.Container(height=24),
            strategy_row,
            ft.Card(content=ft.Container(content=table, padding=12), expand=True),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(content=schedule_card, col={"sm": 12, "md": 6}),
                    ft.Container(
                        content=ft.Card(
                            content=ft.Container(
                                padding=12,
                                content=ft.Column(
                                    controls=[
                                        ft.Text("Payoff chart", weight=ft.FontWeight.BOLD),
                                        ft.Image(ref=payoff_chart_ref, height=240),
                                        ft.Text(
                                            "Line chart shows projected remaining balance over time.",
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                            size=12,
                                        ),
                                    ],
                                    spacing=8,
                                ),
                            )
                        ),
                        col={"sm": 12, "md": 6},
                    ),
                ],
                spacing=12,
                run_spacing=12,
            ),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    app_bar = build_app_bar(ctx, "Debts", page)
    main_layout = build_main_layout(ctx, page, "/debts", content, use_menu_bar=True)

    _refresh()

    return ft.View(
        route="/debts",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )
