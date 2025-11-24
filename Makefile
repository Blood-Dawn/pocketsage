PYTHON ?= python
PIP ?= $(PYTHON) -m pip
ENV ?= .venv

.PHONY: setup dev test lint package demo-seed

setup:
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	pre-commit install

dev:
	$(PYTHON) run_desktop.py

test:
	pytest

lint:
	ruff check .
	black --check .

package:
	flet pack run_desktop.py \
		--name "PocketSage" \
		--product-name "PocketSage" \
		--product-version "0.1.0" \
		--file-description "Offline Finance & Habit Tracker" \
		--delete-build

demo-seed:
	$(PYTHON) scripts/seed_demo.py
