"""Tests for the desktop navigation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from pocketsage.desktop.navigation_helpers import (
    handle_navigation_selection,
    index_for_route,
    nav_routes,
    resolve_shortcut_route,
    route_for_index,
)


@dataclass
class _PageSpy:
    """Minimal fake page that records navigation actions."""

    navigated_to: list[str] = field(default_factory=list)

    def go(self, route: str) -> None:
        self.navigated_to.append(route)


def test_navigation_selection_drives_page_route() -> None:
    """Selecting a navigation index pushes the expected route."""

    page = _PageSpy()

    handle_navigation_selection(page, 2)

    assert page.navigated_to == ["/budgets"]


def test_navigation_selection_for_habits() -> None:
    """Navigation index for habits routes correctly."""

    page = _PageSpy()

    handle_navigation_selection(page, 3)

    assert page.navigated_to == ["/habits"]


def test_navigation_selection_out_of_bounds_does_nothing() -> None:
    """Out-of-range indexes do not trigger navigation."""

    page = _PageSpy()

    handle_navigation_selection(page, 99)

    assert page.navigated_to == []


def test_index_and_route_round_trip() -> None:
    """Every navigation route resolves back to itself via the helpers."""

    for index, route in enumerate(nav_routes()):
        assert route_for_index(index) == route
        assert index_for_route(route) == index

    assert index_for_route("/something-unknown") == 0


def test_shortcut_resolution() -> None:
    """Keyboard shortcuts resolve to the routes consumed by the router."""

    assert resolve_shortcut_route("n", True, False) == "/ledger"
    assert resolve_shortcut_route("h", True, True) == "/habits"
    assert resolve_shortcut_route("1", True, False) == "/dashboard"
    assert resolve_shortcut_route("7", True, False) == "/settings"
    assert resolve_shortcut_route("5", False, False) is None
