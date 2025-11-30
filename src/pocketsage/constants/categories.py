"""
Centralized category definitions for all dropdowns across the app.
These categories match the seed data for consistency and comprehensive coverage.
"""

# Transaction Categories - Income
INCOME_CATEGORIES = [
    "Salary",
    "Wages",
    "Freelance",
    "Business Income",
    "Investment Income",
    "Dividends",
    "Interest",
    "Rental Income",
    "Capital Gains",
    "Gift Received",
    "Tax Refund",
    "Bonus",
    "Commission",
    "Royalties",
    "Side Hustle",
    "Refund",
    "Transfer In",
    "Rebalance",
    "Other Income",
]

# Transaction Categories - Expenses
EXPENSE_CATEGORIES = [
    "Rent",
    "Mortgage",
    "Utilities",
    "Electric",
    "Gas Bill",
    "Water",
    "Internet",
    "Phone",
    "Groceries",
    "Dining Out",
    "Coffee",
    "Transportation",
    "Gas",
    "Car Payment",
    "Car Insurance",
    "Car Maintenance",
    "Public Transit",
    "Transit",
    "Parking",
    "Insurance",
    "Health Insurance",
    "Life Insurance",
    "Home Insurance",
    "Healthcare",
    "Medical",
    "Dental",
    "Vision",
    "Pharmacy",
    "Entertainment",
    "Movies",
    "Streaming Services",
    "Gaming",
    "Sports",
    "Hobbies",
    "Shopping",
    "Clothing",
    "Electronics",
    "Home Goods",
    "Subscriptions",
    "Education",
    "Books",
    "Courses",
    "Tuition",
    "Travel",
    "Hotels",
    "Flights",
    "Vacation",
    "Personal Care",
    "Haircut",
    "Gym",
    "Wellness",
    "Gifts",
    "Charity",
    "Donations",
    "Taxes",
    "Federal Tax",
    "State Tax",
    "Property Tax",
    "Debt Payment",
    "Payment",
    "Credit Card Payment",
    "Loan Payment",
    "Student Loan",
    "Childcare",
    "Pet Care",
    "Pets",
    "Home Maintenance",
    "Home Improvement",
    "Household",
    "Bank Fees",
    "ATM Fees",
    "Late Fees",
    "Transfer Out",
    "Other Expense",
]

# All transaction categories combined
ALL_TRANSACTION_CATEGORIES = ["All"] + INCOME_CATEGORIES + EXPENSE_CATEGORIES

# Transaction Types
TRANSACTION_TYPES = [
    "Income",
    "Expense",
    "Transfer",
]

# Budget Categories (subset of expenses that are commonly budgeted)
BUDGET_CATEGORIES = [
    "Rent",
    "Mortgage",
    "Utilities",
    "Groceries",
    "Dining Out",
    "Transportation",
    "Gas",
    "Car Payment",
    "Insurance",
    "Healthcare",
    "Entertainment",
    "Shopping",
    "Subscriptions",
    "Personal Care",
    "Gifts",
    "Education",
    "Travel",
    "Childcare",
    "Pet Care",
    "Savings Goal",
    "Emergency Fund",
    "Other",
]

# Habit Frequencies
HABIT_FREQUENCIES = [
    "Daily",
    "Weekly",
    "Monthly",
]

# Habit Categories
HABIT_CATEGORIES = [
    "Health",
    "Fitness",
    "Finance",
    "Productivity",
    "Learning",
    "Social",
    "Mindfulness",
    "Creativity",
    "Self-Care",
    "Other",
]

# Portfolio Asset Classes
ASSET_CLASSES = [
    "Stocks",
    "ETFs",
    "Mutual Funds",
    "Bonds",
    "Crypto",
    "Real Estate",
    "Commodities",
    "Cash",
    "Other",
]

# Portfolio Account Types
PORTFOLIO_ACCOUNT_TYPES = [
    "Brokerage",
    "401(k)",
    "IRA",
    "Roth IRA",
    "HSA",
    "529",
    "Other",
]


def get_category_dropdown_options(include_all: bool = False) -> list:
    """
    Get category options formatted for Flet dropdown with income and expense sections.

    Args:
        include_all: If True, includes an "All" option at the top

    Returns:
        List of Flet dropdown options with category sections
    """
    try:
        import flet as ft
    except ImportError:
        # Fallback for non-Flet contexts
        options = []
        if include_all:
            options.append("All")
        options.extend(INCOME_CATEGORIES)
        options.extend(EXPENSE_CATEGORIES)
        return options

    options = []
    if include_all:
        options.append(ft.dropdown.Option("All"))

    # Income section
    options.append(ft.dropdown.Option("--- INCOME ---", disabled=True))
    for cat in INCOME_CATEGORIES:
        options.append(ft.dropdown.Option(cat))

    # Expense section
    options.append(ft.dropdown.Option("--- EXPENSES ---", disabled=True))
    for cat in EXPENSE_CATEGORIES:
        options.append(ft.dropdown.Option(cat))

    return options


def get_simple_category_list(include_all: bool = False) -> list[str]:
    """
    Get a simple list of category names without Flet formatting.

    Args:
        include_all: If True, includes "All" at the beginning

    Returns:
        List of category name strings
    """
    categories = []
    if include_all:
        categories.append("All")
    categories.extend(INCOME_CATEGORIES)
    categories.extend(EXPENSE_CATEGORIES)
    return categories


def is_income_category(category_name: str) -> bool:
    """Check if a category name is an income category."""
    return category_name in INCOME_CATEGORIES


def is_expense_category(category_name: str) -> bool:
    """Check if a category name is an expense category."""
    return category_name in EXPENSE_CATEGORIES
