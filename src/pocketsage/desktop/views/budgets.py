"""Budgets view implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ..components import build_app_bar, build_main_layout, build_progress_bar

if TYPE_CHECKING:
    from ..context import AppContext


def build_budgets_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the budgets view."""

    # Get current month's budget
    today = ctx.current_month
    budget = ctx.budget_repo.get_for_month(today.year, today.month)

    if budget:
        # Get budget lines
        lines = ctx.budget_repo.get_lines_for_budget(budget.id)

        # Build budget progress bars
        budget_rows = []
        total_planned = 0
        total_spent = 0

        for line in lines:
            category = ctx.category_repo.get_by_id(line.category_id)
            if not category:
                continue

            # Get actual spending for this category this month
            transactions = ctx.transaction_repo.search(
                start_date=budget.period_start,
                end_date=budget.period_end,
                category_id=line.category_id,
            )

            actual = sum(abs(t.amount) for t in transactions if t.amount < 0)

            total_planned += line.planned_amount
            total_spent += actual

            progress = build_progress_bar(
                current=actual,
                maximum=line.planned_amount,
                label=category.name,
            )

            budget_rows.append(
                ft.Container(
                    content=progress,
                    padding=16,
                    border=ft.border.only(
                        bottom=ft.border.BorderSide(1, ft.colors.OUTLINE_VARIANT)
                    ),
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
                            [
                                ft.Column(
                                    [
                                        ft.Text(
                                            "Total Budgeted",
                                            size=14,
                                            color=ft.colors.ON_SURFACE_VARIANT,
                                        ),
                                        ft.Text(
                                            f"${total_planned:,.2f}",
                                            size=24,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                    ],
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            "Total Spent",
                                            size=14,
                                            color=ft.colors.ON_SURFACE_VARIANT,
                                        ),
                                        ft.Text(
                                            f"${total_spent:,.2f}",
                                            size=24,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.colors.ORANGE,
                                        ),
                                    ],
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            "Remaining", size=14, color=ft.colors.ON_SURFACE_VARIANT
                                        ),
                                        ft.Text(
                                            f"${total_planned - total_spent:,.2f}",
                                            size=24,
                                            weight=ft.FontWeight.BOLD,
                                            color=(
                                                ft.colors.GREEN
                                                if total_spent <= total_planned
                                                else ft.colors.RED
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
            [
                summary_card,
                ft.Container(height=16),
                ft.Card(
                    content=ft.Column(budget_rows, spacing=0),
                    elevation=2,
                ),
            ],
            spacing=0,
        )

    else:
        # No budget for this month
        budget_content = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        ft.icons.ACCOUNT_BALANCE_OUTLINED,
                        size=64,
                        color=ft.colors.ON_SURFACE_VARIANT,
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
                        color=ft.colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Container(height=24),
                    ft.FilledButton(
                        "Create Budget",
                        icon=ft.icons.ADD,
                        on_click=lambda _: None,  # TODO: Implement budget creation
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=40,
        )

    # Build content
    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text("Budgets", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        f"{today.strftime('%B %Y')}",
                        size=18,
                        color=ft.colors.ON_SURFACE_VARIANT,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(height=16),
            budget_content,
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Build main layout
    app_bar = build_app_bar(ctx, "Budgets")
    main_layout = build_main_layout(page, "/budgets", content)

    return ft.View(
        route="/budgets",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )
