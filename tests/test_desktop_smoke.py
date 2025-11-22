from __future__ import annotations

import os
import tempfile

import flet as ft

# Ensure icon namespace exists for view builders in headless mode.
if not hasattr(ft, "icons"):
    try:
        from flet import icons as flet_icons  # type: ignore

        ft.icons = flet_icons  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover

        class _IconsStub:
            def __getattr__(self, name):
                return name

        ft.icons = _IconsStub()  # type: ignore[attr-defined]

if not hasattr(ft, "colors"):

    class _ColorsStub:
        def __getattr__(self, name):
            return name

    ft.colors = _ColorsStub()  # type: ignore[attr-defined]
from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.navigation import Router
from pocketsage.desktop.views import (
    admin,
    budgets,
    dashboard,
    debts,
    habits,
    help as help_view,
    ledger,
    portfolio,
    reports,
    settings,
)
from pocketsage.services import auth


class DummyPage:
    """Minimal stand-in for flet.Page used in view builders and router tests."""

    def __init__(self):
        self.views: list[ft.View] = []
        self.route: str = ""
        self.snack_bar = None
        self.overlay: list[ft.Control] = []

    def go(self, route: str):
        self.route = route

    def update(self):
        return None

    # hook attributes accessed by AppBar / NavRail
    padding = 0
    window_width = 1280
    window_height = 800
    window_min_width = 1024
    window_min_height = 600
    theme_mode = ft.ThemeMode.DARK


def _ensure_user(ctx):
    if not auth.any_users_exist(ctx.session_factory):
        user = auth.create_user(
            username="smoke-admin",
            password="password",
            role="admin",
            session_factory=ctx.session_factory,
        )
    else:
        user = auth.list_users(ctx.session_factory)[0]
    ctx.current_user = user
    return user


def _build_views():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    os.environ["POCKETSAGE_DATABASE_URL"] = f"sqlite:///{tmp.name}"
    ctx = create_app_context()
    _ensure_user(ctx)
    page = DummyPage()
    builders = [
        dashboard.build_dashboard_view,
        ledger.build_ledger_view,
        budgets.build_budgets_view,
        habits.build_habits_view,
        debts.build_debts_view,
        portfolio.build_portfolio_view,
        reports.build_reports_view,
        settings.build_settings_view,
        help_view.build_help_view,
        admin.build_admin_view,
    ]
    return ctx, page, builders


def test_view_builders_render():
    """Each view builder should return a View without raising."""
    ctx, page, builders = _build_views()
    for build in builders:
        view = build(ctx, page)  # type: ignore[arg-type]
        assert isinstance(view, ft.View)
        assert view.route


def test_router_register_and_route_change():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    os.environ["POCKETSAGE_DATABASE_URL"] = f"sqlite:///{tmp.name}"
    ctx = create_app_context()
    _ensure_user(ctx)
    page = DummyPage()
    router = Router(page, ctx)

    def sample_builder(_, __):
        return ft.View(route="/sample", controls=[])

    router.register("/sample", sample_builder)
    router.route_change(type("Evt", (), {"route": "/sample"}))

    assert page.views
    assert page.views[0].route == "/sample"


def test_main_entrypoint_runs(monkeypatch):
    """Ensure desktop entrypoint registers target without launching window."""
    captured = {}

    def fake_app(target):
        captured["target"] = target
        return None

    monkeypatch.setattr(ft, "app", fake_app)
    from pocketsage.desktop import app as app_module

    app_module.ft.app(target=app_module.main)
    assert captured.get("target") == app_module.main
