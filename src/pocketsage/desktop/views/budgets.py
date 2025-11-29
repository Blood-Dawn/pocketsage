"""Budgets view implementation."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from typing import TYPE_CHECKING

import flet as ft

from ...models.budget import Budget, BudgetLine
from ...models.category import Category
from ..components import build_app_bar, build_main_layout, build_progress_bar
from ..components.dialogs import show_budget_dialog

if TYPE_CHECKING:
    from ..context import AppContext


def build_budgets_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the budgets view."""

    uid = ctx.require_user_id()
    # Get current month's budget
    today = ctx.current_month
    budget = ctx.budget_repo.get_for_month(today.year, today.month, user_id=uid)

    def _shift_month(delta: int):
        current = ctx.current_month
        next_month = (current.month - 1 + delta) % 12 + 1
        next_year = current.year + ((current.month - 1 + delta) // 12)
        ctx.current_month = date(next_year, next_month, 1)
        page.go("/budgets")

    def refresh_view():
        page.go("/budgets")

    def _close_dialog(dialog: ft.AlertDialog) -> None:
        """Helper to properly close a dialog."""
        dialog.open = False
        page.update()

    def show_create_budget_dialog():
        """Open budget creation/editing dialog using reusable component."""
        show_budget_dialog(
            ctx=ctx,
            page=page,
            target_month=ctx.current_month,
            on_save_callback=refresh_view,
        )

    def copy_previous_month():
        prev_month = today.month - 1 or 12
        prev_year = today.year - 1 if today.month == 1 else today.year
        prev_budget = ctx.budget_repo.get_for_month(prev_year, prev_month, user_id=uid)
        if not prev_budget:
            page.snack_bar = ft.SnackBar(content=ft.Text("No previous month budget to copy"))
            page.snack_bar.open = True
            page.update()
            return
        start = today.replace(day=1)
        end = today.replace(day=monthrange(today.year, today.month)[1])
        new_budget = Budget(
            period_start=start,
            period_end=end,
            label=f"{today.strftime('%B %Y')} Budget",
            user_id=uid,
        )
        created = ctx.budget_repo.create(new_budget, user_id=uid)
        prev_lines = ctx.budget_repo.get_lines_for_budget(prev_budget.id, user_id=uid)

        for line in prev_lines:
            # Start with previous month's planned amount as the base budget
            base_budget = line.planned_amount
            new_planned = base_budget

            # If rollover enabled, adjust for surplus/deficit from previous month
            if line.rollover_enabled:
                # Get actual spending for this category in previous month
                prev_txs = ctx.transaction_repo.search(
                    start_date=datetime(prev_year, prev_month, 1),
                    end_date=datetime(
                        prev_year,
                        prev_month,
                        monthrange(prev_year, prev_month)[1],
                        23,
                        59,
                        59,
                    ),
                    category_id=line.category_id,
                    user_id=uid,
                )
                actual_spent = sum(abs(t.amount) for t in prev_txs if t.amount < 0)

                # Rollover: carry forward the surplus (underspent) or deficit (overspent)
                # This maintains the base budget AND adds the rollover amount
                # Example: Budgeted $100, spent $80 -> Next month base $100 + $20 surplus = $120
                # Example: Budgeted $100, spent $120 -> Next month base $100 - $20 deficit = $80
                surplus_or_deficit = base_budget - actual_spent
                new_planned = max(0.0, base_budget + surplus_or_deficit)  # Ensure non-negative

            clone = BudgetLine(
                budget_id=created.id,
                category_id=line.category_id,
                planned_amount=round(new_planned, 2),
                rollover_enabled=line.rollover_enabled,
                user_id=uid,
            )
            ctx.budget_repo.create_line(clone, user_id=uid)
        page.snack_bar = ft.SnackBar(content=ft.Text("Copied previous month budget"))
        page.snack_bar.open = True
        refresh_view()

    def add_budget_line(budget_id: int):
        categories = ctx.category_repo.list_all(user_id=uid)
        if not categories:
            default_cat = ctx.category_repo.create(
                Category(
                    name="General",
                    slug="general",
                    category_type="expense",
                    user_id=uid,
                ),
                user_id=uid,
            )
            categories = [default_cat]
        category_dd = ft.Dropdown(
            label="Category",
            options=[ft.dropdown.Option(str(c.id), c.name) for c in categories],
            width=240,
        )
        amount_field = ft.TextField(label="Planned amount", width=180)

        def save_line(_):
            try:
                if not category_dd.value:
                    raise ValueError("Select a category")
                line = BudgetLine(
                    budget_id=budget_id,
                    category_id=int(category_dd.value),
                    planned_amount=float(amount_field.value or 0),
                    rollover_enabled=False,
                    user_id=uid,
                )
                ctx.budget_repo.create_line(line, user_id=uid)
                dlg.open = False
                refresh_view()
            except Exception as exc:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"Failed to add line: {exc}"))
                page.snack_bar.open = True
                page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Add budget line"),
            content=ft.Column(controls=[category_dd, amount_field], spacing=8, tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: _close_dialog(dlg)),
                ft.FilledButton("Save", on_click=save_line),
            ],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def handle_add_line(_):
        """Route add-line requests based on whether a budget exists."""
        if budget and budget.id:
            add_budget_line(int(budget.id))
        else:
            show_create_budget_dialog()

    def _open_budget_dialog(_=None):
        show_budget_dialog(
            ctx=ctx,
            page=page,
            target_month=ctx.current_month,
            on_save_callback=refresh_view,
        )

    if budget:
        # Get budget lines
        lines = ctx.budget_repo.get_lines_for_budget(budget.id, user_id=uid)
        period_start_dt = datetime.combine(budget.period_start, datetime.min.time())
        period_end_dt = datetime.combine(budget.period_end, datetime.max.time())

        # Build budget progress bars
        budget_rows = []
        total_planned = 0
        total_spent = 0

        for line in lines:
            category = ctx.category_repo.get_by_id(line.category_id, user_id=uid)
            if not category:
                continue

            # Get actual spending for this category this month
            transactions = ctx.transaction_repo.search(
                start_date=period_start_dt,
                end_date=period_end_dt,
                category_id=line.category_id,
                user_id=uid,
            )

            actual = sum(abs(t.amount) for t in transactions if t.amount < 0)

            total_planned += line.planned_amount
            total_spent += actual

            progress = build_progress_bar(
                current=actual,
                maximum=line.planned_amount,
                label=category.name,
            )

            def edit_line(_e, line=line):
                amount_field = ft.TextField(
                    label="Planned amount", value=str(line.planned_amount), width=180
                )
                rollover_switch = ft.Switch(label="Rollover enabled", value=line.rollover_enabled)
                categories = ctx.category_repo.list_all(user_id=uid)
                category_dd = ft.Dropdown(
                    label="Category",
                    options=[ft.dropdown.Option(str(c.id), c.name) for c in categories],
                    value=str(line.category_id),
                    width=240,
                )

                def save_edit(_):
                    try:
                        line.category_id = int(category_dd.value)
                        line.planned_amount = float(amount_field.value or 0)
                        line.rollover_enabled = bool(rollover_switch.value)
                        ctx.budget_repo.update_line(line, user_id=uid)
                        dlg.open = False
                        refresh_view()
                    except Exception as exc:
                        page.snack_bar = ft.SnackBar(
                            content=ft.Text(f"Failed to update line: {exc}")
                        )
                        page.snack_bar.open = True
                        page.update()

                dlg = ft.AlertDialog(
                    title=ft.Text("Edit budget line"),
                    content=ft.Column(
                        [category_dd, amount_field, rollover_switch], spacing=8, tight=True
                    ),
                    actions=[
                        ft.TextButton("Cancel", on_click=lambda _: _close_dialog(dlg)),
                        ft.FilledButton("Save", on_click=save_edit),
                    ],
                )
                page.dialog = dlg
                dlg.open = True
                page.update()

            def delete_line(_e, line_id=line.id):
                if line_id is None:
                    page.snack_bar = ft.SnackBar(content=ft.Text("Cannot delete an unsaved line"))
                    page.snack_bar.open = True
                    page.update()
                    return
                try:
                    ctx.budget_repo.delete_line(line_id, user_id=uid)
                    refresh_view()
                except Exception as exc:
                    page.snack_bar = ft.SnackBar(content=ft.Text(f"Failed to delete: {exc}"))
                    page.snack_bar.open = True
                    page.update()

            budget_rows.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(content=progress, expand=True),
                            ft.IconButton(icon=ft.Icons.EDIT, tooltip="Edit", on_click=edit_line),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                tooltip="Delete",
                                icon_color=ft.Colors.RED,
                                on_click=delete_line,
                            ),
                        ]
                    ),
                    padding=16,
                    border=ft.border.only(
                        bottom=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT)
                    ),
                    on_click=lambda _e, l=line: edit_line(_e, line=l),
                )
            )

        # Summary card
        summary_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Budget Summary", size=18, weight=ft.FontWeight.BOLD),
                        ft.Container(height=16),
                        ft.Row(
                            controls=[
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            "Total Budgeted",
                                            size=14,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                        ft.Text(
                                            f"${total_planned:,.2f}",
                                            size=24,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                    ],
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            "Total Spent",
                                            size=14,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                        ft.Text(
                                            f"${total_spent:,.2f}",
                                            size=24,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.ORANGE,
                                        ),
                                    ],
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            "Remaining", size=14, color=ft.Colors.ON_SURFACE_VARIANT
                                        ),
                                        ft.Text(
                                            f"${total_planned - total_spent:,.2f}",
                                            size=24,
                                            weight=ft.FontWeight.BOLD,
                                            color=(
                                                ft.Colors.GREEN
                                                if total_spent <= total_planned
                                                else ft.Colors.RED
                                            ),
                                        ),
                                    ],
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        ),
                    ],
                ),
                padding=20,
            ),
            elevation=2,
        )

        budget_content = ft.Column(
            controls=[
                summary_card,
                ft.Container(height=16),
                ft.Card(
                    content=ft.Column(controls=budget_rows, spacing=0),
                    elevation=2,
                ),
                ft.Container(height=12),
                ft.Row(
                    controls=[
                        ft.FilledButton(
                            "Edit budget",
                            icon=ft.Icons.EDIT,
                            on_click=_open_budget_dialog,
                        ),
                        ft.TextButton(
                            "Add category",
                            icon=ft.Icons.ADD,
                            on_click=lambda _: _open_budget_dialog(),
                        ),
                    ],
                    spacing=8,
                ),
            ],
            spacing=0,
        )

    else:
        # No budget for this month
        budget_content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.ACCOUNT_BALANCE_OUTLINED,
                        size=64,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Container(height=16),
                    ft.Text(
                        "No budget set for this month",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "Create a budget to track your spending against your goals",
                        size=14,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Container(height=24),
                    ft.FilledButton(
                        "Create Budget",
                        icon=ft.Icons.ADD,
                        on_click=_open_budget_dialog,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=40,
        )

    # Build content
    content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text("Budgets", size=24, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.CHEVRON_LEFT,
                                tooltip="Previous month",
                                on_click=lambda _: _shift_month(-1),
                            ),
                            ft.Text(
                                f"{today.strftime('%B %Y')}",
                                size=18,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CHEVRON_RIGHT,
                                tooltip="Next month",
                                on_click=lambda _: _shift_month(1),
                            ),
                            ft.FilledButton(
                                "Add line",
                                icon=ft.Icons.ADD,
                                on_click=handle_add_line,
                            ),
                            ft.TextButton(
                                "Create budget", on_click=lambda _: show_create_budget_dialog()
                            ),
                            ft.TextButton(
                                "Copy previous month", on_click=lambda _: copy_previous_month()
                            ),
                        ],
                        spacing=8,
                        wrap=True,
                        run_spacing=8,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                wrap=True,
                run_spacing=8,
            ),
            ft.Container(height=16),
            budget_content,
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Build main layout
    app_bar = build_app_bar(ctx, "Budgets", page)
    main_layout = build_main_layout(ctx, page, "/budgets", content, use_menu_bar=True)

    return ft.View(
        route="/budgets",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )
