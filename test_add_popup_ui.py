"""Robust test for Add Popup UI functionality.

Verifies that pressing any Add button (transaction, account, category, habit, budget) opens the correct dialog with the expected fields and categories.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pocketsage.desktop.components.dialogs import (
    show_account_dialog,
    show_budget_dialog,
    show_category_dialog,
    show_habit_dialog,
    show_transaction_dialog,
)
from pocketsage.desktop.context import create_app_context
from pocketsage.models.user import User


class MockPage:
    def __init__(self):
        self.dialog = None
        self.snack_bar = None
        self.route = "/dashboard"
        self.last_dialog_title = None
        self.last_fields = []
    def update(self):
        pass
    def go(self, route):
        self.route = route
    def destroy(self):
        pass

# Helper to extract dialog info

def extract_dialog_info(dialog):
    title = getattr(dialog, "title", None)
    if hasattr(title, "value"):
        title = title.value
    fields = []
    if hasattr(dialog, "content") and hasattr(dialog.content, "content"):
        col = dialog.content.content
        if hasattr(col, "controls"):
            for control in col.controls:
                if hasattr(control, "label") and hasattr(control, "value"):
                    fields.append((control.label, control.value))
                elif hasattr(control, "label"):
                    fields.append((control.label, None))
    return title, fields

def test_add_popup_transaction():
    ctx = create_app_context()
    ctx.current_user = User(id=1, username="testuser", email="test@example.com", role="admin")
    page = MockPage()
    show_transaction_dialog(ctx, page)
    dialog = page.dialog
    title, fields = extract_dialog_info(dialog)
    print(f"Transaction dialog title: {title}")
    print("Fields:")
    for label, value in fields:
        print(f"  • {label}")
    assert "Date *" in [label for label, _ in fields]
    assert "Amount *" in [label for label, _ in fields]
    assert "Account *" in [label for label, _ in fields]
    assert "Category" in [label for label, _ in fields]
    print("✓ Transaction Add popup shows correct fields")

def test_add_popup_account():
    ctx = create_app_context()
    ctx.current_user = User(id=1, username="testuser", email="test@example.com", role="admin")
    page = MockPage()
    show_account_dialog(ctx, page)
    dialog = page.dialog
    title, fields = extract_dialog_info(dialog)
    print(f"Account dialog title: {title}")
    print("Fields:")
    for label, value in fields:
        print(f"  • {label}")
    assert "Account Name *" in [label for label, _ in fields]
    assert "Account Type *" in [label for label, _ in fields]
    assert "Initial Balance" in [label for label, _ in fields]
    print("✓ Account Add popup shows correct fields")

def test_add_popup_category():
    ctx = create_app_context()
    ctx.current_user = User(id=1, username="testuser", email="test@example.com", role="admin")
    page = MockPage()
    show_category_dialog(ctx, page)
    dialog = page.dialog
    title, fields = extract_dialog_info(dialog)
    print(f"Category dialog title: {title}")
    print("Fields:")
    for label, value in fields:
        print(f"  • {label}")
    assert "Category Name *" in [label for label, _ in fields]
    assert "Slug (optional)" in [label for label, _ in fields]
    print("✓ Category Add popup shows correct fields")

def test_add_popup_habit():
    ctx = create_app_context()
    ctx.current_user = User(id=1, username="testuser", email="test@example.com", role="admin")
    page = MockPage()
    show_habit_dialog(ctx, page)
    dialog = page.dialog
    title, fields = extract_dialog_info(dialog)
    print(f"Habit dialog title: {title}")
    print("Fields:")
    for label, value in fields:
        print(f"  • {label}")
    assert "Habit Name *" in [label for label, _ in fields]
    print("✓ Habit Add popup shows correct fields")

def test_add_popup_budget():
    ctx = create_app_context()
    ctx.current_user = User(id=1, username="testuser", email="test@example.com", role="admin")
    page = MockPage()
    show_budget_dialog(ctx, page)
    dialog = page.dialog
    title, fields = extract_dialog_info(dialog)
    print(f"Budget dialog title: {title}")
    print("Fields:")
    for label, value in fields:
        print(f"  • {label}")
    assert "Budget Name *" in [label for label, _ in fields]
    print("✓ Budget Add popup shows correct fields")

def main():
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 18 + "ADD POPUP UI TEST" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝\n")
    test_add_popup_transaction()
    test_add_popup_account()
    test_add_popup_category()
    test_add_popup_habit()
    test_add_popup_budget()
    print("\n🎉 All Add popup UI tests passed!")

if __name__ == "__main__":
    main()
