PYTHON ?= python
PIP ?= $(PYTHON) -m pip
ENV ?= .venv

.PHONY: setup dev test lint package demo-seed

setup:
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	pre-commit install
	# TODO(@devops): add SQLCipher installation guidance per platform.

dev:
	$(PYTHON) run_desktop.py

test:
	pytest
	# TODO(@qa-team): remove skips as features land.

lint:
	ruff check .
	black --check .
	# TODO(@devops): integrate mypy once models stabilized.

package:
	flet pack run_desktop.py \
		--name "PocketSage" \
		--product-name "PocketSage" \
		--product-version "0.1.0" \
		--file-description "Offline Finance & Habit Tracker"

demo-seed:
	$(PYTHON) scripts/seed_demo.py
	# TODO(@admin-squad): ensure idempotent seeding + sample data coverage.
