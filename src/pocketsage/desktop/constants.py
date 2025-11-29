"""Shared desktop constants for options used across forms."""

from __future__ import annotations

# Harmonized account types for account creation/editing and filters.
ACCOUNT_TYPE_OPTIONS: list[tuple[str, str]] = [
    ("checking", "Checking"),
    ("savings", "Savings"),
    ("cash", "Cash"),
    ("credit", "Credit Card"),
    ("loan", "Loan"),
    ("mortgage", "Mortgage"),
    ("investment", "Investment"),
    ("retirement", "Retirement"),
    ("brokerage", "Brokerage"),
    ("crypto", "Crypto"),
    ("business", "Business"),
    ("prepaid", "Prepaid"),
    ("other", "Other"),
]

# Canonical category seed used by quick-add forms and charts.
DEFAULT_CATEGORY_SEED = [
    # Expenses
    {"name": "Groceries", "slug": "groceries", "category_type": "expense", "color": "#4CAF50"},
    {"name": "Dining Out", "slug": "dining-out", "category_type": "expense", "color": "#FF7043"},
    {"name": "Rent", "slug": "rent", "category_type": "expense", "color": "#8D6E63"},
    {"name": "Mortgage", "slug": "mortgage", "category_type": "expense", "color": "#5D4037"},
    {"name": "Utilities", "slug": "utilities", "category_type": "expense", "color": "#29B6F6"},
    {"name": "Internet", "slug": "internet", "category_type": "expense", "color": "#0277BD"},
    {"name": "Phone", "slug": "phone", "category_type": "expense", "color": "#5C6BC0"},
    {"name": "Insurance", "slug": "insurance", "category_type": "expense", "color": "#546E7A"},
    {"name": "Gas", "slug": "gas", "category_type": "expense", "color": "#AB47BC"},
    {"name": "Transit", "slug": "transit", "category_type": "expense", "color": "#7E57C2"},
    {"name": "Medical", "slug": "medical", "category_type": "expense", "color": "#C62828"},
    {"name": "Subscriptions", "slug": "subscriptions", "category_type": "expense", "color": "#6D4C41"},
    {"name": "Gaming", "slug": "gaming", "category_type": "expense", "color": "#9C27B0"},
    {"name": "Clothing", "slug": "clothing", "category_type": "expense", "color": "#8E24AA"},
    {"name": "Gifts", "slug": "gifts", "category_type": "expense", "color": "#D81B60"},
    {"name": "Travel", "slug": "travel", "category_type": "expense", "color": "#00897B"},
    {"name": "Education", "slug": "education", "category_type": "expense", "color": "#039BE5"},
    {"name": "Pets", "slug": "pets", "category_type": "expense", "color": "#6D4C41"},
    {"name": "Household", "slug": "household", "category_type": "expense", "color": "#9E9D24"},
    {"name": "Entertainment", "slug": "entertainment", "category_type": "expense", "color": "#F4511E"},
    {"name": "Coffee", "slug": "coffee", "category_type": "expense", "color": "#795548"},
    {"name": "Wellness", "slug": "wellness", "category_type": "expense", "color": "#8D6E63"},
    {"name": "Childcare", "slug": "childcare", "category_type": "expense", "color": "#F57C00"},
    {"name": "Charity", "slug": "charity", "category_type": "expense", "color": "#AD1457"},
    # Income / transfers
    {"name": "Salary", "slug": "salary", "category_type": "income", "color": "#2E7D32"},
    {"name": "Bonus", "slug": "bonus", "category_type": "income", "color": "#4CAF50"},
    {"name": "Interest", "slug": "interest", "category_type": "income", "color": "#1B5E20"},
    {"name": "Dividends", "slug": "dividends", "category_type": "income", "color": "#00796B"},
    {"name": "Side Hustle", "slug": "side-hustle", "category_type": "income", "color": "#00695C"},
    {"name": "Refund", "slug": "refund", "category_type": "income", "color": "#558B2F"},
    {"name": "Transfer In", "slug": "transfer-in", "category_type": "income", "color": "#00796B"},
    {"name": "Transfer Out", "slug": "transfer-out", "category_type": "expense", "color": "#00838F"},
    {"name": "Payment", "slug": "payment", "category_type": "expense", "color": "#AD1457"},
    {"name": "Rebalance", "slug": "rebalance", "category_type": "income", "color": "#00695C"},
]

# Lookup for default income names to avoid duplicating logic in forms.
DEFAULT_INCOME_CATEGORY_NAMES = {c["name"] for c in DEFAULT_CATEGORY_SEED if c["category_type"] == "income"}
