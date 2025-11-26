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
    def collect_fields(control):
        # Recursively collect fields from any control with 'controls' attribute
        if hasattr(control, "controls"):
            for c in control.controls:
                collect_fields(c)
        # Also check for fields inside 'content' attribute (for e.g. RadioGroup)
        if hasattr(control, "content") and hasattr(control.content, "controls"):
            for c in control.content.controls:
                collect_fields(c)
        if hasattr(control, "label"):
            fields.append((control.label, getattr(control, "value", None)))
    if hasattr(dialog, "content") and hasattr(dialog.content, "content"):
        collect_fields(dialog.content.content)
    return title, fields

def test_add_popup_transaction():
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 18 + "ADD POPUP UI TEST" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝\n")
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
    required = ["Date *", "Amount *", "Account *", "Category", "Description *", "Notes (optional)"]
    for req in required:
        assert req in [label for label, _ in fields], f"Missing field: {req}"
    print("✓ Transaction Add popup shows correct fields")

def test_add_popup_account():
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 18 + "ADD POPUP UI TEST" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝\n")
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
    required = ["Account Name *", "Account Type *", "Initial Balance"]
    for req in required:
        assert req in [label for label, _ in fields], f"Missing field: {req}"
    print("✓ Account Add popup shows correct fields")

def test_add_popup_category():
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 18 + "ADD POPUP UI TEST" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝\n")
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
    required = ["Category Name *", "Slug (optional)"]
    for req in required:
        assert req in [label for label, _ in fields], f"Missing field: {req}"
    # Check for Type label and radio options
    # The Type label is a Text control, not a field, so we check for it in the dialog content
    dialog_content = getattr(page.dialog, "content", None)
    found_type_label = False
    found_expense_radio = False
    found_income_radio = False
    if hasattr(dialog_content, "controls"):
        for control in dialog_content.controls:
            if getattr(control, "value", None) == "Type:":
                found_type_label = True
            if hasattr(control, "content") and hasattr(control.content, "controls"):
                for radio in control.content.controls:
                    if getattr(radio, "label", None) == "Expense":
                        found_expense_radio = True
                    if getattr(radio, "label", None) == "Income":
                        found_income_radio = True
    assert found_type_label, "Missing Type label"
    assert found_expense_radio, "Missing Expense radio option"
    assert found_income_radio, "Missing Income radio option"
    print("✓ Category Add popup shows correct fields")

def test_add_popup_habit():
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 18 + "ADD POPUP UI TEST" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝\n")
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
    required = ["Habit Name *"]
    for req in required:
        assert req in [label for label, _ in fields], f"Missing field: {req}"
    print("✓ Habit Add popup shows correct fields")

def test_add_popup_budget():
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 18 + "ADD POPUP UI TEST" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝\n")
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
    required = ["Budget Name *"]
    for req in required:
        assert req in [label for label, _ in fields], f"Missing field: {req}"
    print("✓ Budget Add popup shows correct fields")

def main():
    test_add_popup_transaction()
    test_add_popup_account()
    test_add_popup_category()
    test_add_popup_habit()
    test_add_popup_budget()
    print("\n🎉 All Add popup UI tests passed!")

if __name__ == "__main__":
    main()
