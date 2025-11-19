#!/usr/bin/env python
"""Desktop app entrypoint for PocketSage."""

import flet as ft

from src.pocketsage.desktop.app import main

if __name__ == "__main__":
    ft.app(target=main)
