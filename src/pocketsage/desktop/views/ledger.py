"""Ledger view with desktop-focused register layout and refreshed workflows."""
# TODO(@codex-max, ledger-ui): implement three-tier layout (filters, summary cards, two-column).
# TODO(@codex-max, ledger-ui): replace old table layout with register-style table + actions column.
# TODO(@codex-max, ledger-flow): implement Add/Edit transaction dialog + validation + refresh hooks.
# TODO(@codex-max, ledger-flow): centralize transaction creation/update in a helper/service.
# TODO(@codex-max, ledger-bugs): fix category filter 'All' ValueError and make filters robust.
# TODO(@codex-max, ledger-io): wire Import/Export/CSV Help buttons with proper feedback.
# TODO(@codex-max, ledger-charts): refresh spending chart and budget progress after data changes.

from __future__ import annotations

import math
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Iterable

import flet as ft

from ...devtools import dev_log
from ...logging_config import get_logger
from ...models.account import Account
from ...models.category import Category
from ...models.transaction import Transaction
from ...services import export_csv, ledger_service
from .. import controllers

logger = get_logger(__name__)
from ..charts import spending_chart_png
from ..components import (
    build_app_bar,
    build_main_layout,
    build_progress_bar,
    show_confirm_dialog,
    show_error_dialog,
)

if TYPE_CHECKING:
    from ..context import AppContext


def _format_currency(amount: float) -> str:
    return f"${amount:,.2f}"


def _month_bounds(target: date) -> tuple[date, date]:
    """Return the first/last day of the month for the given date."""

    first = target.replace(day=1)
    last = target.replace(day=monthrange(target.year, target.month)[1])
    return first, last


