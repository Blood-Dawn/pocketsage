PYTHON ?= python
PIP ?= $(PYTHON) -m pip
FLASK_APP ?= pocketsage
ENV ?= .venv

.PHONY: setup dev test lint package demo-seed

setup:
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	pre-commit install
	# TODO(@devops): add SQLCipher installation guidance per platform.

dev:
	FLASK_ENV=development $(PYTHON) run.py
	# TODO(@devops): consider `flask --app pocketsage --debug run` once CLI wiring exists.

test:
	pytest
	# TODO(@qa-team): remove skips as features land.

lint:
	ruff check .
	black --check .
	# TODO(@devops): integrate mypy once models stabilized.


package:
	@if [ ! -f PocketSage.spec ]; then \
		echo "PocketSage.spec is missing. Restore it from version control or regenerate with 'pyinstaller run.py --name PocketSage --specpath .'"; \
		exit 1; \
	fi
	pyinstaller PocketSage.spec --clean
	# TODO(@release): customize spec and add post-build smoke test.

demo-seed:
	$(PYTHON) scripts/seed_demo.py
	# TODO(@admin-squad): ensure idempotent seeding + sample data coverage.
