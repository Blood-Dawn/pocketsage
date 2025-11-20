from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import flet as ft
import pytest
from pocketsage.config import BaseConfig
from pocketsage.desktop import controllers
from pocketsage.infra.database import create_db_engine, init_database, session_scope
from pocketsage.services import auth


class _PageSpy:
    def __init__(self):
        self.route: str | None = None
        self.overlay: list[ft.Control] = []
        self.snacks: list[str] = []
        self.updates: int = 0

    def go(self, route: str) -> None:
        self.route = route

    def update(self) -> None:
        self.updates += 1


class _PickerSpy:
    def __init__(self):
        self.called_with: dict[str, Any] = {}

    def pick_files(self, **kwargs) -> None:
        self.called_with = kwargs


@pytest.fixture()
def session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "desktop-actions.db"
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")
    config = BaseConfig()
    engine = create_db_engine(config)
    init_database(engine)

    def base_factory():
        return session_scope(engine)

    user = auth.create_user(
        username="admin",
        password="password",
        role="admin",
        session_factory=base_factory,
    )

    def factory():
        return session_scope(engine)

    return factory, user


def test_handle_navigation_selection_updates_route() -> None:
    page = _PageSpy()
    user = SimpleNamespace(role="admin")
    ctx = SimpleNamespace(current_user=user)

    controllers.handle_nav_selection(ctx, page, 1)  # /ledger

    assert page.route == "/ledger"
    assert page.updates == 1


def test_handle_shortcut_routes_to_habits() -> None:
    page = _PageSpy()

    handled = controllers.handle_shortcut(page, "h", ctrl=True, shift=True)

    assert handled is True
    assert page.route == "/habits"


def test_start_ledger_import_invokes_picker() -> None:
    page = _PageSpy()
    ctx = SimpleNamespace(file_picker=_PickerSpy(), file_picker_mode=None)

    controllers.start_ledger_import(ctx, page)

    assert ctx.file_picker_mode == "ledger"
    assert ctx.file_picker.called_with["allow_multiple"] is False
    assert ctx.file_picker.called_with["allowed_extensions"] == ["csv"]


def test_file_picker_result_triggers_ledger_import(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    calls: dict[str, Path] = {}

    def fake_import_ledger_transactions(
        *, csv_path: Path, session_factory, mapping=None, user_id: int
    ):
        calls["ledger"] = csv_path
        return 2

    monkeypatch.setattr(
        controllers.importers, "import_ledger_transactions", fake_import_ledger_transactions
    )

    ctx = SimpleNamespace(
        session_factory=lambda: None,
        file_picker=None,
        file_picker_mode=None,
        require_user_id=lambda: 1,
    )
    page = _PageSpy()
    picker = controllers.attach_file_picker(ctx, page)

    csv_file = tmp_path / "ledger.csv"
    csv_file.write_text("date,amount,memo\n2024-01-01,-10,Test")
    ctx.file_picker_mode = "ledger"
    event = SimpleNamespace(files=[SimpleNamespace(path=str(csv_file))])

    picker.on_result(event)

    assert calls["ledger"] == csv_file
    assert page.route == "/ledger"
    assert "Imported 2 transactions" in page.snack_bar.content.value  # type: ignore[attr-defined]


def test_file_picker_result_triggers_portfolio_import(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    calls: dict[str, Path] = {}

    def fake_import_portfolio_holdings(*, csv_path: Path, session_factory, user_id: int):
        calls["portfolio"] = csv_path
        return 3

    monkeypatch.setattr(
        controllers.importers, "import_portfolio_holdings", fake_import_portfolio_holdings
    )

    ctx = SimpleNamespace(
        session_factory=lambda: None,
        file_picker=None,
        file_picker_mode=None,
        require_user_id=lambda: 1,
    )
    page = _PageSpy()
    picker = controllers.attach_file_picker(ctx, page)

    csv_file = tmp_path / "portfolio.csv"
    csv_file.write_text("symbol,shares,price\nAAPL,1,100")
    ctx.file_picker_mode = "portfolio"
    event = SimpleNamespace(files=[SimpleNamespace(path=str(csv_file))])

    picker.on_result(event)

    assert calls["portfolio"] == csv_file
    assert page.route == "/portfolio"
    assert "Imported 3 holdings" in page.snack_bar.content.value  # type: ignore[attr-defined]


def test_run_and_reset_demo_seed_show_feedback(session_factory):
    page = _PageSpy()
    factory, user = session_factory
    ctx = SimpleNamespace(
        session_factory=factory,
        file_picker=None,
        file_picker_mode=None,
        require_user_id=lambda: user.id,
    )

    controllers.run_demo_seed(ctx, page)
    assert page.snack_bar is not None  # type: ignore[attr-defined]
    assert "Demo data ready" in page.snack_bar.content.value  # type: ignore[attr-defined]

    controllers.reset_demo_data(ctx, page)
    assert "reset" in page.snack_bar.content.value.lower()  # type: ignore[attr-defined]
