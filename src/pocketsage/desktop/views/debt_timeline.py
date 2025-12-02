"""Semiannual payoff timeline view."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import flet as ft

from ...devtools import dev_log
from .. import controllers
from ..components import build_app_bar, build_main_layout
from .debts import PAYMENT_MODE_SURPLUS, project_payoff_schedule

if TYPE_CHECKING:
    from ..context import AppContext


def _format_month(value: str) -> str:
    """Return a friendly month label from an ISO date string."""
    try:
        return date.fromisoformat(value).strftime("%b %Y")
    except Exception:
        return value


def build_debt_timeline_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Show payoff checkpoints every six months until debt free."""

    uid = ctx.require_user_id()
    prefs = getattr(ctx, "payoff_preferences", {}) or {}
    state = {
        "strategy": prefs.get("strategy", "snowball"),
        "mode": prefs.get("mode", "balanced"),
    }

    timeline_ref = ft.Ref[ft.Column]()
    payoff_ref = ft.Ref[ft.Text]()
    months_ref = ft.Ref[ft.Text]()
    interest_ref = ft.Ref[ft.Text]()

    def _set_summary(payoff: str | None, total_interest: float, months: int) -> None:
        if payoff_ref.current:
            payoff_ref.current.value = payoff or "N/A"
        if months_ref.current:
            months_ref.current.value = f"{months} months"
        if interest_ref.current:
            interest_ref.current.value = f"${total_interest:,.2f}"

    def _build_rows(schedule: list[dict]) -> list[ft.Control]:
        if not schedule:
            return [
                ft.Text(
                    "Add a liability to see the semiannual payoff timeline.",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                )
            ]
        indices = list(range(0, len(schedule), 6))
        if len(schedule) - 1 not in indices:
            indices.append(len(schedule) - 1)
        rows: list[ft.Control] = []
        for idx in indices:
            entry = schedule[idx] if idx < len(schedule) else schedule[-1]
            payments = entry.get("payments", {}) if isinstance(entry, dict) else {}
            payment_total = sum(float(p.get("payment_amount", 0.0) or 0.0) for p in payments.values())
            remaining_total = sum(float(p.get("remaining_balance", 0.0) or 0.0) for p in payments.values())
            interest_total = sum(float(p.get("interest_paid", 0.0) or 0.0) for p in payments.values())
            month_label = _format_month(str(entry.get("date", "")))
            rows.append(
                ft.Card(
                    content=ft.Container(
                        padding=12,
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(f"Month {idx + 1}", weight=ft.FontWeight.BOLD),
                                        ft.Text(month_label, color=ft.Colors.ON_SURFACE_VARIANT),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    wrap=True,
                                ),
                                ft.Row(
                                    [
                                        ft.Text(f"Payment: ${payment_total:,.2f}"),
                                        ft.Text(f"Interest: ${interest_total:,.2f}"),
                                        ft.Text(f"Remaining: ${remaining_total:,.2f}", weight=ft.FontWeight.BOLD),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    wrap=True,
                                ),
                            ],
                            spacing=6,
                        ),
                    )
                )
            )
        return rows

    def _refresh() -> None:
        liabilities = ctx.liability_repo.list_all(user_id=uid)
        try:
            schedule, payoff, total_interest, months = project_payoff_schedule(
                liabilities, strategy=state["strategy"], mode=state["mode"]
            )
            ctx.payoff_preferences = {"strategy": state["strategy"], "mode": state["mode"]}
            _set_summary(payoff, total_interest, months)
            if timeline_ref.current:
                timeline_ref.current.controls = _build_rows(schedule)
            page.update()
        except Exception as exc:
            dev_log(ctx.config, "Timeline render failed", exc=exc)
            if timeline_ref.current:
                timeline_ref.current.controls = [ft.Text(f"Unable to generate timeline: {exc}")]
            page.update()

    header = ft.Row(
        [
            ft.Text("Payoff timeline", size=24, weight=ft.FontWeight.BOLD),
            ft.TextButton(
                "Back to debts",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: controllers.navigate(page, "/debts"),
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        wrap=True,
    )

    summary_cards = ft.Row(
        [
            ft.Card(
                content=ft.Container(
                    padding=12,
                    content=ft.Column(
                        [ft.Text("Debt-free date", color=ft.Colors.ON_SURFACE_VARIANT), ft.Text("", ref=payoff_ref)],
                        spacing=6,
                    ),
                ),
                expand=True,
            ),
            ft.Card(
                content=ft.Container(
                    padding=12,
                    content=ft.Column(
                        [ft.Text("Months remaining", color=ft.Colors.ON_SURFACE_VARIANT), ft.Text("", ref=months_ref)],
                        spacing=6,
                    ),
                ),
                expand=True,
            ),
            ft.Card(
                content=ft.Container(
                    padding=12,
                    content=ft.Column(
                        [ft.Text("Projected interest", color=ft.Colors.ON_SURFACE_VARIANT), ft.Text("", ref=interest_ref)],
                        spacing=6,
                    ),
                ),
                expand=True,
            ),
        ],
        spacing=12,
    )

    strategy_selector = ft.RadioGroup(
        value=state["strategy"],
        on_change=lambda e: (state.update({"strategy": e.control.value or "snowball"}), _refresh()),
        content=ft.Row(
            controls=[
                ft.Radio(value="snowball", label="Snowball"),
                ft.Radio(value="avalanche", label="Avalanche"),
            ]
        ),
    )

    mode_selector = ft.Dropdown(
        width=220,
        value=state["mode"],
        options=[
            ft.dropdown.Option("aggressive", f"Aggressive (+${PAYMENT_MODE_SURPLUS['aggressive']:.0f}/mo)"),
            ft.dropdown.Option("balanced", f"Balanced (+${PAYMENT_MODE_SURPLUS['balanced']:.0f}/mo)"),
            ft.dropdown.Option("lazy", "Lazy (minimums only)"),
        ],
        on_change=lambda e: (state.update({"mode": e.control.value or "balanced"}), _refresh()),
    )

    controls_row = ft.Row(
        [
            ft.Column([ft.Text("Strategy"), strategy_selector], spacing=6),
            ft.Column([ft.Text("Payment mode"), mode_selector], spacing=6),
            ft.Text(
                "Timeline shows every 6th month plus the final payoff checkpoint.",
                color=ft.Colors.ON_SURFACE_VARIANT,
                width=260,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.START,
        wrap=True,
        spacing=16,
    )

    timeline_card = ft.Card(
        content=ft.Container(
            padding=12,
            content=ft.Column(
                [
                    ft.Text("Semiannual payoff checkpoints", weight=ft.FontWeight.BOLD),
                    ft.Column(ref=timeline_ref, spacing=8),
                ],
                spacing=10,
            ),
        )
    )

    content = ft.Column(
        controls=[
            header,
            ft.Text(
                "Review your payoff plan every six months and the final payoff month using your selected strategy.",
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            summary_cards,
            controls_row,
            timeline_card,
        ],
        spacing=16,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    app_bar = build_app_bar(ctx, "Payoff timeline", page)
    main_layout = build_main_layout(ctx, page, "/debts", content, use_menu_bar=True)

    _refresh()

    return ft.View(
        route="/debts/timeline",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )
