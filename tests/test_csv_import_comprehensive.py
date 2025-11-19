"""Comprehensive tests for CSV import functionality.

Tests cover:
- Parsing CSV files with various formats
- Column mapping and normalization
- Data type conversion and validation
- Idempotent imports (no duplicates on re-import)
- External ID deduplication
- Error handling for malformed data
- Edge cases (empty files, missing columns, etc.)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from pocketsage.services.import_csv import (
    ColumnMapping,
    import_csv_file,
    normalize_frame,
    upsert_transactions,
)


class TestNormalizeFrame:
    """Tests for CSV file normalization (loading and column cleanup)."""

    def test_loads_basic_csv(self):
        """Should load a basic CSV file successfully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("Date,Amount,Description\n")
            f.write("2024-01-01,100.00,Salary\n")
            f.write("2024-01-02,-50.00,Groceries\n")
            csv_path = Path(f.name)

        try:
            df = normalize_frame(file_path=csv_path)

            assert len(df) == 2
            assert list(df.columns) == ["date", "amount", "description"]
            assert df["amount"].iloc[0] == 100.00
            assert df["amount"].iloc[1] == -50.00
        finally:
            csv_path.unlink()

    def test_normalizes_column_names_to_lowercase(self):
        """Column names should be normalized to lowercase."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("DATE,AMOUNT,Description,Memo\n")
            f.write("2024-01-01,100,Test,Note\n")
            csv_path = Path(f.name)

        try:
            df = normalize_frame(file_path=csv_path)

            # All columns should be lowercase
            assert list(df.columns) == ["date", "amount", "description", "memo"]
        finally:
            csv_path.unlink()

    def test_strips_whitespace_from_column_names(self):
        """Whitespace should be stripped from column names."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(" Date , Amount , Description \n")
            f.write("2024-01-01,100,Test\n")
            csv_path = Path(f.name)

        try:
            df = normalize_frame(file_path=csv_path)

            # Whitespace should be stripped
            assert list(df.columns) == ["date", "amount", "description"]
        finally:
            csv_path.unlink()

    def test_handles_utf8_encoding(self):
        """Should handle UTF-8 encoded files with special characters."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write("date,amount,description\n")
            f.write("2024-01-01,-25.00,Café lunch\n")
            f.write("2024-01-02,100.00,Paychèque\n")
            csv_path = Path(f.name)

        try:
            df = normalize_frame(file_path=csv_path, encoding="utf-8")

            assert len(df) == 2
            assert "Café" in df["description"].iloc[0]
            assert "Paychèque" in df["description"].iloc[1]
        finally:
            csv_path.unlink()


class TestUpsertTransactions:
    """Tests for converting CSV rows to transaction dictionaries."""

    def test_basic_transaction_conversion(self):
        """Should convert basic CSV rows to transaction dicts."""
        rows = [
            {"date": "2024-01-01", "amount": "100.00", "memo": "Salary"},
            {"date": "2024-01-02", "amount": "-50.00", "memo": "Groceries"},
        ]

        mapping = ColumnMapping(
            amount="amount",
            occurred_at="date",
            memo="memo",
        )

        transactions = upsert_transactions(rows=rows, mapping=mapping)

        assert len(transactions) == 2
        assert transactions[0]["amount"] == 100.00
        assert transactions[0]["occurred_at"] == "2024-01-01"
        assert transactions[0]["memo"] == "Salary"
        assert transactions[1]["amount"] == -50.00

    def test_skips_rows_with_missing_amount(self):
        """Rows with missing amount should be skipped."""
        rows = [
            {"date": "2024-01-01", "amount": "100.00", "memo": "Valid"},
            {"date": "2024-01-02", "amount": None, "memo": "Missing amount"},
            {"date": "2024-01-03", "amount": "", "memo": "Empty amount"},
            {"date": "2024-01-04", "amount": "50.00", "memo": "Valid"},
        ]

        mapping = ColumnMapping(
            amount="amount",
            occurred_at="date",
            memo="memo",
        )

        transactions = upsert_transactions(rows=rows, mapping=mapping)

        # Should only have 2 valid transactions
        assert len(transactions) == 2
        assert transactions[0]["memo"] == "Valid"
        assert transactions[1]["memo"] == "Valid"

    def test_skips_rows_with_invalid_amount(self):
        """Rows with non-numeric amount should be skipped."""
        rows = [
            {"date": "2024-01-01", "amount": "100.00", "memo": "Valid"},
            {"date": "2024-01-02", "amount": "not a number", "memo": "Invalid"},
            {"date": "2024-01-03", "amount": "50.00", "memo": "Valid"},
        ]

        mapping = ColumnMapping(
            amount="amount",
            occurred_at="date",
            memo="memo",
        )

        transactions = upsert_transactions(rows=rows, mapping=mapping)

        # Should only have 2 valid transactions
        assert len(transactions) == 2
        assert all(tx["memo"] in ["Valid"] for tx in transactions)

    def test_handles_optional_fields(self):
        """Optional fields should default to None or empty string."""
        rows = [
            {"date": "2024-01-01", "amount": "100.00"},  # No memo
        ]

        mapping = ColumnMapping(
            amount="amount",
            occurred_at="date",
            memo="memo",  # Mapped but not present
        )

        transactions = upsert_transactions(rows=rows, mapping=mapping)

        assert len(transactions) == 1
        assert transactions[0]["memo"] == ""  # Defaults to empty string

    def test_maps_external_id_for_deduplication(self):
        """External ID should be mapped for deduplication."""
        rows = [
            {"date": "2024-01-01", "amount": "100.00", "transaction_id": "TXN-001"},
            {"date": "2024-01-02", "amount": "-50.00", "transaction_id": "TXN-002"},
        ]

        mapping = ColumnMapping(
            amount="amount",
            occurred_at="date",
            external_id="transaction_id",
        )

        transactions = upsert_transactions(rows=rows, mapping=mapping)

        assert transactions[0]["external_id"] == "TXN-001"
        assert transactions[1]["external_id"] == "TXN-002"

    def test_maps_account_id_as_integer(self):
        """Account ID should be converted to integer."""
        rows = [
            {"date": "2024-01-01", "amount": "100.00", "account": "1"},
            {"date": "2024-01-02", "amount": "-50.00", "account": "2"},
        ]

        mapping = ColumnMapping(
            amount="amount",
            occurred_at="date",
            account_id="account",
        )

        transactions = upsert_transactions(rows=rows, mapping=mapping)

        assert transactions[0]["account_id"] == 1
        assert transactions[1]["account_id"] == 2

    def test_handles_invalid_account_id_gracefully(self):
        """Invalid account ID should be set to None."""
        rows = [
            {"date": "2024-01-01", "amount": "100.00", "account": "not a number"},
            {"date": "2024-01-02", "amount": "-50.00", "account": ""},
        ]

        mapping = ColumnMapping(
            amount="amount",
            occurred_at="date",
            account_id="account",
        )

        transactions = upsert_transactions(rows=rows, mapping=mapping)

        # Account ID should be None for invalid values
        assert "account_id" not in transactions[0] or transactions[0].get("account_id") is None
        assert "account_id" not in transactions[1] or transactions[1].get("account_id") is None

    def test_maps_account_name_from_string(self):
        """Account name should be extracted and trimmed."""
        rows = [
            {"date": "2024-01-01", "amount": "100.00", "account_name": " Checking "},
            {"date": "2024-01-02", "amount": "-50.00", "account_name": "Savings"},
        ]

        mapping = ColumnMapping(
            amount="amount",
            occurred_at="date",
            account_name="account_name",
        )

        transactions = upsert_transactions(rows=rows, mapping=mapping)

        assert transactions[0]["account_name"] == "Checking"  # Trimmed
        assert transactions[1]["account_name"] == "Savings"

    def test_ignores_empty_account_name(self):
        """Empty account name should not be included."""
        rows = [
            {"date": "2024-01-01", "amount": "100.00", "account_name": ""},
            {"date": "2024-01-02", "amount": "-50.00", "account_name": "   "},
        ]

        mapping = ColumnMapping(
            amount="amount",
            occurred_at="date",
            account_name="account_name",
        )

        transactions = upsert_transactions(rows=rows, mapping=mapping)

        # account_name should not be in the result
        assert "account_name" not in transactions[0]
        assert "account_name" not in transactions[1]

    def test_maps_currency_to_uppercase(self):
        """Currency should be uppercased and trimmed to 3 chars."""
        rows = [
            {"date": "2024-01-01", "amount": "100.00", "currency": "usd"},
            {"date": "2024-01-02", "amount": "-50.00", "currency": " eur "},
            {"date": "2024-01-03", "amount": "75.00", "currency": "GBPXXX"},  # Too long
        ]

        mapping = ColumnMapping(
            amount="amount",
            occurred_at="date",
            currency="currency",
        )

        transactions = upsert_transactions(rows=rows, mapping=mapping)

        assert transactions[0]["currency"] == "USD"
        assert transactions[1]["currency"] == "EUR"
        assert transactions[2]["currency"] == "GBP"  # Trimmed to 3 chars

    def test_ignores_empty_currency(self):
        """Empty currency should not be included."""
        rows = [
            {"date": "2024-01-01", "amount": "100.00", "currency": ""},
            {"date": "2024-01-02", "amount": "-50.00", "currency": "   "},
        ]

        mapping = ColumnMapping(
            amount="amount",
            occurred_at="date",
            currency="currency",
        )

        transactions = upsert_transactions(rows=rows, mapping=mapping)

        assert "currency" not in transactions[0]
        assert "currency" not in transactions[1]


class TestImportCsvFile:
    """Tests for end-to-end CSV file import."""

    def test_imports_valid_csv_file(self):
        """Should import a valid CSV file and return row count."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("date,amount,description\n")
            f.write("2024-01-01,100.00,Salary\n")
            f.write("2024-01-02,-50.00,Groceries\n")
            f.write("2024-01-03,-25.00,Gas\n")
            csv_path = Path(f.name)

        try:
            mapping = ColumnMapping(
                amount="amount",
                occurred_at="date",
                memo="description",
            )

            count = import_csv_file(csv_path=csv_path, mapping=mapping)

            # Should return count of parsed transactions
            assert count == 3
        finally:
            csv_path.unlink()

    def test_skips_invalid_rows_and_returns_valid_count(self):
        """Should skip invalid rows and return count of valid ones."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("date,amount,description\n")
            f.write("2024-01-01,100.00,Valid\n")
            f.write("2024-01-02,invalid,Invalid amount\n")
            f.write("2024-01-03,-50.00,Valid\n")
            f.write("2024-01-04,,Missing amount\n")
            f.write("2024-01-05,75.00,Valid\n")
            csv_path = Path(f.name)

        try:
            mapping = ColumnMapping(
                amount="amount",
                occurred_at="date",
                memo="description",
            )

            count = import_csv_file(csv_path=csv_path, mapping=mapping)

            # Should only count 3 valid rows
            assert count == 3
        finally:
            csv_path.unlink()

    def test_handles_empty_csv_file(self):
        """Empty CSV file should return count of 0."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("date,amount,description\n")  # Header only
            csv_path = Path(f.name)

        try:
            mapping = ColumnMapping(
                amount="amount",
                occurred_at="date",
                memo="description",
            )

            count = import_csv_file(csv_path=csv_path, mapping=mapping)

            assert count == 0
        finally:
            csv_path.unlink()

    def test_preserves_external_ids_for_deduplication(self):
        """External IDs should be preserved for idempotent re-imports."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("transaction_id,date,amount,description\n")
            f.write("TXN-001,2024-01-01,100.00,Salary\n")
            f.write("TXN-002,2024-01-02,-50.00,Groceries\n")
            csv_path = Path(f.name)

        try:
            mapping = ColumnMapping(
                amount="amount",
                occurred_at="date",
                memo="description",
                external_id="transaction_id",
            )

            count = import_csv_file(csv_path=csv_path, mapping=mapping)

            # Note: This function returns count but doesn't actually persist to DB
            # The caller is responsible for persisting using a repository
            assert count == 2
        finally:
            csv_path.unlink()


class TestIdempotentImport:
    """Tests for idempotent CSV imports (no duplicates on re-import).

    Note: This requires integration with actual repository/database layer.
    These tests verify the external_id mapping works correctly at the parsing level.
    """

    def test_external_id_uniquely_identifies_transactions(self):
        """External ID should be used to identify unique transactions."""
        # First import
        rows1 = [
            {
                "transaction_id": "TXN-001",
                "date": "2024-01-01",
                "amount": "100.00",
                "memo": "Original",
            },
        ]

        # Second import (same transaction_id, different amount - should update)
        rows2 = [
            {
                "transaction_id": "TXN-001",
                "date": "2024-01-01",
                "amount": "150.00",
                "memo": "Updated",
            },
        ]

        mapping = ColumnMapping(
            amount="amount",
            occurred_at="date",
            memo="memo",
            external_id="transaction_id",
        )

        txs1 = upsert_transactions(rows=rows1, mapping=mapping)
        txs2 = upsert_transactions(rows=rows2, mapping=mapping)

        # Both should have the same external_id
        assert txs1[0]["external_id"] == "TXN-001"
        assert txs2[0]["external_id"] == "TXN-001"

        # The updated transaction has different amount
        assert txs2[0]["amount"] == 150.00
        assert txs2[0]["memo"] == "Updated"
