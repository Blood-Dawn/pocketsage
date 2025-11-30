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

import threading
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from .. import controllers
from ...devtools import dev_log
from ...logging_config import get_logger
from ...models.liability import Liability
from ...services.debts import DebtAccount, avalanche_schedule, schedule_summary, snowball_schedule
from ...services.liabilities import build_payment_transaction
from ..charts import debt_payoff_chart_png
from ..components import build_app_bar, build_main_layout, show_confirm_dialog, show_error_dialog
from ..components import (
    build_app_bar,
    build_main_layout,
    show_confirm_dialog,
    show_error_dialog,
)

if TYPE_CHECKING:
    from ..context import AppContext


logger = get_logger(__name__)


def _safe_update(control: ft.Control | None) -> None:
    """Safely update a control, ignoring errors if not mounted."""
    if control is None:
        return
    try:
        if hasattr(control, "page") and control.page:
            control.update()
    except AssertionError:
        pass  # Control not mounted to page
    except Exception:
        pass  # Other update errors


def build_debts_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the debts/liabilities view."""

    uid = ctx.require_user_id()
    strategy_state = {"value": "snowball", "mode": "balanced"}
    liabilities: list[Liability] = ctx.liability_repo.list_all(user_id=uid)

    total_debt_text = ft.Ref[ft.Text]()
    weighted_apr_text = ft.Ref[ft.Text]()
    min_payment_text = ft.Ref[ft.Text]()
    payoff_text = ft.Ref[ft.Text]()
    interest_text = ft.Ref[ft.Text]()
    table_ref = ft.Ref[ft.DataTable]()
    schedule_ref = ft.Ref[ft.Column]()
    schedule_page_ref = ft.Ref[ft.Text]()
    schedule_state = {"current_page": 0, "page_size": 12, "total_rows": 0}
    payoff_chart_ref = ft.Ref[ft.Image]()
    payoff_chart_card_ref = ft.Ref[ft.Container]()
    empty_state_ref = ft.Ref[ft.Container]()
    main_content_ref = ft.Ref[ft.Column]()

    def _log_debts_state(prefix: str, liabilities: list[Liability], schedule: list[dict]):
        """Log diagnostics for debugging payoff rendering issues."""
        logger.info(
            "%s: debts=%s schedule_len=%s",
            prefix,
            [
                {
                    "id": li.id,
                    "name": li.name,
                    "balance": li.balance,
                    "apr": li.apr,
                    "min_payment": li.minimum_payment,
                    "due_day": getattr(li, "due_day", None),
                }
                for li in liabilities
            ],
            len(schedule),
        )

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
    ) -> tuple[list[dict], str | None, float, int, Path | None]:
        """Run payoff projection with full error handling."""

        # Early return for empty input
        if not liabilities:
            return [], None, 0.0, 0, None

        # Convert to DebtAccount objects with validation
        debts = []
        for lb in liabilities:
            try:
                balance = float(lb.balance) if lb.balance else 0.0
                apr = float(lb.apr) if lb.apr else 0.0
                min_payment = float(lb.minimum_payment) if lb.minimum_payment else 0.0

                # Skip invalid entries
                if balance <= 0 or min_payment <= 0:
                    continue

                debts.append(DebtAccount(
                    id=lb.id or 0,
                    balance=balance,
                    apr=apr,
                    minimum_payment=min_payment,
                    statement_due_day=getattr(lb, "due_day", 1) or 1,
                ))
            except (TypeError, ValueError) as e:
                logger.warning(f"Skipping invalid liability: {e}")
                continue

        if not debts:
            return [], None, 0.0, 0, None

        total_debt = sum(d.balance for d in debts)
        if total_debt <= 0:
            return [], None, 0.0, 0, None

        # Determine surplus based on mode
        surplus = 0.0
        if mode == "aggressive":
            surplus = 150.0
        elif mode == "balanced":
            surplus = 50.0

        # Initialize return values
        sched: list[dict] = []
        payoff: str | None = None
        total_interest = 0.0
        months = 0
        chart_path: Path | None = None

        try:
            if strategy_state["value"] == "avalanche":
                sched = avalanche_schedule(debts=debts, surplus=surplus)
            else:
                sched = snowball_schedule(debts=debts, surplus=surplus)

            if sched and len(sched) > 0:
                payoff, total_interest, months = schedule_summary(sched)
                try:
                    chart_path = debt_payoff_chart_png(sched)
                except Exception as chart_exc:
                    logger.warning("Chart generation failed: %s", chart_exc)
                    chart_path = None

        except Exception as exc:
            logger.warning("Payoff schedule generation failed: %s", exc)
            sched = []
            chart_path = None
            payoff = None
            total_interest = 0.0
            months = 0

        return sched, payoff, total_interest, months, chart_path

    def _update_schedule(
        schedule: list[dict],
        payoff: str | None,
        total_interest: float,
        months: int,
        *,
        has_liabilities: bool,
        chart_path: Path | None,
    ) -> None:
        if payoff_text.current:
            payoff_text.current.value = (
                f"Projected payoff: {payoff or 'N/A'} ({months} months)" if schedule else "Projected payoff: N/A"
            )
            _safe_update(payoff_text.current)
        if interest_text.current:
            interest_text.current.value = f"Projected interest: ${total_interest:,.2f}"
            _safe_update(interest_text.current)

        # Build all rows first
        all_rows: list[ft.Control] = []
        for entry in schedule:
            payments = entry.get("payments", {}) if isinstance(entry, dict) else {}
            remaining = sum(
                float(p.get("remaining_balance", 0.0) or 0.0) for p in payments.values()
            )
            total_payment = sum(float(p.get("payment_amount", 0.0) or 0.0) for p in payments.values())
            all_rows.append(
                ft.Row(
                    [
                        ft.Text(str(entry.get("date", "")), width=110),
                        ft.Text(f"Payment: ${total_payment:,.2f}", width=160),
                        ft.Text(f"Remaining: ${remaining:,.2f}", width=160),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

        # Update pagination state
        schedule_state["total_rows"] = len(all_rows)
        total_pages = max(1, (len(all_rows) + schedule_state["page_size"] - 1) // schedule_state["page_size"])

        # Ensure current page is valid
        if schedule_state["current_page"] >= total_pages:
            schedule_state["current_page"] = max(0, total_pages - 1)

        # Get rows for current page
        start_idx = schedule_state["current_page"] * schedule_state["page_size"]
        end_idx = min(start_idx + schedule_state["page_size"], len(all_rows))
        page_rows = all_rows[start_idx:end_idx] if all_rows else []

        # Update schedule display
        if schedule_ref.current is not None:
            if page_rows:
                schedule_ref.current.controls = page_rows
            else:
                schedule_ref.current.controls = [
                    ft.Text(
                        "Add a liability to see payoff steps.", color=ft.Colors.ON_SURFACE_VARIANT
                    )
                ]
            _safe_update(schedule_ref.current)

        # Update page indicator
        if schedule_page_ref.current and all_rows:
            schedule_page_ref.current.value = (
                f"Page {schedule_state['current_page'] + 1} of {total_pages} "
                f"(showing {start_idx + 1}-{end_idx} of {len(all_rows)} months)"
            )
            _safe_update(schedule_page_ref.current)

        # Update payoff chart with comprehensive error handling
        # Wrap ALL property assignments in try-except to prevent unmounted control errors
        if payoff_chart_ref.current is not None:
            try:
                if not has_liabilities or not schedule:
                    # Hide chart - wrap each property assignment individually
                    try:
                        payoff_chart_ref.current.visible = False
                    except Exception:
                        pass
                    try:
                        payoff_chart_ref.current.src = ""
                    except Exception:
                        pass
                    try:
                        payoff_chart_ref.current.height = 0
                    except Exception:
                        pass
                    if payoff_chart_card_ref.current:
                        try:
                            payoff_chart_card_ref.current.visible = False
                        except Exception:
                            pass
                        _safe_update(payoff_chart_card_ref.current)
                    logger.info(
                        "Payoff chart hidden (has_liabilities=%s, schedule_len=%s)",
                        has_liabilities,
                        len(schedule),
                    )
                    _safe_update(payoff_chart_ref.current)
                    return

                if chart_path is not None:
                    try:
                        if hasattr(chart_path, 'exists') and chart_path.exists():
                            # Show chart - wrap each property assignment individually
                            try:
                                payoff_chart_ref.current.src = str(chart_path)
                            except Exception:
                                pass
                            try:
                                payoff_chart_ref.current.visible = True
                            except Exception:
                                pass
                            try:
                                payoff_chart_ref.current.fit = ft.ImageFit.CONTAIN
                            except Exception:
                                pass
                            try:
                                payoff_chart_ref.current.height = 240
                            except Exception:
                                pass
                            if payoff_chart_card_ref.current:
                                try:
                                    payoff_chart_card_ref.current.visible = True
                                except Exception:
                                    pass
                                _safe_update(payoff_chart_card_ref.current)
                            logger.info("Payoff chart shown at %s", chart_path)
                        else:
                            # Hide chart if file doesn't exist
                            try:
                                payoff_chart_ref.current.src = ""
                            except Exception:
                                pass
                            try:
                                payoff_chart_ref.current.visible = False
                            except Exception:
                                pass
                            try:
                                payoff_chart_ref.current.height = 0
                            except Exception:
                                pass
                            if payoff_chart_card_ref.current:
                                try:
                                    payoff_chart_card_ref.current.visible = False
                                except Exception:
                                    pass
                            logger.warning("Chart path missing or not found: %s", chart_path)
                    except Exception as path_exc:
                        logger.warning("Chart path check failed: %s", path_exc)
                        try:
                            payoff_chart_ref.current.visible = False
                        except Exception:
                            pass
                        try:
                            payoff_chart_ref.current.height = 0
                        except Exception:
                            pass
                        if payoff_chart_card_ref.current:
                            try:
                                payoff_chart_card_ref.current.visible = False
                            except Exception:
                                pass
                else:
                    # No chart path - hide chart
                    try:
                        payoff_chart_ref.current.src = ""
                    except Exception:
                        pass
                    try:
                        payoff_chart_ref.current.visible = False
                    except Exception:
                        pass
                    try:
                        payoff_chart_ref.current.height = 0
                    except Exception:
                        pass
                    if payoff_chart_card_ref.current:
                        try:
                            payoff_chart_card_ref.current.visible = False
                        except Exception:
                            pass
                    logger.info("No chart path produced; chart hidden")

            except Exception as exc:
                logger.warning("Chart update failed: %s", exc)
                try:
                    payoff_chart_ref.current.visible = False
                except Exception:
                    pass
                try:
                    payoff_chart_ref.current.height = 0
                except Exception:
                    pass
                if payoff_chart_card_ref.current:
                    try:
                        payoff_chart_card_ref.current.visible = False
                    except Exception:
                        pass

            _safe_update(payoff_chart_ref.current)

    def _refresh() -> None:
        nonlocal liabilities
        liabilities = ctx.liability_repo.list_all(user_id=uid)
        has_liabilities = bool(liabilities)
        total_debt = ctx.liability_repo.get_total_debt(user_id=uid)
        weighted_apr = ctx.liability_repo.get_weighted_apr(user_id=uid)
        total_min_payment = sum(li.minimum_payment for li in liabilities)

        # Dynamically update content list based on whether we have liabilities
        if content_ref.current and len(content_ref.current.controls) == 2:
            # Remove the temporary spacer and add the actual content
            content_ref.current.controls.pop()  # Remove spacer
            if has_liabilities:
                content_ref.current.controls.append(main_section)
                main_content_ref.current.visible = True
            else:
                content_ref.current.controls.append(empty_state)
                empty_state_ref.current.visible = True

        if total_debt_text.current:
            total_debt_text.current.value = f"${total_debt:,.2f}"
            _safe_update(total_debt_text.current)
        if weighted_apr_text.current:
            weighted_apr_text.current.value = f"{weighted_apr:.2f}%"
            _safe_update(weighted_apr_text.current)
        if min_payment_text.current:
            min_payment_text.current.value = f"${total_min_payment:,.2f}"
            _safe_update(min_payment_text.current)

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
            _safe_update(table_ref.current)

        try:
            schedule, payoff, total_interest, months, chart_path = _run_projection(
                liabilities, mode=strategy_state.get("mode", "balanced")
            )
            _log_debts_state("After projection", liabilities, schedule)
            _update_schedule(
                schedule,
                payoff,
                total_interest,
                months,
                has_liabilities=has_liabilities,
                chart_path=chart_path,
            )
        except ValueError as exc:
            show_error_dialog(page, "Payoff calculation failed", str(exc))
        try:
            page.update()
        except AssertionError:
            pass

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
                if payment <= 0:
                    amount_field.error_text = "Payment must be greater than 0"
                    _safe_update(amount_field)
                    return
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
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(
                        f"Payment recorded; new balance ${current.balance:,.2f}"
                        if current
                        else "Payment recorded"
                    ),
                    show_close_icon=True,
                )
                page.snack_bar.open = True
                try:
                    page.update()
                except AssertionError:
                    pass
            except Exception as exc:
                dev_log(ctx.config, "Payment failed", exc=exc, context={"liability": liability.id})
                show_error_dialog(page, "Payment failed", str(exc))

        def _cancel_payment(_e):
            payment_dialog.open = False
            try:
                page.update()
            except AssertionError:
                pass

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
        """Parse combined strategy value like 'snowball_balanced' into strategy and mode."""
        combined = e.control.value or "snowball_balanced"
        parts = combined.split("_", 1)
        strategy = parts[0] if len(parts) > 0 else "snowball"
        mode = parts[1] if len(parts) > 1 else "balanced"

        strategy_state["value"] = strategy
        strategy_state["mode"] = mode
        _refresh()

    # Calculate initial values to prevent grey boxes
    initial_total_debt = sum(li.balance for li in liabilities) if liabilities else 0.0
    initial_weighted_apr = ctx.liability_repo.get_weighted_apr(user_id=uid) if liabilities else 0.0
    initial_min_payment = sum(li.minimum_payment for li in liabilities) if liabilities else 0.0

    summary = ft.Row(
        [
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Total Debt", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(
                                f"${initial_total_debt:,.2f}",
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                ref=total_debt_text
                            ),
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
                            ft.Text(
                                f"{initial_weighted_apr:.2f}%",
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                ref=weighted_apr_text
                            ),
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
                            ft.Text(
                                f"${initial_min_payment:,.2f}",
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                ref=min_payment_text
                            ),
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
                            ft.Text(
                                "$0.00",
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                ref=interest_text
                            ),
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

    def _schedule_prev_page(_):
        """Go to previous page of schedule."""
        if schedule_state["current_page"] > 0:
            schedule_state["current_page"] -= 1
            _refresh()

    def _schedule_next_page(_):
        """Go to next page of schedule."""
        total_pages = max(1, (schedule_state["total_rows"] + schedule_state["page_size"] - 1) // schedule_state["page_size"])
        if schedule_state["current_page"] < total_pages - 1:
            schedule_state["current_page"] += 1
            _refresh()

    schedule_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Payoff schedule", weight=ft.FontWeight.BOLD, expand=True),
                            ft.Text("", ref=schedule_page_ref, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(
                        [
                            ft.Text("Month", width=110, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text("Payment", width=130, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text("Remaining", width=150, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Column(controls=[], ref=schedule_ref, spacing=6),
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.CHEVRON_LEFT,
                                tooltip="Previous page",
                                on_click=_schedule_prev_page,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CHEVRON_RIGHT,
                                tooltip="Next page",
                                on_click=_schedule_next_page,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
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
                    ft.Text("Payoff strategy", weight=ft.FontWeight.BOLD),
                    ft.Dropdown(
                        label="Payoff Strategy",
                        width=320,
                        value=f"{strategy_state.get('value', 'snowball')}_{strategy_state.get('mode', 'balanced')}",
                        options=[
                            ft.dropdown.Option("snowball_aggressive", "Snowball - Aggressive"),
                            ft.dropdown.Option("snowball_balanced", "Snowball - Balanced"),
                            ft.dropdown.Option("snowball_minimum", "Snowball - Minimum Only"),
                            ft.dropdown.Option("avalanche_aggressive", "Avalanche - Aggressive"),
                            ft.dropdown.Option("avalanche_balanced", "Avalanche - Balanced"),
                            ft.dropdown.Option("avalanche_minimum", "Avalanche - Minimum Only"),
                        ],
                        on_change=_on_strategy_change,
                    ),
                    ft.Text(
                        "Snowball: pay smallest balance first. Avalanche: pay highest APR first.",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ]
            ),
            ft.Column(
                [
                    ft.Text("", ref=payoff_text),
                ],
                expand=True,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.START,
        wrap=True,
    )

    payoff_summary = ft.Text(
        "Snowball: smallest balance first. Avalanche: highest APR first. Payment mode adds surplus toward the current focus debt.",
        size=12,
        color=ft.Colors.ON_SURFACE_VARIANT,
        selectable=True,
    )

    empty_state = ft.Container(
        ref=empty_state_ref,
        content=ft.Column(
            [
                ft.Icon(ft.Icons.CREDIT_CARD_OFF, size=64, color=ft.Colors.OUTLINE),
                ft.Text("No debts tracked yet", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Add a debt to see payoff projections and strategies."),
                ft.FilledButton(
                    "Add Debt",
                    icon=ft.Icons.ADD,
                    on_click=lambda _: controllers.navigate(page, "/add-data"),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
        ),
        alignment=ft.alignment.center,
        expand=True,
        visible=False,  # Will be set to True by _refresh() if needed
        padding=ft.padding.all(32),
    )

    main_section = ft.Column(
        ref=main_content_ref,
        controls=[
            ft.Container(height=16),
            summary,
            ft.Container(height=24),
            strategy_row,
            payoff_summary,
            ft.Card(content=ft.Container(content=table, padding=12)),
            ft.Column(
                controls=[
                    ft.Container(content=schedule_card),
                    ft.Container(
                        ref=payoff_chart_card_ref,
                        content=ft.Card(
                            content=ft.Container(
                                padding=12,
                                content=ft.Column(
                                    controls=[
                                        ft.Text("Payoff chart", weight=ft.FontWeight.BOLD),
                                        ft.Image(ref=payoff_chart_ref, height=0, visible=False),
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
                        visible=False,
                    ),
                ],
                spacing=12,
            ),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        visible=False,  # Start hidden - will be shown by _refresh() after mount
    )

    content_ref = ft.Ref[ft.Column]()

    content = ft.Column(
        ref=content_ref,
        controls=[
            ft.Row(
                controls=[
                    ft.Text("Debts & Liabilities", size=24, weight=ft.FontWeight.BOLD),
                    ft.FilledButton(
                        "Add liability",
                        icon=ft.Icons.ADD,
                        on_click=lambda _: controllers.navigate(page, "/add-data"),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                wrap=True,
                run_spacing=8,
            ),
            ft.Container(height=200),  # Temporary spacer - will be replaced
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    app_bar = build_app_bar(ctx, "Debts", page)
    main_layout = build_main_layout(ctx, page, "/debts", content, use_menu_bar=True)

    # Defer the initial refresh until after view is mounted
    def _delayed_refresh():
        import time
        time.sleep(0.5)  # Give Flet time to mount the view
        try:
            logger.info("Starting deferred refresh for debts view")
            _refresh()
            logger.info("Deferred refresh completed successfully")
        except Exception as exc:
            logger.warning("Delayed refresh failed: %s", exc, exc_info=True)

    threading.Thread(target=_delayed_refresh, daemon=True).start()

    return ft.View(
        route="/debts",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )
