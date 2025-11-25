"""Budget creation and editing dialogs (FR-13).

Implements budget management with per-category budget lines:
- Create monthly budget with category allocations
- Edit existing budget amounts
- Delete budget lines
- Visual feedback for budget status
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import flet as ft

from ....logging_config import get_logger
from ....models.budget import Budget

if TYPE_CHECKING:
    from ...context import AppContext

logger = get_logger(__name__)


def show_budget_dialog(
    ctx: AppContext,
    page: ft.Page,
    target_month: date | None = None,
    on_save_callback=None,
) -> None:
    """Show budget creation/edit dialog.

    Args:
        ctx: Application context
        page: Flet page
        target_month: Month to create/edit budget for (defaults to current month)
        on_save_callback: Optional callback after successful save
    """
    uid = ctx.require_user_id()

    # Default to current month if not specified
    if target_month is None:
        target_month = date.today().replace(day=1)
    else:
        target_month = target_month.replace(day=1)  # Ensure it's first of month

    # Check if budget exists for this month
    existing_budget = ctx.budget_repo.get_for_month(
        target_month.year, target_month.month, user_id=uid
    )
    is_edit = existing_budget is not None

    # Get existing budget lines if editing
    if is_edit:
        existing_lines = ctx.budget_repo.get_lines_for_budget(
            existing_budget.id, user_id=uid
        )
    else:
        existing_lines = []

    # Get all categories for dropdown
    categories = ctx.category_repo.list_all(user_id=uid)
    expense_categories = [c for c in categories if c.category_type == "expense"]

    # Budget lines container
    budget_lines_ref = ft.Ref[ft.Column]()
    budget_lines_data: list[dict] = []

    # Pre-populate with existing lines
    for line in existing_lines:
        cat = next((c for c in expense_categories if c.id == line.category_id), None)
        if cat:
            budget_lines_data.append({
                "id": line.id,
                "category_id": line.category_id,
                "category_name": cat.name,
                "amount": line.planned_amount,
            })

    def _render_budget_lines():
        """Render the budget lines list."""
        if not budget_lines_ref.current:
            return

        if not budget_lines_data:
            budget_lines_ref.current.controls = [
                ft.Text(
                    "No budget lines yet. Click 'Add Category' to start.",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    size=12,
                    italic=True,
                )
            ]
        else:
            lines = []
            total = 0.0
            for idx, line_data in enumerate(budget_lines_data):
                amount = float(line_data["amount"])
                total += amount

                lines.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Text(
                                    line_data["category_name"],
                                    weight=ft.FontWeight.BOLD,
                                    expand=True,
                                ),
                                ft.Text(f"${amount:,.2f}"),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    icon_size=18,
                                    tooltip="Remove",
                                    on_click=lambda _, i=idx: _remove_line(i),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=8,
                        border_radius=4,
                        bgcolor=ft.Colors.SURFACE_VARIANT,
                    )
                )

            # Total row
            lines.append(ft.Divider())
            lines.append(
                ft.Row(
                    controls=[
                        ft.Text("Total Budget:", weight=ft.FontWeight.BOLD),
                        ft.Text(f"${total:,.2f}", weight=ft.FontWeight.BOLD),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

            budget_lines_ref.current.controls = lines

        budget_lines_ref.current.update()

    def _add_budget_line(_):
        """Show dialog to add a new budget line."""
        # Filter out already-budgeted categories
        budgeted_cat_ids = {line["category_id"] for line in budget_lines_data}
        expense_categories = [c for c in categories if c.category_type == "expense"]
        available_cats = [
            c for c in expense_categories if c.id not in budgeted_cat_ids
        ]

        if not available_cats:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("All expense categories already have budgets!")
            )
            page.snack_bar.open = True
            page.update()
            return

        category_dd = ft.Dropdown(
            label="Category",
            options=[
                ft.dropdown.Option(str(c.id), c.name) for c in available_cats
            ],
            value=str(available_cats[0].id) if available_cats else None,
            width=300,
        )

        amount_field = ft.TextField(
            label="Budget Amount *",
            hint_text="e.g., 500.00",
            value="",
            width=200,
        )

        def _save_line(_):
            # Validate amount
            try:
                amount = float(amount_field.value or 0)
                if amount <= 0:
                    amount_field.error_text = "Amount must be greater than 0"
                    amount_field.update()
                    return
            except ValueError:
                amount_field.error_text = "Enter a valid number"
                amount_field.update()
                return

            # Get category
            cat_id = int(category_dd.value)
            cat = next((c for c in available_cats if c.id == cat_id), None)

            # Add to list
            budget_lines_data.append({
                "id": None,  # Will be created on save
                "category_id": cat_id,
                "category_name": cat.name,
                "amount": amount,
            })

            # Close add dialog and refresh
            add_dialog.open = False
            page.dialog = None
            _render_budget_lines()
            page.update()

        def _cancel_add(_):
            add_dialog.open = False
            page.dialog = None
            page.update()

        add_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add Budget Line"),
            content=ft.Column(
                controls=[category_dd, amount_field],
                tight=True,
                spacing=12,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel_add),
                ft.FilledButton("Add", on_click=_save_line),
            ],
        )

        page.dialog = add_dialog
        add_dialog.open = True
        page.update()

    def _remove_line(index: int):
        """Remove a budget line."""
        budget_lines_data.pop(index)
        _render_budget_lines()

    def _save_budget(_):
        """Save the budget and all lines."""
        if not budget_lines_data:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Add at least one category to create a budget"),
                bgcolor=ft.Colors.WARNING,
            )
            page.snack_bar.open = True
            page.update()
            return

        try:
            # Create or update budget
            if is_edit:
                budget = existing_budget
                # Delete all existing lines first
                for line in existing_lines:
                    ctx.budget_repo.delete_line(line.id, user_id=uid)
            else:
                # Create new budget
                budget = Budget(
                    year=target_month.year,
                    month=target_month.month,
                    user_id=uid,
                )
                budget = ctx.budget_repo.create(budget, user_id=uid)

            # Create all budget lines
            for line_data in budget_lines_data:
                ctx.budget_repo.add_line(
                    budget.id,
                    line_data["category_id"],
                    line_data["amount"],
                    user_id=uid,
                )

            logger.info(
                f"Budget saved for {target_month.strftime('%B %Y')}: "
                f"{len(budget_lines_data)} categories"
            )

            # Close dialog
            dialog.open = False
            page.dialog = None
            page.update()

            # Show success
            page.snack_bar = ft.SnackBar(
                content=ft.Text(
                    f"Budget for {target_month.strftime('%B %Y')} saved"
                )
            )
            page.snack_bar.open = True
            page.update()

            # Callback
            if on_save_callback:
                on_save_callback()

        except Exception as exc:
            logger.error(f"Failed to save budget: {exc}", exc_info=True)
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Failed to save budget: {exc}"),
                bgcolor=ft.Colors.ERROR,
            )
            page.snack_bar.open = True
            page.update()

    def _close_dialog(_):
        """Close without saving."""
        dialog.open = False
        page.dialog = None
        page.update()

    # Build dialog
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(
            f"Budget for {target_month.strftime('%B %Y')}"
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Set spending limits for each category to stay on track.",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Divider(),
                    ft.Row(
                        controls=[
                            ft.Text("Budget Categories:", weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.FilledButton(
                                "Add Category",
                                icon=ft.Icons.ADD,
                                on_click=_add_budget_line,
                            ),
                        ],
                    ),
                    ft.Column(
                        ref=budget_lines_ref,
                        controls=[],
                        spacing=8,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                ],
                spacing=12,
            ),
            width=500,
            height=400,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=_close_dialog),
            ft.FilledButton("Save Budget", on_click=_save_budget),
        ],
    )

    page.dialog = dialog
    dialog.open = True
    page.update()

    # Initial render
    _render_budget_lines()
