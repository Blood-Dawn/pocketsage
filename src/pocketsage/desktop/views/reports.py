"""Reports/export view implementation for Flet app."""

from __future__ import annotations

import csv
import shutil
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import flet as ft

from ...services.admin_tasks import run_export
from ...services.debts import DebtAccount, avalanche_schedule, snowball_schedule
from ...services.reports import export_spending_png, export_transactions_csv
from ..charts import (
    cashflow_by_account_png,
    category_trend_png,
    debt_payoff_chart_png,
)
from ..components import build_app_bar, build_main_layout, empty_state
from ..context import AppContext


def build_reports_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the reports/export view."""

    uid = ctx.require_user_id()

    def notify(message: str):
        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        page.update()

    def _exports_dir() -> Path:
        out = Path(ctx.config.DATA_DIR) / "exports"
        out.mkdir(parents=True, exist_ok=True)
        return out

    def export_all(_):
        try:
            path = run_export(
                _exports_dir(), session_factory=ctx.session_factory, user_id=uid
            )
            notify(f"Export ready: {path}")
        except Exception as exc:
            notify(f"Export failed: {exc}")

    def export_monthly_spending(_):
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
            output = _exports_dir() / f"spending_{month.strftime('%Y_%m')}.png"
            export_spending_png(transactions=txs, output_path=output, renderer=None)  # type: ignore[arg-type]
            notify(f"Monthly spending saved to {output}")
        except Exception as exc:
            notify(f"Spending report failed: {exc}")

    def export_ytd_summary(_):
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
            output = _exports_dir() / f"ytd_summary_{year}.csv"
            with output.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["metric", "amount"])
                writer.writerow(["income", f"{income:.2f}"])
                writer.writerow(["expenses", f"{expenses:.2f}"])
                writer.writerow(["net", f"{net:.2f}"])
            notify(f"YTD summary saved to {output}")
        except Exception as exc:
            notify(f"YTD summary failed: {exc}")

    def export_debt_report(_):
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

            output_csv = _exports_dir() / f"debt_payoff_{stamp}.csv"
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
            chart_dst = _exports_dir() / f"debt_payoff_{stamp}.png"
            shutil.copy(chart_src, chart_dst)
            notify(f"Debt payoff report saved to {output_csv}")
        except Exception as exc:
            notify(f"Debt report failed: {exc}")

    def export_category_trend(_):
        try:
            txs = ctx.transaction_repo.list_all(user_id=uid, limit=5000)
            categories = {c.id: c.name for c in ctx.category_repo.list_all(user_id=uid) if c.id}
            png = category_trend_png(txs, category_lookup=categories)
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            dest = _exports_dir() / f"category_trend_{stamp}.png"
            shutil.copy(png, dest)
            notify(f"Category trend saved to {dest}")
        except Exception as exc:
            notify(f"Category trend failed: {exc}")

    def export_cashflow_by_account(_):
        try:
            txs = ctx.transaction_repo.list_all(user_id=uid, limit=5000)
            accounts = {a.id: a.name for a in ctx.account_repo.list_all(user_id=uid) if a.id}
            png = cashflow_by_account_png(txs, account_lookup=accounts)
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            dest = _exports_dir() / f"cashflow_accounts_{stamp}.png"
            shutil.copy(png, dest)
            notify(f"Cashflow by account saved to {dest}")
        except Exception as exc:
            notify(f"Cashflow by account failed: {exc}")

    def export_combined_bundle(_):
        try:
            exports_dir = _exports_dir()
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            bundle_path = exports_dir / f"reports_bundle_{stamp}.zip"
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
                ytd_csv = tmp / "ytd_summary.csv"
                export_ytd_summary(None)
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
                on_click=export_all,
            ),
            _report_card(
                title="Monthly spending report",
                description="Current month category breakdown.",
                on_click=export_monthly_spending,
            ),
            _report_card(
                title="Year-to-date summary",
                description="Income vs expense year-to-date.",
                on_click=export_ytd_summary,
            ),
            _report_card(
                title="Debt payoff summary",
                description="Latest payoff projection as CSV + chart.",
                on_click=export_debt_report,
            ),
            _report_card(
                title="Category trend",
                description="Stacked expenses by category across recent months.",
                on_click=export_category_trend,
            ),
            _report_card(
                title="Cashflow by account",
                description="Net cashflow per account.",
                on_click=export_cashflow_by_account,
            ),
            _report_card(
                title="Combined bundle",
                description="ZIP of transactions, spending, YTD, debt, trend, cashflow.",
                on_click=export_combined_bundle,
            ),
        ],
        spacing=12,
        run_spacing=12,
    )

    content = ft.Column(
        [
            ft.Text("Reports & Exports", size=24, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Generate CSVs/ZIPs for archives or sharing.", color=ft.Colors.ON_SURFACE_VARIANT
            ),
            ft.Container(height=12),
            cards,
            ft.Container(height=16),
            empty_state("More reports coming soon."),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    app_bar = build_app_bar(ctx, "Reports", page)
    main_layout = build_main_layout(ctx, page, "/reports", content)

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
                    [
                        ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(description, color=ft.Colors.ON_SURFACE_VARIANT, size=13),
                        ft.Container(height=8),
                        ft.FilledTonalButton("Download", icon=ft.Icons.DOWNLOAD, on_click=on_click),
                    ]
                ),
            )
        ),
    )
