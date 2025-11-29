from calendar import monthrange
from datetime import date
from typing import Callable

import flet as ft
import pytest

from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.views import dashboard
from pocketsage.models import Category
from pocketsage.services.admin_tasks import reset_demo_database, run_demo_seed
from pocketsage.services.heavy_seed import run_heavy_seed


class DummyPage:
    def __init__(self):
        self.views: list[ft.View] = []
        self.route = "/"
        self.snack_bar = None
        self.dialog = None
        self.overlay: list[ft.Control] = []
        self.padding = 0
        self.window_width = 1280
        self.window_height = 800
        self.window_min_width = 1024
        self.window_min_height = 600
        self.theme_mode = ft.ThemeMode.DARK
        self.window = type("Win", (), {"destroy": lambda: None})()

    def go(self, route: str) -> None:
        self.route = route

    def update(self) -> None:
        return None


def _find_control(root: ft.Control, predicate: Callable[[ft.Control], bool]) -> ft.Control | None:
    stack = [root]
    seen: set[int] = set()
    while stack:
        control = stack.pop()
        if id(control) in seen:
            continue
        seen.add(id(control))
        try:
            if predicate(control):
                return control
        except Exception:
            pass
        for attr in ("controls", "content", "actions"):
            child = getattr(control, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                stack.extend(child)
            elif isinstance(child, ft.Control):
                stack.append(child)
    return None


def _find_image_sources(root: ft.Control) -> list[str]:
    images: list[str] = []
    stack = [root]
    seen: set[int] = set()
    while stack:
        control = stack.pop()
        if id(control) in seen:
            continue
        seen.add(id(control))
        if isinstance(control, ft.Image):
            src = getattr(control, "src", "") or ""
            if src:
                images.append(src)
        for attr in ("controls", "content", "actions"):
            child = getattr(control, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                stack.extend(child)
            elif isinstance(child, ft.Control):
                stack.append(child)
    return images


def _category_names(ctx) -> set[str]:
    return {c.name for c in ctx.category_repo.list_all(user_id=ctx.require_user_id())}


@pytest.mark.parametrize("restart", [False, True])
def test_seed_creates_all_sections(monkeypatch: pytest.MonkeyPatch, tmp_path, restart: bool):
    data_dir = tmp_path / "instance"
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("POCKETSAGE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")

    ctx = create_app_context()
    user = ctx.current_user or ctx.require_user_id()  # ensure user exists
    uid = ctx.require_user_id()

    first_summary = run_demo_seed(session_factory=ctx.session_factory, user_id=uid, force=True)
    assert first_summary.categories > 5
    assert first_summary.accounts > 0
    assert first_summary.habits > 0
    assert first_summary.liabilities > 0
    assert first_summary.budgets > 0
    assert first_summary.transactions > 0

    if restart:
        reset_demo_database(user_id=uid, session_factory=ctx.session_factory, reseed=False)
        second = run_heavy_seed(session_factory=ctx.session_factory, user_id=uid)
        assert second.transactions > 0
        assert second.categories >= first_summary.categories
        assert second.accounts >= first_summary.accounts

    names = _category_names(ctx)
    for expected in {"Groceries", "Salary", "Rent", "Utilities", "Transfer In", "Transfer Out"}:
        assert expected in names

    # Dashboard should surface charts after seeding
    page = DummyPage()
    dash_view = dashboard.build_dashboard_view(ctx, page)
    assert _find_image_sources(dash_view)
