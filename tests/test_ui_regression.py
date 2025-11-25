from __future__ import annotations

import os
import tempfile
from typing import Callable

import flet as ft
import pytest

from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.views import debts, habits, ledger, portfolio, reports
from pocketsage.services import auth


class DummyPage:
    """Minimal stand-in for flet.Page used in view builders."""

    def __init__(self):
        self.views: list[ft.View] = []
        self.route: str = ""
        self.snack_bar = None
        self.overlay: list[ft.Control] = []

    def go(self, route: str):
        self.route = route

    def update(self):
        return None

    padding = 0
    window_width = 1280
    window_height = 800
    window_min_width = 1024
    window_min_height = 600
    theme_mode = ft.ThemeMode.DARK


def _ensure_user(ctx):
    if not auth.any_users_exist(ctx.session_factory):
        user = auth.create_user(
            username="ui-regression",
            password="password",
            role="admin",
            session_factory=ctx.session_factory,
        )
    else:
        user = auth.list_users(ctx.session_factory)[0]
    ctx.current_user = user
    return user


def _ctx_and_page():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    os.environ["POCKETSAGE_DATABASE_URL"] = f"sqlite:///{tmp.name}"
    ctx = create_app_context()
    _ensure_user(ctx)
    page = DummyPage()
    return ctx, page


def _find_control(root: ft.Control, predicate: Callable[[ft.Control], bool]) -> ft.Control | None:
    """DFS to locate a control matching predicate."""
    stack = [root]
    seen = set()
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

        for attr in ("controls", "content", "leading", "trailing", "title", "subtitle", "actions"):
            child = getattr(control, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                stack.extend(child)
            else:
                stack.append(child)
    return None


@pytest.mark.parametrize(
    "builder, button_text",
    [
        (ledger.build_ledger_view, "Add transaction"),
        (habits.build_habits_view, "Add habit"),
        (debts.build_debts_view, "Add liability"),
        (portfolio.build_portfolio_view, "Add holding"),
    ],
)
def test_primary_dialog_buttons_clickable(builder, button_text):
    ctx, page = _ctx_and_page()
    view = builder(ctx, page)  # type: ignore[arg-type]
    target = _find_control(
        view,
        lambda c: isinstance(c, ft.FilledButton) and button_text in getattr(c, "text", ""),
    )
    assert target is not None, f"{button_text} not found"
    # Should not raise when triggering the handler
    if target.on_click:
        target.on_click(None)


def test_reports_download_buttons_clickable():
    ctx, page = _ctx_and_page()
    view = reports.build_reports_view(ctx, page)
    downloads = []
    target = _find_control(
        view,
        lambda c: isinstance(c, ft.FilledTonalButton)
        and getattr(c, "text", "") == "Download"
    )
    downloads.append(target)
    assert any(d is not None for d in downloads)
    for btn in downloads:
        if btn and btn.on_click:
            btn.on_click(None)
