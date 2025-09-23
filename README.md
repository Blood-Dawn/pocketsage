# PocketSage (Offline Personal Finance & Habits) — Starter Framework
Desktop-first Flask app (runs locally) for **transactions**, **habits**, **liabilities**, optional **portfolio** from CSV.

## Quickstart
1) Python 3.11 + Git
2) Create venv
   - Windows: `python -m venv .venv && .venv\Scripts\activate`
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
3) `pip install -r requirements.txt`
4) `cp .env.example .env` (or copy manually on Windows)
5) `python run.py` → http://127.0.0.1:5000

## URLs
`/ledger`, `/habits`, `/liabilities`, `/portfolio`, `/admin`
