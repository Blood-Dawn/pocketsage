"""Portfolio routes."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Dict, Iterable

from flask import (
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

from ...extensions import session_scope
from . import bp
from .repository import SqlModelPortfolioRepository

COLUMN_ALIASES: Dict[str, tuple[str, ...]] = {
    "symbol": ("symbol", "ticker", "security"),
    "quantity": ("quantity", "shares", "units"),
    "avg_price": ("avg_price", "price", "cost_basis", "basis", "avgprice"),
    "amount": ("amount", "value", "market_value", "balance"),
    "occurred_at": ("occurred_at", "date", "trade_date", "priced_at", "asof"),
    "acquired_at": ("acquired_at", "purchased_at", "purchase_date"),
    "account_id": ("account_id", "accountid", "acct_id"),
    "account_name": ("account", "account_name", "portfolio", "wallet"),
    "currency": ("currency", "ccy", "fx"),
    "memo": ("memo", "note", "description"),
    "external_id": ("external_id", "externalid", "id", "uid"),
}


def _prefers_json() -> bool:
    accepts = request.accept_mimetypes
    json_quality = accepts["application/json"]
    html_quality = accepts["text/html"]
    if json_quality == 0:
        return False
    return json_quality > html_quality


def _format_quantity(amount: float) -> str:
    if amount.is_integer():
        return f"{int(amount):,}"
    return f"{amount:,.4f}".rstrip("0").rstrip(".")


def _suggest_mapping(columns: Iterable[str]) -> dict[str, str | None]:
    normalized = [c.strip().lower() for c in columns]
    mapping: dict[str, str | None] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        mapping[canonical] = next((col for col in normalized if col in aliases), None)
    return mapping


def _normalize_rows(rows: Iterable[dict], mapping: dict[str, str | None]) -> list[dict]:
    normalized: list[dict] = []
    permitted_keys = {canonical for canonical, column in mapping.items() if column}
    for row in rows:
        clean = {
            (key or "").strip().lower(): (str(value).strip() if value is not None else "")
            for key, value in row.items()
        }
        for canonical, column in mapping.items():
            if column and column in clean:
                clean[canonical] = clean[column]
            elif not column:
                clean.pop(canonical, None)
        if permitted_keys:
            filtered = {key: clean.get(key, "") for key in permitted_keys}
        else:
            filtered = {}
        normalized.append(filtered)
    return normalized


@bp.get("/")
def list_portfolio():
    """Show current holdings and allocation summary."""

    with session_scope() as session:
        repo = SqlModelPortfolioRepository(session)
        raw_holdings = list(repo.list_holdings())
        summary = repo.allocation_summary()

        allocation_map = summary.get("allocation", {})
        holdings_view: list[dict] = []
        for holding in raw_holdings:
            quantity = float(holding.quantity or 0)
            avg_price = float(holding.avg_price or 0)
            value = quantity * avg_price
            allocation_pct = round(allocation_map.get(holding.symbol, 0.0) * 100, 2)
            account_name = None
            if holding.account is not None:
                account_name = holding.account.name
            elif holding.account_id is not None:
                account_name = f"Account #{holding.account_id}"
            holdings_view.append(
                {
                    "symbol": holding.symbol,
                    "quantity": quantity,
                    "quantity_display": _format_quantity(quantity),
                    "avg_price": avg_price,
                    "avg_price_display": f"${avg_price:,.2f}",
                    "value": value,
                    "value_display": f"${value:,.2f}",
                    "allocation_pct": allocation_pct,
                    "allocation_display": f"{allocation_pct:.2f}%",
                    "account": account_name,
                    "currency": (holding.currency or "USD").upper(),
                }
            )

        total_value = summary.get("total_value", 0.0) or 0.0

    holdings_view.sort(key=lambda h: h["value"], reverse=True)
    allocation_chart = [
        {"symbol": h["symbol"], "percentage": h["allocation_pct"]}
        for h in holdings_view
        if h["allocation_pct"] > 0
    ]

    return render_template(
        "portfolio/index.html",
        holdings=holdings_view,
        total_value=total_value,
        allocation=allocation_chart,
        upload_url=url_for("portfolio.upload_portfolio"),
        export_url=url_for("portfolio.export_holdings"),
    )


def _apply_mapping_overrides(
    mapping: dict[str, str | None],
    overrides: dict[str, str | None],
    *,
    available_columns: Iterable[str],
) -> dict[str, str | None]:
    """Merge mapping overrides with detected mapping."""

    columns = {column.strip().lower() for column in available_columns}
    merged = mapping.copy()
    for canonical, column in overrides.items():
        if canonical not in merged:
            continue
        if column in (None, ""):
            merged[canonical] = None
            continue
        normalized_column = str(column).strip().lower()
        if normalized_column in columns:
            merged[canonical] = normalized_column
    return merged


def _preview_rows(rows: list[dict], mapping: dict[str, str | None], limit: int = 5) -> list[dict]:
    """Return a lightweight preview of the normalized rows."""

    preview_columns = [key for key, column in mapping.items() if column]
    samples: list[dict] = []
    for row in rows[:limit]:
        samples.append({column: row.get(column, "") for column in preview_columns})
    return samples


@bp.post("/import")
def import_portfolio():
    """Handle CSV upload for portfolio positions."""

    wants_json = _prefers_json()
    file_storage = request.files.get("file")
    if file_storage is None or not file_storage.filename:
        message = "Please choose a CSV file to import."
        if wants_json:
            return jsonify({"error": "missing_file", "message": message}), 400
        flash(message, "warning")
        return redirect(url_for("portfolio.upload_portfolio"))

    is_preview = request.form.get("preview") in {"1", "true", "yes"}

    mapping_overrides_raw = request.form.get("mapping")
    mapping_overrides: dict[str, str | None] = {}
    if mapping_overrides_raw:
        try:
            loaded = json.loads(mapping_overrides_raw)
        except (TypeError, ValueError):
            loaded = {}
        if isinstance(loaded, dict):
            mapping_overrides = {
                str(key): (value if value not in (None, "") else None)
                for key, value in loaded.items()
            }

    upload_dir = Path(current_app.instance_path) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(file_storage.filename or "portfolio.csv")
    file_path = upload_dir / filename
    file_storage.save(file_path)

    rows: list[dict]
    mapping: dict[str, str | None] = {}
    normalized_headers: list[str] = []
    try:
        with file_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("CSV file is missing a header row")
            normalized_headers = [header.strip().lower() for header in reader.fieldnames]
            reader.fieldnames = normalized_headers
            mapping = _suggest_mapping(normalized_headers)
            if mapping_overrides:
                mapping = _apply_mapping_overrides(
                    mapping,
                    mapping_overrides,
                    available_columns=normalized_headers,
                )
            rows = _normalize_rows(reader, mapping)
    except Exception:  # pragma: no cover - surfaced via user feedback
        file_path.unlink(missing_ok=True)
        message = "Unable to read CSV file. Please verify the format."
        if wants_json:
            return jsonify({"error": "invalid_csv", "message": message}), 400
        flash(message, "danger")
        return redirect(url_for("portfolio.upload_portfolio"))

    file_path.unlink(missing_ok=True)

    if is_preview:
        samples = _preview_rows(rows, mapping)
        payload = {
            "message": "Preview generated.",
            "mapping": mapping,
            "source_columns": normalized_headers,
            "samples": samples,
            "total_rows": len(rows),
        }
        if wants_json:
            return jsonify(payload)
        flash("Preview generated.", "info")
        return redirect(url_for("portfolio.upload_portfolio"))

    with session_scope() as session:
        repo = SqlModelPortfolioRepository(session)
        imported = repo.import_positions(rows=rows)

    message = f"Imported {imported} holdings." if imported else "No holdings were imported."
    if wants_json:
        status = 200 if imported else 202
        return (
            jsonify(
                {
                    "imported": imported,
                    "message": message,
                    "redirect": url_for("portfolio.list_portfolio"),
                    "mapping": mapping,
                }
            ),
            status,
        )

    account_hint = mapping.get("account_id") or mapping.get("account_name") or "n/a"
    currency_hint = mapping.get("currency") or "n/a"
    flash(
        f"{message} (account column: {account_hint}, currency column: {currency_hint}).",
        "success" if imported else "info",
    )
    return redirect(url_for("portfolio.list_portfolio"))


@bp.get("/upload")
def upload_portfolio():
    """Render upload form for portfolio CSV."""

    return render_template("portfolio/upload.html")


@bp.get("/export")
def export_holdings():
    """Download current holdings as a CSV export."""

    rows: list[tuple[str, float, float, float]] = []

    with session_scope() as session:
        repo = SqlModelPortfolioRepository(session)
        raw_holdings = list(repo.list_holdings())

        if not raw_holdings:
            flash("No holdings available to export.", "warning")
            return redirect(url_for("portfolio.list_portfolio"))

        for holding in raw_holdings:
            quantity = float(holding.quantity or 0)
            avg_price = float(holding.avg_price or 0)
            value = quantity * avg_price
            rows.append((holding.symbol, quantity, avg_price, value))

    if not rows:
        flash("No holdings available to export.", "warning")
        return redirect(url_for("portfolio.list_portfolio"))

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["symbol", "quantity", "avg_price", "value"])
    writer.writerows(rows)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = (
        f"attachment; filename=pocketsage_holdings_{timestamp}.csv"
    )
    return response
