"""Reusable UI components for the desktop app."""

from .layout import build_app_bar, build_navigation_rail, build_main_layout
from .dialogs import show_error_dialog, show_confirm_dialog
from .widgets import build_card, build_stat_card, build_progress_bar

__all__ = [
    "build_app_bar",
    "build_navigation_rail",
    "build_main_layout",
    "show_error_dialog",
    "show_confirm_dialog",
    "build_card",
    "build_stat_card",
    "build_progress_bar",
]
