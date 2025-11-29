"""Reports/export view implementation for Flet app."""
# TODO(@pocketsage-reports): Centralize report generation to a service layer and keep views thin.

from __future__ import annotations

import csv
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import flet as ft

from ...services.admin_tasks import run_export
from ...services.debts import DebtAccount, avalanche_schedule, snowball_schedule
from ...services.reports import export_spending_png, export_transactions_csv
from .. import controllers
from ..charts import (
    allocation_chart_png,
    cashflow_by_account_png,
    category_trend_png,
    debt_payoff_chart_png,
    spending_chart_png,
)
from ..components import build_app_bar, build_main_layout, empty_state
from ..context import AppContext


def build_reports_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the reports/export view."""

    uid = ctx.require_user_id()

    # FilePicker for export destination
    export_dir_picker = ft.FilePicker()
    if page.overlay is None:
        page.overlay = [export_dir_picker]
    else:
        page.overlay.append(export_dir_picker)

    def notify(message: str):
        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        page.update()

    # Build aggregated charts for quick viewing
    def _build_charts() -> ft.ResponsiveRow:
        month = ctx.current_month
        start = datetime(month.year, month.month, 1)
        if month.month == 12:
            end = datetime(month.year + 1, 1, 1)
        else:
            end = datetime(month.year, month.month + 1, 1)
        txs_month = ctx.transaction_repo.search(
            start_date=start, end_date=end, user_id=uid, category_id=None, account_id=None, text=None  # type: ignore[arg-type]
        )
        categories = {c.id: c.name for c in ctx.category_repo.list_all(user_id=uid) if c.id}

        spending_png = spending_chart_png(txs_month, category_lookup=categories)

        # Budget usage progress snapshot
        budget = ctx.budget_repo.get_for_month(month.year, month.month, user_id=uid)
        budget_rows: list[ft.Control] = []
        if budget:
            lines = ctx.budget_repo.get_lines_for_budget(budget.id, user_id=uid)
            for line in lines:
                cat_name = categories.get(line.category_id, "Category")
                actual = sum(
                    abs(t.amount)
                    for t in ctx.transaction_repo.search(
                        start_date=start, end_date=end, category_id=line.category_id, user_id=uid
                    )
                    if t.amount < 0
                )
                pct = 0 if line.planned_amount == 0 else min((actual / line.planned_amount) * 100, 999)
                budget_rows.append(
                    ft.Row(
                        controls=[
                            ft.Text(cat_name, width=140),
                            ft.ProgressBar(
                                value=min(actual / (line.planned_amount or 1), 1.0),
                                color=ft.Colors.PRIMARY if actual <= line.planned_amount else ft.Colors.ERROR,
                                expand=True,
                            ),
                            ft.Text(f"{pct:.0f}%", width=50),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                )
        else:
            budget_rows.append(
                ft.Text("No budget for this month", color=ft.Colors.ON_SURFACE_VARIANT)
            )

        # Habits completion snapshot (last 7 days)
        habits = ctx.habit_repo.list_active(user_id=uid)
        today = datetime.today().date()
        habit_rows: list[ft.Control] = []
        for habit in habits:
            entries = ctx.habit_repo.get_entries_for_habit(
                habit.id, today - timedelta(days=6), today, user_id=uid
            )
            completed = sum(1 for e in entries if e.value > 0)
            pct = (completed / 7) * 100
            habit_rows.append(
                ft.Row(
                    controls=[
                        ft.Text(habit.name, width=140),
                        ft.ProgressBar(
                            value=completed / 7,
                            color=ft.Colors.GREEN if completed >= 5 else ft.Colors.AMBER,
                            expand=True,
                        ),
                        ft.Text(f"{pct:.0f}%", width=50),
                    ],
                    spacing=8,
                )
            )
        if not habit_rows:
            habit_rows.append(ft.Text("No habits yet", color=ft.Colors.ON_SURFACE_VARIANT))

        # Debt payoff chart snapshot
        liabilities = ctx.liability_repo.list_all(user_id=uid)
        debts = [
            DebtAccount(
                id=lb.id or 0,
                balance=lb.balance,
                apr=lb.apr,
                minimum_payment=lb.minimum_payment,
                statement_due_day=getattr(lb, "due_day", 1) or 1,
            )
            for lb in liabilities
        ]
        payoff_png = debt_payoff_chart_png(snowball_schedule(debts=debts, surplus=0.0)) if debts else None

        # Portfolio allocation snapshot
        holdings = ctx.holding_repo.list_all(user_id=uid) if hasattr(ctx, "holding_repo") else []
        allocation_png = allocation_chart_png(holdings) if holdings else None

        return ft.ResponsiveRow(
            controls=[
                _chart_card("Spending by category", spending_png, page=page, drill_route="/ledger"),
                _chart_card(
                    "Budget usage",
                    None,
                    ft.Column(controls=budget_rows, spacing=6),
                    page=page,
                    drill_route="/budgets",
                ),
                _chart_card(
                    "Habit completion (7d)",
                    None,
                    ft.Column(controls=habit_rows, spacing=6),
                    page=page,
                    drill_route="/habits",
                ),
                _chart_card("Debt payoff projection", payoff_png, page=page, drill_route="/debts"),
                _chart_card("Portfolio allocation", allocation_png, page=page, drill_route="/portfolio"),
            ],
            spacing=12,
            run_spacing=12,
        )

    # On-demand report generator
    report_type_dd = ft.Dropdown(
        label="Report type",
        options=[
            ft.dropdown.Option("spending", "Spending (this month)"),
            ft.dropdown.Option("ytd", "YTD summary"),
            ft.dropdown.Option("debt", "Debt payoff"),
            ft.dropdown.Option("portfolio", "Portfolio allocation"),
        ],
        value="spending",
        width=240,
    )
    result_text = ft.Ref[ft.Text]()
    result_image = ft.Ref[ft.Image]()

    def _generate_report(_=None):
        rtype = report_type_dd.value or "spending"
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        try:
            if rtype == "spending":
                month = ctx.current_month
                start = datetime(month.year, month.month, 1)
                end = datetime(month.year + (1 if month.month == 12 else 0), (month.month % 12) + 1, 1)
                txs = ctx.transaction_repo.search(
                    start_date=start, end_date=end, user_id=uid, category_id=None, account_id=None, text=None  # type: ignore[arg-type]
                )
                out = _exports_dir() / f"spending_{stamp}.png"
                export_spending_png(transactions=txs, output_path=out)
                if result_image.current:
                    result_image.current.src = str(out)
                    result_image.current.visible = True
                if result_text.current:
                    result_text.current.value = f"Spending chart saved to {out}"
            elif rtype == "ytd":
                year = ctx.current_month.year
                start = datetime(year, 1, 1)
                end = datetime(year + 1, 1, 1)
                txs = ctx.transaction_repo.search(
                    start_date=start, end_date=end, user_id=uid, category_id=None, account_id=None, text=None  # type: ignore[arg-type]
                )
                income = sum(t.amount for t in txs if t.amount > 0)
                expenses = sum(abs(t.amount) for t in txs if t.amount < 0)
                net = income - expenses
                out = _exports_dir() / f"ytd_{year}_{stamp}.csv"
                with out.open("w", newline="") as fh:
                    writer = csv.writer(fh)
                    writer.writerow(["metric", "amount"])
                    writer.writerow(["income", f"{income:.2f}"])
                    writer.writerow(["expenses", f"{expenses:.2f}"])
                    writer.writerow(["net", f"{net:.2f}"])
                if result_image.current:
                    result_image.current.visible = False
                if result_text.current:
                    result_text.current.value = f"YTD summary saved to {out}"
            elif rtype == "debt":
                liabilities = ctx.liability_repo.list_all(user_id=uid)
                debts = [
                    DebtAccount(
                        id=lb.id or 0,
                        balance=lb.balance,
                        apr=lb.apr,
                        minimum_payment=lb.minimum_payment,
                        statement_due_day=getattr(lb, "due_day", 1) or 1,
                    )
                    for lb in liabilities
                ]
                if not debts:
                    notify("No debts to report on.")
                    return
                schedule = snowball_schedule(debts=debts, surplus=0.0)
                out = _exports_dir() / f"debt_{stamp}.png"
                chart_path = debt_payoff_chart_png(schedule, output_path=out)
                if result_image.current:
                    result_image.current.src = str(chart_path)
                    result_image.current.visible = True
                if result_text.current:
                    result_text.current.value = f"Debt payoff chart saved to {chart_path}"
            elif rtype == "portfolio":
                holdings = ctx.holding_repo.list_all(user_id=uid) if hasattr(ctx, "holding_repo") else []
                if not holdings:
                    notify("No holdings to export.")
                    return
                out = _exports_dir() / f"allocation_{stamp}.png"
                chart = allocation_chart_png(holdings, output_path=out) if "output_path" in allocation_chart_png.__code__.co_varnames else allocation_chart_png(holdings)
                chart_path = out if out.exists() else chart
                if result_image.current:
                    result_image.current.src = str(chart_path)
                    result_image.current.visible = True
                if result_text.current:
                    result_text.current.value = f"Allocation chart saved to {chart_path}"
        except Exception as exc:
            notify(f"Report generation failed: {exc}")

    def _exports_dir() -> Path:
        out = Path(ctx.config.DATA_DIR) / "exports"
        out.mkdir(parents=True, exist_ok=True)
        return out

    def _pick_export_dir(callback):
        """Show directory picker and call callback with selected path."""
        def on_result(e: ft.FilePickerResultEvent):
            if e.path:
                callback(Path(e.path))
            else:
                # User cancelled, use default
                callback(_exports_dir())

        export_dir_picker.get_directory_path(
            dialog_title="Select Export Destination",
        )
        export_dir_picker.on_result = on_result

    def export_all_to(custom_path: Path | None = None):
        def _do_export(export_dir: Path):
            try:
                target_dir = export_dir
                path = run_export(
                    output_dir=str(target_dir),
                    session_factory=ctx.session_factory,
                    user_id=uid,
                    retention=ctx.config.EXPORT_RETENTION,
                )
                notify(f"Export ready: {path}")
            except Exception as exc:
                notify(f"Export failed: {exc}")

        if custom_path:
            _do_export(custom_path)
        else:
            _pick_export_dir(_do_export)

    def export_monthly_spending(custom_path: Path | None = None):
        try:
            month = ctx.current_month
            start = datetime(month.year, month.month, 1)
            if month.month == 12:
                end = datetime(month.year + 1, 1, 1)
            else:
                end = datetime(month.year, month.month + 1, 1)
            txs = ctx.transaction_repo.search(
                start_date=start, end_date=end, user_id=uid, category_id=None, account_id=None, text=None  # type: ignore[arg-type]
            )
            output = (
                custom_path
                if custom_path is not None
                else _exports_dir() / f"spending_{month.strftime('%Y_%m')}.png"
            )
            export_spending_png(transactions=txs, output_path=output, renderer=None)  # type: ignore[arg-type]
            notify(f"Monthly spending saved to {output}")
        except Exception as exc:
            notify(f"Spending report failed: {exc}")

    def export_ytd_summary(custom_path: Path | None = None):
        try:
            year = ctx.current_month.year
            start = datetime(year, 1, 1)
            end = datetime(year + 1, 1, 1)
            txs = ctx.transaction_repo.search(
                start_date=start, end_date=end, user_id=uid, category_id=None, account_id=None, text=None  # type: ignore[arg-type]
            )
            income = sum(t.amount for t in txs if t.amount > 0)
            expenses = sum(abs(t.amount) for t in txs if t.amount < 0)
            net = income - expenses
            output = (
                custom_path
                if custom_path is not None
                else _exports_dir() / f"ytd_summary_{year}.csv"
            )
            with output.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["metric", "amount"])
                writer.writerow(["income", f"{income:.2f}"])
                writer.writerow(["expenses", f"{expenses:.2f}"])
                writer.writerow(["net", f"{net:.2f}"])
            notify(f"YTD summary saved to {output}")
        except Exception as exc:
            notify(f"YTD summary failed: {exc}")

    def export_debt_report(custom_csv: Path | None = None, custom_chart: Path | None = None):
        try:
            liabilities = ctx.liability_repo.list_all(user_id=uid)
            if not liabilities:
                notify("No liabilities to report on.")
                return
            debts = [
                DebtAccount(
                    id=lb.id or 0,
                    balance=lb.balance,
                    apr=lb.apr,
                    minimum_payment=lb.minimum_payment,
                    statement_due_day=getattr(lb, "due_day", 1) or 1,
                )
                for lb in liabilities
            ]
            # Default to snowball but surface avalanche as well for comparison.
            schedule = snowball_schedule(debts=debts, surplus=0.0)
            alt_schedule = avalanche_schedule(debts=debts, surplus=0.0)
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")

            output_csv = (
                custom_csv
                if custom_csv is not None
                else _exports_dir() / f"debt_payoff_{stamp}.csv"
            )
            with output_csv.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["date", "strategy", "total_payment", "remaining_balance"])
                for label, sched in (("snowball", schedule), ("avalanche", alt_schedule)):
                    for entry in sched:
                        payments = entry.get("payments", {}) if isinstance(entry, dict) else {}
                        total_payment = sum(
                            float(p.get("payment_amount", 0.0) or 0.0) for p in payments.values()
                        )
                        remaining = sum(
                            float(p.get("remaining_balance", 0.0) or 0.0) for p in payments.values()
                        )
                        writer.writerow([entry.get("date", ""), label, f"{total_payment:.2f}", f"{remaining:.2f}"])

            chart_src = debt_payoff_chart_png(schedule)
            chart_dst = (
                custom_chart
                if custom_chart is not None
                else _exports_dir() / f"debt_payoff_{stamp}.png"
            )
            shutil.copy(chart_src, chart_dst)
            notify(f"Debt payoff report saved to {output_csv}")
        except Exception as exc:
            notify(f"Debt report failed: {exc}")

    def export_category_trend(custom_path: Path | None = None):
        try:
            txs = ctx.transaction_repo.list_all(user_id=uid, limit=5000)
            categories = {c.id: c.name for c in ctx.category_repo.list_all(user_id=uid) if c.id}
            png = category_trend_png(txs, category_lookup=categories)
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            dest = custom_path if custom_path is not None else _exports_dir() / f"category_trend_{stamp}.png"
            shutil.copy(png, dest)
            notify(f"Category trend saved to {dest}")
        except Exception as exc:
            notify(f"Category trend failed: {exc}")

    def export_cashflow_by_account(custom_path: Path | None = None):
        try:
            txs = ctx.transaction_repo.list_all(user_id=uid, limit=5000)
            accounts = {a.id: a.name for a in ctx.account_repo.list_all(user_id=uid) if a.id}
            png = cashflow_by_account_png(txs, account_lookup=accounts)
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            dest = custom_path if custom_path is not None else _exports_dir() / f"cashflow_accounts_{stamp}.png"
            shutil.copy(png, dest)
            notify(f"Cashflow by account saved to {dest}")
        except Exception as exc:
            notify(f"Cashflow by account failed: {exc}")

    def export_portfolio_allocation(custom_path: Path | None = None):
        try:
            holdings = ctx.holding_repo.list_all(user_id=uid) if hasattr(ctx, "holding_repo") else []
            if not holdings:
                notify("No holdings to export.")
                return
            png = allocation_chart_png(holdings)
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            dest = custom_path if custom_path is not None else _exports_dir() / f"allocation_{stamp}.png"
            shutil.copy(png, dest)
            notify(f"Portfolio allocation saved to {dest}")
        except Exception as exc:
            notify(f"Portfolio allocation failed: {exc}")

    def export_combined_bundle(custom_path: Path | None = None):
        try:
            exports_dir = _exports_dir() if custom_path is None else custom_path.parent
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            bundle_path = (
                custom_path if custom_path is not None else exports_dir / f"reports_bundle_{stamp}.zip"
            )
            with TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                # Transactions CSV
                txs = ctx.transaction_repo.list_all(user_id=uid, limit=10000)
                tx_csv = tmp / "transactions.csv"
                export_transactions_csv(transactions=txs, output_path=tx_csv)
                # Spending PNG
                spending_png = tmp / "spending.png"
                export_spending_png(transactions=txs, output_path=spending_png, renderer=None)  # type: ignore[arg-type]
                # YTD CSV
                export_ytd_summary(tmp / "ytd_summary.csv")
                # Debt report
                liabilities = ctx.liability_repo.list_all(user_id=uid)
                debts = [
                    DebtAccount(
                        id=lb.id or 0,
                        balance=lb.balance,
                        apr=lb.apr,
                        minimum_payment=lb.minimum_payment,
                        statement_due_day=getattr(lb, "due_day", 1) or 1,
                    )
                    for lb in liabilities
                ]
                debt_csv = tmp / "debt_payoff.csv"
                chart_png = tmp / "debt_payoff.png"
                if debts:
                    schedule = snowball_schedule(debts=debts, surplus=0.0)
                    with debt_csv.open("w", newline="") as handle:
                        writer = csv.writer(handle)
                        writer.writerow(["date", "total_payment", "remaining_balance"])
                        for entry in schedule:
                            payments = entry.get("payments", {}) if isinstance(entry, dict) else {}
                            total_payment = sum(
                                float(p.get("payment_amount", 0.0) or 0.0) for p in payments.values()
                            )
                            remaining = sum(
                                float(p.get("remaining_balance", 0.0) or 0.0) for p in payments.values()
                            )
                            writer.writerow([entry.get("date", ""), f"{total_payment:.2f}", f"{remaining:.2f}"])
                    shutil.copy(debt_payoff_chart_png(schedule), chart_png)
                # Category trend
                trend_png = category_trend_png(txs, category_lookup={c.id: c.name for c in ctx.category_repo.list_all(user_id=uid) if c.id})
                trend_copy = tmp / "category_trend.png"
                shutil.copy(trend_png, trend_copy)
                # Cashflow by account
                cf_png = cashflow_by_account_png(txs, account_lookup={a.id: a.name for a in ctx.account_repo.list_all(user_id=uid) if a.id})
                cf_copy = tmp / "cashflow_by_account.png"
                shutil.copy(cf_png, cf_copy)

                # Build bundle
                with ZipFile(bundle_path, "w") as zipf:
                    for file in tmp.iterdir():
                        zipf.write(file, arcname=file.name)
            notify(f"Reports bundle saved to {bundle_path}")
        except Exception as exc:
            notify(f"Bundle export failed: {exc}")

    cards = ft.ResponsiveRow(
        controls=[
            _report_card(
                title="Full data export",
                description="Generate ZIP with CSVs and charts.",
                on_click=lambda _: controllers.pick_export_destination(
                    ctx,
                    page,
                    suggested_name="full_export.zip",
                    on_path_selected=lambda p: export_all_to(p),
                ),
            ),
            _report_card(
                title="Monthly spending report",
                description="Current month category breakdown.",
                on_click=lambda _: controllers.pick_export_destination(
                    ctx,
                    page,
                    suggested_name="spending.png",
                    on_path_selected=lambda p: export_monthly_spending(p),
                ),
            ),
            _report_card(
                title="Year-to-date summary",
                description="Income vs expense year-to-date.",
                on_click=lambda _: controllers.pick_export_destination(
                    ctx,
                    page,
                    suggested_name="ytd_summary.csv",
                    on_path_selected=lambda p: export_ytd_summary(p),
                ),
            ),
            _report_card(
                title="Debt payoff summary",
                description="Latest payoff projection as CSV + chart.",
                on_click=lambda _: controllers.pick_export_destination(
                    ctx,
                    page,
                    suggested_name="debt_payoff.csv",
                    on_path_selected=lambda p: export_debt_report(p, p.with_suffix(".png")),
                ),
            ),
            _report_card(
                title="Category trend",
                description="Stacked expenses by category across recent months.",
                on_click=lambda _: controllers.pick_export_destination(
                    ctx,
                    page,
                    suggested_name="category_trend.png",
                    on_path_selected=lambda p: export_category_trend(p),
                ),
            ),
            _report_card(
                title="Cashflow by account",
                description="Net cashflow per account.",
                on_click=lambda _: controllers.pick_export_destination(
                    ctx,
                    page,
                    suggested_name="cashflow_by_account.png",
                    on_path_selected=lambda p: export_cashflow_by_account(p),
                ),
            ),
            _report_card(
                title="Portfolio allocation",
                description="Holdings split by symbol/account.",
                on_click=lambda _: controllers.pick_export_destination(
                    ctx,
                    page,
                    suggested_name="allocation.png",
                    on_path_selected=lambda p: export_portfolio_allocation(p),
                ),
            ),
            _report_card(
                title="Combined bundle",
                description="ZIP of transactions, spending, YTD, debt, trend, cashflow.",
                on_click=lambda _: controllers.pick_export_destination(
                    ctx,
                    page,
                    suggested_name="reports_bundle.zip",
                    on_path_selected=lambda p: export_combined_bundle(p),
                ),
            ),
        ],
        spacing=12,
        run_spacing=12,
    )

    generator_card = ft.Card(
        content=ft.Container(
            padding=12,
            content=ft.Column(
                controls=[
                    ft.Text("On-demand report", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        controls=[
                            report_type_dd,
                            ft.FilledButton("Generate", icon=ft.Icons.PLAY_ARROW, on_click=_generate_report),
                        ],
                        spacing=8,
                        wrap=True,
                    ),
                    ft.Text("", ref=result_text, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Image(ref=result_image, height=220, visible=False),
                ],
                spacing=8,
            ),
        )
    )

    content = ft.Column(
        controls=[
            ft.Text("Reports & Exports", size=24, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Generate CSVs/ZIPs for archives or sharing.", color=ft.Colors.ON_SURFACE_VARIANT
            ),
            ft.Container(height=12),
            _build_charts(),
            ft.Container(height=16),
            cards,
            ft.Container(height=16),
            generator_card,
            ft.Container(height=16),
            empty_state("More reports coming soon."),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    app_bar = build_app_bar(ctx, "Reports", page)
    main_layout = build_main_layout(ctx, page, "/reports", content, use_menu_bar=True)

    return ft.View(
        route="/reports",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )


def _report_card(title: str, description: str, on_click):
    return ft.Container(
        col={"sm": 6, "md": 3},
        content=ft.Card(
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(description, color=ft.Colors.ON_SURFACE_VARIANT, size=13),
                        ft.Container(height=8),
                        ft.FilledTonalButton("Download", icon=ft.Icons.DOWNLOAD, on_click=on_click),
                    ]
                ),
            )
        ),
    )


def _open_chart_dialog(
    page: ft.Page,
    title: str,
    image_path: Path | str | None,
    content: ft.Control | None,
    drill_route: str | None,
):
    """Show an expanded chart with optional drill-down navigation."""
    if image_path:
        dialog_body: ft.Control = ft.Image(src=str(image_path), height=420, fit=ft.ImageFit.CONTAIN)
    elif content is not None:
        dialog_body = content
    else:
        dialog_body = ft.Text("No data available", color=ft.Colors.ON_SURFACE_VARIANT)

    def close_dialog(_: ft.ControlEvent | None = None):
        if page.dialog:
            page.dialog.open = False
        page.update()

    def view_details(_: ft.ControlEvent | None = None):
        close_dialog()
        if drill_route:
            page.go(drill_route)

    actions: list[ft.Control] = [ft.TextButton("Close", on_click=close_dialog)]
    if drill_route:
        actions.insert(0, ft.TextButton("View details", on_click=view_details))

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, weight=ft.FontWeight.BOLD),
        content=ft.Container(padding=12, content=dialog_body),
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.dialog = dialog
    dialog.open = True
    page.update()


def _chart_card(
    title: str,
    image_path: Path | str | None,
    content: ft.Control | None = None,
    page: ft.Page | None = None,
    drill_route: str | None = None,
):
    body: ft.Control
    if image_path:
        body = ft.Image(src=str(image_path), height=200, fit=ft.ImageFit.CONTAIN)
    elif content is not None:
        body = content
    else:
        body = ft.Text("No data", color=ft.Colors.ON_SURFACE_VARIANT)

    on_click = (
        (lambda _: _open_chart_dialog(page, title, image_path, content, drill_route))
        if page is not None and (image_path or content is not None)
        else None
    )

    return ft.Container(
        col={"sm": 12, "md": 6},
        on_click=on_click,
        content=ft.Card(
            content=ft.Container(
                padding=12,
                content=ft.Column(
                    controls=[
                        ft.Text(title, weight=ft.FontWeight.BOLD),
                        body,
                    ],
                    spacing=8,
                ),
            )
        ),
    )
