"""Portfolio repository contracts and a simple SQLModel implementation."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Protocol

from sqlmodel import Session, select

from ...models import Account, Holding, Transaction


class PortfolioRepository(Protocol):
    """Persistence operations for portfolio holdings."""

    def list_holdings(self) -> Iterable[dict]:  # pragma: no cover - interface
        ...

    def import_positions(self, *, rows: List[dict]) -> int:  # pragma: no cover - interface
        ...

    def allocation_summary(self) -> dict:  # pragma: no cover - interface
        ...


class SqlModelPortfolioRepository:
    """A minimal SQLModel-backed repository implementation."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_holdings(self):
        return list(self.session.exec(select(Holding)).all())

    def import_positions(self, *, rows: List[dict]) -> int:
        processed_symbols: dict[tuple[Optional[int], str], set[str]] = defaultdict(set)
        created_or_updated = 0

        for row in rows:
            symbol = self._clean_symbol(row)
            if not symbol:
                continue

            quantity = self._parse_float(row.get("quantity"))
            avg_price = self._parse_float(row.get("avg_price") or row.get("price"))
            if quantity is None or avg_price is None:
                continue

            currency = self._clean_currency(row.get("currency"))
            account_id = self._resolve_account(row, currency)
            acquired_at = self._parse_datetime(row.get("acquired_at") or row.get("purchased_at"))

            key = (account_id, currency)
            processed_symbols[key].add(symbol)

            holding = self._fetch_holding(symbol, account_id, currency)
            if holding is None:
                holding = Holding(symbol=symbol, account_id=account_id, currency=currency)

            holding.quantity = quantity
            holding.avg_price = avg_price
            holding.currency = currency
            if acquired_at is not None:
                holding.acquired_at = acquired_at

            self.session.add(holding)
            created_or_updated += 1

            self._upsert_portfolio_transaction(
                row=row,
                symbol=symbol,
                quantity=quantity,
                avg_price=avg_price,
                currency=currency,
                account_id=account_id,
            )
        self._prune_missing_records(processed_symbols)
        self.session.commit()
        return created_or_updated

    def allocation_summary(self) -> dict:
        rows = self.session.exec(select(Holding)).all()
        allocation_totals: dict[str, float] = defaultdict(float)
        for holding in rows:
            value = (holding.quantity or 0.0) * (holding.avg_price or 0.0)
            allocation_totals[holding.symbol] += value

        total_value = sum(allocation_totals.values())
        allocation = {
            symbol: (value / total_value if total_value else 0.0)
            for symbol, value in allocation_totals.items()
        }
        return {"total_value": total_value, "allocation": allocation}

    # internal helpers -------------------------------------------------

    def _fetch_holding(
        self,
        symbol: str,
        account_id: Optional[int],
        currency: str,
    ) -> Optional[Holding]:
        stmt = select(Holding).where(
            Holding.symbol == symbol,
            Holding.account_id == account_id,
            Holding.currency == currency,
        )
        return self.session.exec(stmt).one_or_none()

    def _clean_symbol(self, row: dict) -> str | None:
        raw = row.get("symbol") or row.get("ticker")
        if not isinstance(raw, str):
            return None
        cleaned = raw.strip().upper()
        return cleaned or None

    def _parse_float(self, value) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _parse_datetime(self, value) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    def _clean_currency(self, value) -> str:
        if isinstance(value, str):
            text = value.strip().upper()
            if len(text) >= 3:
                return text[:3]
        return "USD"

    def _resolve_account(self, row: dict, currency: str) -> Optional[int]:
        account_id_value = row.get("account_id")
        if account_id_value not in (None, ""):
            try:
                account_id_int = int(account_id_value)
            except (TypeError, ValueError):
                account_id_int = None
            else:
                account = self.session.get(Account, account_id_int)
                if account is not None:
                    return account.id

        account_name = row.get("account_name") or row.get("account")
        if isinstance(account_name, str) and account_name.strip():
            name = account_name.strip()
            stmt = select(Account).where(Account.name == name)
            account = self.session.exec(stmt).one_or_none()
            if account is None:
                account = Account(name=name, currency=currency)
                self.session.add(account)
                self.session.flush()
            return account.id

        return None

    def _build_external_id(
        self,
        *,
        symbol: str,
        account_id: Optional[int],
        currency: str,
    ) -> str:
        account_component = str(account_id) if account_id is not None else "none"
        return f"portfolio:{account_component}:{currency}:{symbol}".lower()

    def _upsert_portfolio_transaction(
        self,
        *,
        row: dict,
        symbol: str,
        quantity: float,
        avg_price: float,
        currency: str,
        account_id: Optional[int],
    ) -> None:
        amount = self._parse_float(row.get("amount"))
        if amount is None:
            amount = quantity * avg_price

        occurred_at = self._parse_datetime(row.get("occurred_at") or row.get("date"))
        if occurred_at is None:
            occurred_at = datetime.now(timezone.utc).replace(tzinfo=None)

        memo = row.get("memo") or row.get("note") or f"Portfolio position: {symbol}"
        memo = str(memo)

        external_id = row.get("external_id")
        if not external_id:
            external_id = self._build_external_id(
                symbol=symbol, account_id=account_id, currency=currency
            )

        stmt = select(Transaction).where(Transaction.external_id == external_id)
        transaction = self.session.exec(stmt).one_or_none()
        if transaction is None:
            transaction = Transaction(
                external_id=external_id,
                occurred_at=occurred_at,
                amount=amount,
                memo=memo,
            )
        else:
            transaction.occurred_at = occurred_at
            transaction.amount = amount
            transaction.memo = memo

        transaction.account_id = account_id
        transaction.currency = currency

        self.session.add(transaction)

    def _prune_missing_records(self, processed_symbols: dict) -> None:
        for (account_id, currency), symbols in processed_symbols.items():
            stmt = select(Holding).where(
                Holding.account_id == account_id,
                Holding.currency == currency,
            )
            for holding in self.session.exec(stmt):
                if holding.symbol not in symbols:
                    self.session.delete(holding)

            account_component = str(account_id) if account_id is not None else "none"
            normalized_currency = currency.lower() if isinstance(currency, str) else "usd"
            prefix = f"portfolio:{account_component}:{normalized_currency}:"
            txn_stmt = select(Transaction).where(
                Transaction.account_id == account_id,
                Transaction.currency == currency,
            )
            for transaction in self.session.exec(txn_stmt):
                if not transaction.external_id or not transaction.external_id.startswith(prefix):
                    continue
                symbol = transaction.external_id.split(":")[-1].upper()
                if symbol not in symbols:
                    self.session.delete(transaction)
