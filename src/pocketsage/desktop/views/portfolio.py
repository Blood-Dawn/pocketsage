"""Portfolio view implementation."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from ...models.portfolio import Holding
from .. import controllers
from ..charts import allocation_chart_png
from ..components import build_app_bar, build_main_layout
from ..components.dialogs import show_confirm_dialog, show_error_dialog

if TYPE_CHECKING:
    from ..context import AppContext


def build_portfolio_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the portfolio holdings view."""

    uid = ctx.require_user_id()
    table_ref = ft.Ref[ft.DataTable]()
    chart_ref = ft.Ref[ft.Image]()
    total_holdings_text = ft.Ref[ft.Text]()
    cost_basis_text = ft.Ref[ft.Text]()

    def _account_name(account_id: int | None) -> str:
        if account_id is None:
            return "Unassigned"
        acct = ctx.account_repo.get_by_id(account_id, user_id=uid)
        return acct.name if acct else "Account missing"

    def _export_csv(_):
        try:
            holdings = ctx.holding_repo.list_all(user_id=uid)
            exports_dir = Path(ctx.config.DATA_DIR) / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            output = exports_dir / f"holdings_export_{stamp}.csv"
            with output.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["symbol", "quantity", "avg_price", "cost_basis", "account"])
                for h in holdings:
                    writer.writerow(
                        [
                            h.symbol,
                            f"{h.quantity:.4f}",
                            f"{h.avg_price:.2f}",
                            f"{h.quantity * h.avg_price:.2f}",
                            _account_name(h.account_id),
                        ]
                    )
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Exported holdings to {output}"), show_close_icon=True
            )
            page.snack_bar.open = True
            page.update()
        except Exception as exc:
            show_error_dialog(page, "Export failed", str(exc))

    def _open_dialog(existing: Holding | None = None) -> None:
        accounts = ctx.account_repo.list_all(user_id=uid)
        editing = existing is not None
        title = "Edit holding" if editing else "Add holding"
        symbol = ft.TextField(
            label="Symbol", value=(existing.symbol if existing else ""), width=200, autofocus=True
        )
        qty = ft.TextField(
            label="Quantity",
            value=str(existing.quantity if existing else ""),
            width=180,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        price = ft.TextField(
            label="Average price",
            value=str(existing.avg_price if existing else ""),
            width=180,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        account_dd = ft.Dropdown(
            label="Account",
            options=[ft.dropdown.Option(str(a.id), a.name) for a in accounts if a.id is not None]
            + [ft.dropdown.Option("", "Unassigned")],
            value=str(existing.account_id) if existing and existing.account_id else "",
            width=200,
        )

        def _save(_):
            try:
                account_id = int(account_dd.value) if account_dd.value else None
                record = Holding(
                    id=getattr(existing, "id", None),
                    symbol=(symbol.value or "").strip().upper(),
                    quantity=float(qty.value or 0),
                    avg_price=float(price.value or 0),
                    account_id=account_id,
                    currency="USD",
                    user_id=uid,
                )
                if editing:
                    ctx.holding_repo.update(record, user_id=uid)
                else:
                    ctx.holding_repo.create(record, user_id=uid)
                dialog.open = False
                _refresh()
            except Exception as exc:
                show_error_dialog(page, "Save failed", str(exc))

        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Column([symbol, qty, price, account_dd], tight=True, spacing=8),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: setattr(dialog, "open", False)),
                ft.FilledButton("Save", on_click=_save),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def _delete_holding(holding_id: int | None) -> None:
        if holding_id is None:
            return

        def _do_delete() -> None:
            ctx.holding_repo.delete(holding_id, user_id=uid)
            _refresh()

        show_confirm_dialog(page, "Delete holding", "Are you sure?", _do_delete)

    def _refresh() -> None:
        holdings = ctx.holding_repo.list_all(user_id=uid)
        total_cost_basis = ctx.holding_repo.get_total_cost_basis(user_id=uid)

        if total_holdings_text.current:
            total_holdings_text.current.value = str(len(holdings))
        if cost_basis_text.current:
            cost_basis_text.current.value = f"${total_cost_basis:,.2f}"

        rows: list[ft.DataRow] = []
        for h in holdings:
            cost_basis = h.quantity * h.avg_price
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(h.symbol)),
                        ft.DataCell(ft.Text(f"{h.quantity:,.4f}")),
                        ft.DataCell(ft.Text(f"${h.avg_price:,.2f}")),
                        ft.DataCell(ft.Text(f"${cost_basis:,.2f}")),
                        ft.DataCell(ft.Text(_account_name(h.account_id))),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        tooltip="Edit",
                                        on_click=lambda _, existing=h: _open_dialog(existing),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=ft.Colors.RED,
                                        tooltip="Delete",
                                        on_click=lambda _, hid=h.id: _delete_holding(hid),
                                    ),
                                ],
                                spacing=4,
                            )
                        ),
                    ]
                )
            )

        if not rows:
            rows = [ft.DataRow(cells=[ft.DataCell(ft.Text("No holdings found")) for _ in range(6)])]

        if table_ref.current:
            table_ref.current.rows = rows

        if chart_ref.current:
            chart_ref.current.src = str(allocation_chart_png(holdings)) if holdings else ""
        page.update()

    table = ft.DataTable(
        ref=table_ref,
        columns=[
            ft.DataColumn(ft.Text("Symbol")),
            ft.DataColumn(ft.Text("Quantity")),
            ft.DataColumn(ft.Text("Avg Price")),
            ft.DataColumn(ft.Text("Cost Basis")),
            ft.DataColumn(ft.Text("Account")),
            ft.DataColumn(ft.Text("Actions")),
        ],
        rows=[],
        expand=True,
    )

    summary_card = ft.Card(
        content=ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("Total Holdings", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text("", size=28, weight=ft.FontWeight.BOLD, ref=total_holdings_text),
                            ft.Text(
                                "Total Cost Basis", size=14, color=ft.Colors.ON_SURFACE_VARIANT
                            ),
                            ft.Text(
                                "",
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.PRIMARY,
                                ref=cost_basis_text,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Image(ref=chart_ref, height=160),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=20,
        ),
        elevation=2,
    )

    controls_row = ft.Row(
        [
            ft.FilledButton("Add holding", icon=ft.Icons.ADD, on_click=lambda _: _open_dialog(None)),
            ft.TextButton(
                "Import CSV",
                icon=ft.Icons.UPLOAD_FILE,
                on_click=lambda _: controllers.start_portfolio_import(ctx, page),
            ),
            ft.TextButton("Export CSV", icon=ft.Icons.DOWNLOAD, on_click=_export_csv),
        ],
        spacing=8,
    )

    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text("Portfolio", size=24, weight=ft.FontWeight.BOLD),
                    controls_row,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(height=16),
            summary_card,
            ft.Container(height=16),
            ft.Card(content=ft.Container(content=table, padding=12), expand=True),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    app_bar = build_app_bar(ctx, "Portfolio", page)
    main_layout = build_main_layout(ctx, page, "/portfolio", content)

    _refresh()

    return ft.View(
        route="/portfolio",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )
