#!/usr/bin/env python
"""Desktop app entrypoint for PocketSage with verbose console logging enabled."""

import logging
import os
import sys

# Force dev mode with verbose logging
os.environ["POCKETSAGE_DEV_MODE"] = "true"

# Set up console logging before importing anything else
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)-8s [%(name)s:%(lineno)d] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout
)

# Add a banner
print("=" * 80)
print("PocketSage - VERBOSE DEV MODE")
print("All button clicks, dialog operations, and errors will be logged below")
print("=" * 80)
print()

import flet as ft
from pocketsage.desktop.app import main

if __name__ == "__main__":
    ft.app(target=main)