def build_ledger_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the ledger page with filters, register, and insights."""

    uid = ctx.require_user_id()
    per_page = 25
    current_page = 1
    cached_transactions: list[Transaction] = []
    total_pages = 1

    start_default, end_default = _month_bounds(ctx.current_month)

    start_field = ft.TextField(
        label="Start date",
        hint_text="YYYY-MM-DD",
        width=160,
        value="",
    )
    end_field = ft.TextField(
        label="End date",
        hint_text="YYYY-MM-DD",
        width=160,
        value="",
    )
    quick_range = ft.Dropdown(
        label="Quick range",
        options=[
            ft.dropdown.Option("this_month", "This month"),
            ft.dropdown.Option("last_month", "Last month"),
            ft.dropdown.Option("ytd", "Year-to-date"),
            ft.dropdown.Option("all_time", "All time"),
        ],
        width=150,
        value="all_time",
    )
    category_field = ft.Dropdown(label="Category", width=220, value="all")
    type_field = ft.Dropdown(
        label="Type",
        options=[
            ft.dropdown.Option("all", "All types"),
            ft.dropdown.Option("income", "Income"),
            ft.dropdown.Option("expense", "Expense"),
        ],
        width=140,
        value="all",
    )
    search_field = ft.TextField(
        label="Search",
        hint_text="Description, payee, notes",
        width=220,
    )

    table_ref = ft.Ref[ft.DataTable]()
    page_label = ft.Ref[ft.Text]()
    income_text = ft.Ref[ft.Text]()
    expense_text = ft.Ref[ft.Text]()
    net_text = ft.Ref[ft.Text]()
    spending_image_ref = ft.Ref[ft.Image]()
    spending_empty_ref = ft.Ref[ft.Text]()
    budget_progress_ref = ft.Ref[ft.Column]()
    recent_categories_ref = ft.Ref[ft.Column]()

    def _ensure_default_account() -> Account:
        accounts = ctx.account_repo.list_all(user_id=uid)
        if accounts:
            return accounts[0]
        return ctx.account_repo.create(
            Account(name="Cash", currency="USD", user_id=uid), user_id=uid
        )

    def _ensure_baseline_categories() -> list[Category]:
        categories = ctx.category_repo.list_all(user_id=uid)
        if categories:
            return categories
        defaults = [
            ("Salary", "income"),
            ("Bonus", "income"),
            ("Groceries", "expense"),
            ("Dining Out", "expense"),
            ("Rent/Mortgage", "expense"),
            ("Utilities", "expense"),
            ("Transport", "expense"),
        ]
        for name, cat_type in defaults:
            ctx.category_repo.upsert_by_slug(
                Category(
                    name=name,
                    slug=name.lower().replace(" ", "-"),
                    category_type=cat_type,
                    user_id=uid,
                ),
                user_id=uid,
            )
        return ctx.category_repo.list_all(user_id=uid)

    def _hydrate_category_filter(selected: str | None = None) -> list[Category]:
        cats = _ensure_baseline_categories()
        incomes = [c for c in cats if c.category_type == "income"]
        expenses = [c for c in cats if c.category_type == "expense"]
        options: list[ft.dropdown.Option] = [ft.dropdown.Option("all", "All categories")]
        options += [ft.dropdown.Option(str(c.id), f"Income - {c.name}") for c in incomes if c.id]
        options += [
            ft.dropdown.Option(str(c.id), f"Expense - {c.name}") for c in expenses if c.id
        ]
        category_field.options = options
        category_field.value = selected or category_field.value or "all"
        if category_field.page:
            category_field.update()
        return cats

    _hydrate_category_filter()

    def _parse_date(field: ft.TextField) -> datetime | None:
        raw = (field.value or "").strip()
        if not raw:
            field.error_text = None
            return None
        try:
            parsed = datetime.fromisoformat(raw)
            field.error_text = None
            return parsed
        except ValueError:
            field.error_text = "Use YYYY-MM-DD"
            if field.page:
                field.update()
            raise

    def _set_quick_range(value: str):
        today = date.today()
        start: date | None = None
        end: date | None = None
        if value == "this_month":
            start, end = _month_bounds(today)
        elif value == "last_month":
            first_this, _ = _month_bounds(today)
            last_month_end = first_this - timedelta(days=1)
            start, end = _month_bounds(last_month_end)
        elif value == "ytd":
            start = date(today.year, 1, 1)
            end = today
        elif value == "all_time":
            start = None
            end = None
        if start:
            start_field.value = start.isoformat()
        else:
            start_field.value = ""
        if end:
            end_field.value = end.isoformat()
        else:
            end_field.value = ""
        if quick_range.page:
            quick_range.update()
        page.update()

    quick_range.on_change = lambda _: _set_quick_range(quick_range.value or "this_month")

    def _render_summary(totals: dict[str, float]) -> None:
        if income_text.current:
            income_text.current.value = _format_currency(totals["income"])
        if expense_text.current:
            expense_text.current.value = _format_currency(totals["expenses"])
        if net_text.current:
            net_text.current.value = _format_currency(totals["net"])

    def _render_recent_categories(breakdown: list[dict[str, object]]) -> None:
        container = recent_categories_ref.current
        if not container:
            return
        if not breakdown:
            container.controls = [ft.Text("No expense categories yet.")]
        else:
            controls: list[ft.Control] = []
            total_spend = sum(float(item["amount"]) for item in breakdown) or 1.0
            for item in ledger_service.top_categories(breakdown, limit=5):
                amount = float(item["amount"])
                pct = (amount / total_spend) * 100
                controls.append(
                    ft.Row(
                        controls=[
                            ft.Text(str(item["name"]), weight=ft.FontWeight.BOLD),
                            ft.Text(f"{_format_currency(amount)} - {pct:.1f}%"),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    )
                )
            container.controls = controls
        if container.page:
            container.update()

    def _render_spending_chart(transactions: Iterable[Transaction]) -> None:
        expenses = [t for t in transactions if t.amount < 0]
        image = spending_image_ref.current
        empty_state = spending_empty_ref.current
        if not image or not empty_state:
            return
        if not expenses:
            image.visible = False
            empty_state.visible = True
            if image.page:
                image.update()
            if empty_state.page:
                empty_state.update()
            return
        try:
            categories = ctx.category_repo.list_all(user_id=uid)
            lookup = {c.id: c.name for c in categories if c.id is not None}
            path = spending_chart_png(expenses, category_lookup=lookup)
            image.src = path.as_posix()
            image.visible = True
            empty_state.visible = False
            if image.page:
                image.update()
            if empty_state.page:
                empty_state.update()
        except Exception as exc:  # pragma: no cover - user-facing guard
            dev_log(ctx.config, "Spending chart refresh failed", exc=exc)
            image.visible = False
            empty_state.visible = True
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Saved, but spending chart failed to render"),
                show_close_icon=True,
            )
            page.snack_bar.open = True
            page.update()

    def _render_budget_progress(
        transactions: list[Transaction], start_date: datetime | None
    ) -> None:
        container = budget_progress_ref.current
        if not container:
            return
        target_date = start_date.date() if start_date else ctx.current_month
        month_start, _ = _month_bounds(target_date)
        budget = ctx.budget_repo.get_for_month(
            month_start.year, month_start.month, user_id=uid
        )
        controls: list[ft.Control] = []
        if not budget:
            controls.append(
                ft.Text("No budget set for this month", color=ft.Colors.ON_SURFACE_VARIANT)
            )
        else:
            lines = ctx.budget_repo.get_lines_for_budget(budget.id, user_id=uid)
            overall_planned = sum(line_item.planned_amount for line_item in lines)
            total_spent = 0.0
            for line in lines:
                actual = sum(
                    abs(t.amount)
                    for t in transactions
                    if t.amount < 0 and t.category_id == line.category_id
                )
                total_spent += actual
                category = ctx.category_repo.get_by_id(line.category_id, user_id=uid)
                controls.append(
                    build_progress_bar(
                        current=actual,
                        maximum=line.planned_amount or 0.01,
                        label=category.name if category else "Uncategorized",
                    )
                )
            if overall_planned > 0:
                controls.insert(
                    0,
                    build_progress_bar(
                        current=total_spent, maximum=overall_planned, label="Overall budget"
                    ),
                )
        container.controls = controls
        if container.page:
            container.update()

    def _render_table(transactions: list[Transaction]) -> None:
        table = table_ref.current
        if not table:
            return
        rows: list[ft.DataRow] = []
        for tx in transactions:
            category = (
                ctx.category_repo.get_by_id(tx.category_id, user_id=uid)
                if tx.category_id
                else None
            )
            if getattr(tx, "liability_id", None):
                type_label = "Debt"
            else:
                type_label = "Income" if tx.amount >= 0 else "Expense"
            amount_color = ft.Colors.GREEN if tx.amount >= 0 else ft.Colors.RED
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(tx.occurred_at.strftime("%Y-%m-%d"))),
                        ft.DataCell(ft.Text(tx.memo or "")),
                        ft.DataCell(ft.Text(category.name if category else "Uncategorized")),
                        ft.DataCell(ft.Text(type_label)),
                        ft.DataCell(ft.Text(_format_currency(tx.amount), color=amount_color)),
                        ft.DataCell(ft.Text("")),
                        ft.DataCell(
                            ft.Row(
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        tooltip="Edit",
                                        on_click=lambda _, item=tx: open_transaction_dialog(item),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=ft.Colors.RED,
                                        tooltip="Delete",
                                        on_click=lambda _, tx_id=tx.id: delete_transaction(tx_id),
                                    ),
                                ]
                            )
                        ),
                    ]
                )
            )
        if not rows:
            rows = [
                ft.DataRow(
                    cells=[ft.DataCell(ft.Text("No transactions in this period."))]
                    + [ft.DataCell(ft.Text("")) for _ in range(6)],
                )
            ]
        table.rows = rows
        if table.page:
            table.update()

    def _load_transactions(page_index: int = 1) -> None:
        nonlocal current_page, cached_transactions, total_pages
        try:
            start_dt = _parse_date(start_field)
            end_dt = _parse_date(end_field)
        except ValueError:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Use YYYY-MM-DD for dates"), show_close_icon=True
            )
            page.snack_bar.open = True
            page.update()
            return

        filters = ledger_service.LedgerFilters(
            user_id=uid,
            start_date=start_dt,
            end_date=end_dt,
            category_id=ledger_service.normalize_category_value(category_field.value),
            text=(search_field.value or "").strip() or None,
            txn_type=type_field.value or "all",
        )
        txs = ledger_service.filtered_transactions(ctx.transaction_repo, filters)
        cached_transactions = txs
        total_pages = max(1, math.ceil(len(txs) / per_page))
        current_page = max(1, min(page_index, total_pages))
        page_slice, _ = ledger_service.paginate_transactions(
            txs, ledger_service.Pagination(page=current_page, per_page=per_page)
        )
        _render_table(page_slice)
        _render_summary(ledger_service.compute_summary(txs))
        breakdown = ledger_service.compute_spending_by_category(
            txs, ctx.category_repo.list_all(user_id=uid)
        )
        _render_spending_chart(txs)
        _render_budget_progress(txs, start_dt)
        _render_recent_categories(breakdown)
        if page_label.current:
            page_label.current.value = f"Page {current_page} / {total_pages}"
            if getattr(page_label.current, "page", None):
                page_label.current.update()
        page.update()

    def _reset_filters(_=None) -> None:
        start_field.value = start_default.isoformat()
        end_field.value = end_default.isoformat()
        quick_range.value = "this_month"
        category_field.value = "all"
        type_field.value = "all"
        search_field.value = ""
        _load_transactions(1)

    def _paginate(delta: int) -> None:
        _load_transactions(current_page + delta)

    def _save_transaction_payload(
        *,
        existing: Transaction | None,
        amount_field: ft.TextField,
        description_field: ft.TextField,
        notes_field: ft.TextField,
        date_field: ft.TextField,
        type_group: ft.RadioGroup,
        category_dd: ft.Dropdown,
        account_dd: ft.Dropdown,
        dialog: ft.AlertDialog,
    ) -> None:
        """Validate and persist a transaction from the dialog."""

        logger.info("Saving transaction", extra={"is_edit": existing is not None})
        logger.info(f"Save button clicked - amount: {amount_field.value}, desc: {description_field.value}, date: {date_field.value}")
        try:
            description = (description_field.value or "").strip()
            logger.debug(f"Description: {description}")
            if not description:
                logger.warning("Description validation failed - empty")
                description_field.error_text = "Description is required"
                description_field.update()
                raise ValueError("Description required")
            description_field.error_text = None

            try:
                occurred_at = datetime.fromisoformat((date_field.value or "").strip())
                date_field.error_text = None
                logger.info(f"Parsed date: {occurred_at}")
            except ValueError as e:
                logger.warning(f"Date parsing failed: {e}")
                date_field.error_text = "Use YYYY-MM-DD"
                if date_field.page:
                    date_field.update()
                raise

            raw_amount = float(amount_field.value or 0)
            logger.info(f"Raw amount: {raw_amount}")
            if raw_amount == 0:
                logger.warning("Amount validation failed - zero")
                amount_field.error_text = "Amount cannot be zero"
                amount_field.update()
                raise ValueError("Amount cannot be zero")
            txn_type = type_group.value or "expense"
            amount = abs(raw_amount)
            if txn_type == "expense":
                amount = -amount
            amount_field.error_text = None
            logger.info(f"Final amount: {amount} (type: {txn_type})")

            category_id = ledger_service.normalize_category_value(category_dd.value)
            account_id = ledger_service.normalize_category_value(account_dd.value)
            memo = description
            if notes_field.value:
                memo = f"{description} - {notes_field.value.strip()}"

            logger.info(f"Calling save_transaction - memo: {memo}, occurred_at: {occurred_at}, user_id: {uid}")
            saved = ledger_service.save_transaction(
                ctx.transaction_repo,
                existing=existing,
                amount=amount,
                memo=memo,
                occurred_at=occurred_at,
                category_id=category_id,
                account_id=account_id,
                currency="USD",
                user_id=uid,
            )
            logger.info(f"Transaction saved successfully - id: {saved.id}")
            dialog.open = False
            page.dialog = None
            _load_transactions(current_page)
            page.snack_bar = ft.SnackBar(
                content=ft.Text(
                    "Transaction updated" if existing else "Transaction saved"
                ),
                show_close_icon=True,
            )
            page.snack_bar.open = True
            page.update()
            logger.info("Dialog closed and page updated")
        except Exception as exc:
            logger.error(f"Save transaction failed: {exc}", exc_info=True)
            if isinstance(exc, ValueError):
                dev_log(ctx.config, "Ledger validation failed", exc=exc)
            else:
                dev_log(ctx.config, "Ledger save failed", exc=exc)
            show_error_dialog(page, "Save failed", str(exc))

    def _close_dialog(dialog: ft.AlertDialog) -> None:
        """Helper to properly close a dialog."""
        logger.debug("Closing dialog")
        dialog.open = False
        page.update()
        logger.debug("Dialog closed and page updated")

    def open_transaction_dialog(tx: Transaction | None = None) -> None:
        logger.info("Opening transaction dialog", extra={"is_edit": tx is not None})
        base_categories = _ensure_baseline_categories()
        default_account = _ensure_default_account()
        is_edit = tx is not None

        def _options_for_type(target_type: str) -> list[ft.dropdown.Option]:
            filtered = [
                c
                for c in base_categories
                if target_type == "income" and c.category_type == "income"
            ] + [
                c
                for c in base_categories
                if target_type == "expense" and c.category_type == "expense"
            ]
            # Transfers can select any category or none
            if target_type == "transfer":
                filtered = base_categories
            options = [ft.dropdown.Option("all", "No category")]
            options += [ft.dropdown.Option(str(c.id), c.name) for c in filtered if c.id]
            return options

        description_field = ft.TextField(
            label="Description",
            value=tx.memo if tx else "",
            expand=True,
        )
        notes_field = ft.TextField(label="Notes (optional)", value="", expand=True)
        amount_field = ft.TextField(
            label="Amount",
            value=str(abs(tx.amount)) if tx else "",
            helper_text="Positive for income; expense will flip the sign automatically.",
            width=220,
        )
        date_field = ft.TextField(
            label="Date",
            value=tx.occurred_at.strftime("%Y-%m-%d")
            if tx
            else datetime.now().strftime("%Y-%m-%d"),
            width=220,
        )
        type_group = ft.RadioGroup(
            value=("income" if tx and tx.amount >= 0 else "expense"),
            content=ft.Row(
                controls=[
                    ft.Radio(value="income", label="Income"),
                    ft.Radio(value="expense", label="Expense"),
                    ft.Radio(value="transfer", label="Transfer"),
                ],
                spacing=12,
            ),
        )
        category_dd = ft.Dropdown(
            label="Category",
            options=_options_for_type(type_group.value or "expense"),
            value=str(tx.category_id) if tx and tx.category_id else "all",
            width=240,
        )
        account_dd = ft.Dropdown(
            label="Account",
            options=[
                ft.dropdown.Option(str(a.id), a.name)
                for a in ctx.account_repo.list_all(user_id=uid)
            ],
            value=str(tx.account_id) if tx and tx.account_id else str(default_account.id),
            width=240,
        )

        def _on_type_change(_):
            category_dd.options = _options_for_type(type_group.value or "expense")
            if category_dd.page:
                category_dd.update()

        type_group.on_change = _on_type_change

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Update transaction" if is_edit else "Add transaction"),
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Keep everything local; amounts flip sign based on type.",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    type_group,
                    ft.Row(controls=[amount_field, date_field], spacing=10),
                    category_dd,
                    account_dd,
                    description_field,
                    notes_field,
                ],
                tight=True,
                width=520,
                spacing=10,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: (_close_dialog(dialog))),
                ft.FilledButton(
                    "Save",
                    on_click=lambda e: (
                        logger.info("SAVE BUTTON CLICKED!"),
                        _save_transaction_payload(
                            existing=tx,
                            amount_field=amount_field,
                            description_field=description_field,
                            notes_field=notes_field,
                            date_field=date_field,
                            type_group=type_group,
                            category_dd=category_dd,
                            account_dd=account_dd,
                            dialog=dialog,
                        ),
                    ),
                ),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def delete_transaction(txn_id: int | None) -> None:
        if txn_id is None:
            return

        def _confirm():
            try:
                ctx.transaction_repo.delete(txn_id, user_id=uid)
                dev_log(ctx.config, "Transaction deleted", context={"id": txn_id})
                _load_transactions(current_page)
            except Exception as exc:
                dev_log(ctx.config, "Delete failed", exc=exc, context={"id": txn_id})
                show_error_dialog(page, "Delete failed", str(exc))

        show_confirm_dialog(page, "Delete transaction", "Are you sure?", _confirm)

    def _export_csv(_=None) -> None:
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        export_dir = ctx.config.DATA_DIR / "exports"
        output_path = export_dir / f"ledger_export_{stamp}.csv"
        try:
            export_csv.export_transactions_csv(
                transactions=cached_transactions, output_path=output_path
            )
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Exported to {output_path}"), show_close_icon=True
            )
            page.snack_bar.open = True
            page.update()
        except Exception as exc:  # pragma: no cover - user-facing guard
            show_error_dialog(page, "Export failed", str(exc))

    # Reset page scroll handler to avoid lingering callbacks
    page.on_scroll = None

    filter_bar = ft.Row(
        controls=[
            start_field,
            end_field,
            quick_range,
            category_field,
            type_field,
            search_field,
            ft.FilledButton(
                "Apply",
                icon=ft.Icons.FILTER_ALT,
                on_click=lambda _: _load_transactions(1),
            ),
            ft.TextButton("Reset", on_click=_reset_filters),
        ],
        wrap=True,
        spacing=8,
        run_spacing=8,
    )
    # Close dropdown overlays when the page scrolls to avoid floating menus
    def _close_filters_on_scroll(_):
        for dd in (quick_range, category_field, type_field):
            try:
                dd.open = False  # type: ignore[attr-defined]
            except Exception:
                pass
    page.on_scroll = _close_filters_on_scroll

    summary_cards = ft.ResponsiveRow(
        controls=[
            ft.Container(
                content=ft.Card(
                    content=ft.Container(
                        ft.Column(
                            controls=[
                                ft.Text("Income (this period)"),
                                ft.Text("", ref=income_text, size=20, weight=ft.FontWeight.BOLD),
                            ]
                        ),
                        padding=12,
                    ),
                ),
                col={"sm": 12, "md": 4},
            ),
            ft.Container(
                content=ft.Card(
                    content=ft.Container(
                        ft.Column(
                            controls=[
                                ft.Text("Expenses (this period)"),
                                ft.Text("", ref=expense_text, size=20, weight=ft.FontWeight.BOLD),
                            ]
                        ),
                        padding=12,
                    ),
                ),
                col={"sm": 12, "md": 4},
            ),
            ft.Container(
                content=ft.Card(
                    content=ft.Container(
                        ft.Column(
                            controls=[
                                ft.Text("Net (this period)"),
                                ft.Text("", ref=net_text, size=20, weight=ft.FontWeight.BOLD),
                            ]
                        ),
                        padding=12,
                    ),
                ),
                col={"sm": 12, "md": 4},
            ),
        ],
        spacing=12,
        run_spacing=12,
    )

    table = ft.DataTable(
        ref=table_ref,
        columns=[
            ft.DataColumn(ft.Text("Date")),
            ft.DataColumn(ft.Text("Description")),
            ft.DataColumn(ft.Text("Category")),
            ft.DataColumn(ft.Text("Type")),
            ft.DataColumn(ft.Text("Amount")),
            ft.DataColumn(ft.Text("Balance")),
            ft.DataColumn(ft.Text("Actions")),
        ],
        rows=[],
        expand=True,
        heading_row_height=36,
    )

    pagination_row = ft.Row(
        controls=[
            ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                tooltip="Previous page",
                on_click=lambda _: _paginate(-1),
            ),
            ft.Text("", ref=page_label),
            ft.IconButton(
                icon=ft.Icons.ARROW_FORWARD,
                tooltip="Next page",
                on_click=lambda _: _paginate(1),
            ),
        ],
        spacing=4,
    )

    toolbar = ft.Row(
        controls=[
            ft.Row(
                controls=[
                    ft.TextButton(
                        "Import CSV",
                        on_click=lambda _: controllers.start_ledger_import(ctx, page),
                    ),
                    ft.TextButton("Export CSV", on_click=_export_csv),
                    ft.TextButton("CSV Help", on_click=lambda _: controllers.go_to_help(page)),
                ],
                spacing=8,
            ),
            ft.Row(
                controls=[
                    pagination_row,
                    ft.FilledButton(
                        "+ Add transaction",
                        icon=ft.Icons.ADD,
                        on_click=lambda _: controllers.navigate(page, "/add-data"),
                    ),
                ],
                alignment=ft.MainAxisAlignment.END,
                spacing=12,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        wrap=True,
        run_spacing=8,
    )

    register_card = ft.Card(
        content=ft.Container(
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("Transaction register", weight=ft.FontWeight.BOLD, size=18),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(),
                    ft.Container(table, expand=True),
                    toolbar,
                ],
                expand=True,
                spacing=12,
            ),
            padding=12,
        ),
        expand=True,
        elevation=2,
    )

    spending_card = ft.Card(
        content=ft.Container(
            ft.Column(
                controls=[
                    ft.Text("Spending breakdown (this period)", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Expense categories only; refreshed when filters change.",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Image(
                        ref=spending_image_ref,
                        height=220,
                        fit=ft.ImageFit.CONTAIN,
                        visible=False,
                    ),
                    ft.Text(
                        "No expense data for this period",
                        ref=spending_empty_ref,
                        visible=True,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                spacing=8,
            ),
            padding=12,
        ),
        elevation=2,
    )

    budget_card = ft.Card(
        content=ft.Container(
            ft.Column(
                controls=[
                    ft.Text("Budget progress (this period)", size=18, weight=ft.FontWeight.BOLD),
                    ft.Column(ref=budget_progress_ref, spacing=8),
                ],
                spacing=8,
            ),
            padding=12,
        ),
        elevation=2,
    )

    recent_card = ft.Card(
        content=ft.Container(
            ft.Column(
                controls=[
                    ft.Text("Recent categories", size=18, weight=ft.FontWeight.BOLD),
                    ft.Column(ref=recent_categories_ref, spacing=6),
                ],
                spacing=8,
            ),
            padding=12,
        ),
        elevation=2,
    )

    insights_column = ft.Column(
        controls=[spending_card, budget_card, recent_card],
        spacing=12,
        expand=3,
        scroll=ft.ScrollMode.AUTO,
    )

    register_column = ft.Column(
        controls=[
            register_card,
        ],
        expand=7,
    )

    main_body = ft.Row(
        controls=[register_column, insights_column],
        spacing=12,
        expand=True,
    )

    content = ft.Column(
        controls=[
            ft.Row(
                controls=[ft.Text("Ledger", size=24, weight=ft.FontWeight.BOLD)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(height=8),
            filter_bar,
            ft.Container(height=8),
            summary_cards,
            ft.Container(height=12),
            main_body,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if getattr(ctx, "pending_refresh_route", None) == "/ledger":
        ctx.pending_refresh_route = None
    _load_transactions()
    if getattr(ctx, "pending_new_transaction", False):
        ctx.pending_new_transaction = False
        open_transaction_dialog(None)

    app_bar = build_app_bar(ctx, "Ledger", page)
    main_layout = build_main_layout(ctx, page, "/ledger", content, use_menu_bar=True)
    return ft.View(route="/ledger", appbar=app_bar, controls=main_layout, padding=0)
