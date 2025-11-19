#!/usr/bin/env python
"""Desktop app entrypoint for PocketSage."""

import flet as ft
from pocketsage.desktop.app import main

if __name__ == "__main__":
    ft.app(target=main)
