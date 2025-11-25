from __future__ import annotations

import os
import tempfile

import flet as ft

from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.views import debts, habits, portfolio, reports


class _PageStub:
    def __init__(self):
        self.views: list[ft.View] = []
        self.route: str = ""
        self.snack_bar = None
        self.overlay: list[ft.Control] = []
        self.padding = 0
        self.window_width = 1280
        self.window_height = 800
        self.window_min_width = 1024
        self.window_min_height = 600
        self.theme_mode = ft.ThemeMode.DARK

    def go(self, route: str):
        self.route = route

    def update(self):
        return None


def _ctx_and_page():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    data_dir = tempfile.mkdtemp()
    os.environ["POCKETSAGE_DATABASE_URL"] = f"sqlite:///{tmp.name}"
    os.environ["POCKETSAGE_DATA_DIR"] = data_dir
    ctx = create_app_context()
    page = _PageStub()
    return ctx, page


def test_habits_view_reachable():
    ctx, page = _ctx_and_page()
    view = habits.build_habits_view(ctx, page)
    assert view.route == "/habits"


def test_debts_view_reachable():
    ctx, page = _ctx_and_page()
    view = debts.build_debts_view(ctx, page)
    assert view.route == "/debts"


def test_portfolio_view_reachable():
    ctx, page = _ctx_and_page()
    view = portfolio.build_portfolio_view(ctx, page)
    assert view.route == "/portfolio"


def test_reports_view_reachable():
    ctx, page = _ctx_and_page()
    view = reports.build_reports_view(ctx, page)
    assert view.route == "/reports"
