"""Reusable UI components for the desktop app."""

from .dialogs import show_confirm_dialog, show_error_dialog
from .layout import build_app_bar, build_main_layout, build_navigation_rail
from .widgets import build_card, build_progress_bar, build_stat_card, empty_state

__all__ = [
    "build_app_bar",
    "build_navigation_rail",
    "build_main_layout",
    "show_error_dialog",
    "show_confirm_dialog",
    "build_card",
    "build_stat_card",
    "build_progress_bar",
    "empty_state",
]
