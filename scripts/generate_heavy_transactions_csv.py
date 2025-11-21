"""
Generate a heavy 10-year transaction CSV for PocketSage testing.

Output file:
    pocketsage_10y_heavy_transactions.csv
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


def main() -> None:
    # ---- Config ----
    start_date = datetime(2015, 1, 1)
    end_date = datetime(2025, 1, 1)

    accounts = [
        "Checking",
        "Savings",
        "Credit Card - Sapphire",
        "Credit Card - CashBack",
        "Brokerage",
    ]

    income_categories = ["Salary", "Bonus", "Interest", "Dividends", "Refund"]
    expense_categories = [
        "Groceries",
        "Dining Out",
        "Rent",
        "Utilities",
        "Internet",
        "Phone",
        "Gas",
        "Transit",
        "Medical",
        "Subscriptions",
        "Gaming",
        "Clothing",
        "Gifts",
        "Travel",
        "Education",
        "Pets",
        "Household",
        "Entertainment",
    ]
    transfer_categories = ["Transfer In", "Transfer Out", "Payment", "Rebalance"]

    merchants = [
        "Amazon",
        "Walmart",
        "Target",
        "Steam",
        "Netflix",
        "Spotify",
        "Hulu",
        "Uber",
        "Lyft",
        "Publix",
        "Aldi",
        "Costco",
        "Shell",
        "Chevron",
        "Local Cafe",
        "Electric Co",
        "Water & Sewer",
        "Mobile Carrier",
        "Gym",
        "Bookstore",
        "Pharmacy",
        "Airline",
        "Hotel",
        "GameStop",
    ]

    # ---- State ----
    rows: list[dict[str, str]] = []
    current_date = start_date
    txn_id = 1

    # Start each account with a random base balance
    balance_by_account: dict[str, float] = {
        acc: random.uniform(500, 4000) for acc in accounts
    }

    # ---- Generate rows ----
    while current_date < end_date:
        # 0–6 transactions per day
        num_txn_today = random.randint(0, 6)

        for _ in range(num_txn_today):
            roll = random.random()

            if roll < 0.15:
                txn_type = "income"
                category = random.choice(income_categories)
                amount = round(random.uniform(200, 3000), 2)
            elif roll < 0.75:
                txn_type = "expense"
                category = random.choice(expense_categories)
                amount = round(-random.uniform(5, 400), 2)
            else:
                txn_type = "transfer"
                category = random.choice(transfer_categories)
                amount = round(random.uniform(50, 1500), 2)

            account = random.choice(accounts)
            merchant = random.choice(merchants)

            # Transfers: randomly make them positive or negative
            if txn_type == "transfer" and random.random() < 0.5:
                amount = -amount

            balance_by_account[account] += amount
            running_balance = round(balance_by_account[account], 2)

            description = f"{category} - {merchant}"

            if txn_type == "income":
                tags = "income,recurring" if category == "Salary" else "income"
            elif txn_type == "expense":
                if category in ["Rent", "Utilities", "Internet", "Phone", "Subscriptions"]:
                    tags = "bill,recurring"
                else:
                    tags = "discretionary"
            else:
                tags = "transfer"

            rows.append(
                {
                    "id": str(txn_id),
                    "date": current_date.strftime("%Y-%m-%d"),
                    "account_name": account,
                    "transaction_type": txn_type,
                    "category": category,
                    "description": description,
                    "merchant": merchant,
                    "amount": f"{amount:.2f}",
                    "running_balance": f"{running_balance:.2f}",
                    "tags": tags,
                    "cleared": random.choice(["yes", "no"]),
                    "notes": "",
                }
            )

            txn_id += 1

        current_date += timedelta(days=1)

    # ---- Write CSV ----
    out_path = Path("pocketsage_10y_heavy_transactions.csv")

    fieldnames = [
        "id",
        "date",
        "account_name",
        "transaction_type",
        "category",
        "description",
        "merchant",
        "amount",
        "running_balance",
        "tags",
        "cleared",
        "notes",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows → {out_path.resolve()}")


if __name__ == "__main__":
    main()
