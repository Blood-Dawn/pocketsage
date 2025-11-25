"""Category management dialogs (FR-9).

Implements full CRUD for categories with validation:
- Create new category
- Edit existing category
- Delete category (with usage check)
- List all categories with actions
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ....logging_config import get_logger
from ....models.category import Category

if TYPE_CHECKING:
    from ...context import AppContext

logger = get_logger(__name__)


def show_category_dialog(
    ctx: AppContext,
    page: ft.Page,
    category: Category | None = None,
    on_save_callback=None,
) -> None:
    """Show create or edit category dialog.

    Args:
        ctx: Application context
        page: Flet page
        category: Existing category to edit, or None to create new
        on_save_callback: Optional callback function to call after successful save
    """
    is_edit = category is not None
    uid = ctx.require_user_id()

    # Form fields
    name_field = ft.TextField(
        label="Category Name *",
        value=category.name if category else "",
        hint_text="e.g., Groceries, Rent, Salary",
        autofocus=True,
        width=400,
    )

    type_field = ft.RadioGroup(
        value=category.category_type if category else "expense",
        content=ft.Row(
            controls=[
                ft.Radio(value="expense", label="Expense"),
                ft.Radio(value="income", label="Income"),
            ],
            spacing=20,
        ),
    )

    slug_field = ft.TextField(
        label="Slug (optional)",
        value=category.slug if category else "",
        hint_text="Auto-generated from name if empty",
        width=400,
    )

    def _generate_slug(name: str) -> str:
        """Generate URL-friendly slug from name."""
        return name.lower().replace(" ", "-").replace("_", "-")

    def _validate_and_save(_):
        """Validate form and save category."""
        # Clear previous errors
        name_field.error_text = None
        slug_field.error_text = None

        # Validate name
        name = (name_field.value or "").strip()
        if not name:
            name_field.error_text = "Name is required"
            name_field.update()
            return

        # Generate slug if empty
        slug = (slug_field.value or "").strip()
        if not slug:
            slug = _generate_slug(name)

        # Check for duplicate slug (excluding current category if editing)
        existing = None
        try:
            all_categories = ctx.category_repo.list_all(user_id=uid)
            for cat in all_categories:
                if cat.slug == slug and (not is_edit or cat.id != category.id):
                    existing = cat
                    break
        except Exception as exc:
            logger.error(f"Failed to check for duplicate slug: {exc}")

        if existing:
            slug_field.error_text = f"Slug '{slug}' already exists"
            slug_field.update()
            return

        # Save category
        try:
            if is_edit:
                # Update existing
                category.name = name
                category.slug = slug
                category.category_type = type_field.value
                updated = ctx.category_repo.update(category, user_id=uid)
                logger.info(f"Category updated: {updated.name}")
                message = f"Category '{name}' updated"
            else:
                # Create new
                new_category = Category(
                    name=name,
                    slug=slug,
                    category_type=type_field.value,
                    user_id=uid,
                )
                created = ctx.category_repo.create(new_category, user_id=uid)
                logger.info(f"Category created: {created.name}")
                message = f"Category '{name}' created"

            # Close dialog
            dialog.open = False
            page.dialog = None
            page.update()

            # Show success message
            page.snack_bar = ft.SnackBar(content=ft.Text(message))
            page.snack_bar.open = True
            page.update()

            # Call callback if provided
            if on_save_callback:
                on_save_callback()

        except Exception as exc:
            logger.error(f"Failed to save category: {exc}", exc_info=True)
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Failed to save: {exc}"),
                bgcolor=ft.Colors.ERROR,
            )
            page.snack_bar.open = True
            page.update()

    def _close_dialog(_):
        """Close the dialog without saving."""
        dialog.open = False
        page.dialog = None
        page.update()

    # Build dialog
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit Category" if is_edit else "New Category"),
        content=ft.Column(
            controls=[
                ft.Text(
                    "Categories help organize your transactions and budgets.",
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Divider(),
                name_field,
                ft.Text("Type:", weight=ft.FontWeight.BOLD),
                type_field,
                slug_field,
                ft.Text(
                    "Slug is used internally for unique identification.",
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    italic=True,
                ),
            ],
            tight=True,
            spacing=12,
            width=450,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=_close_dialog),
            ft.FilledButton("Save", on_click=_validate_and_save),
        ],
    )

    page.dialog = dialog
    dialog.open = True
    page.update()


def show_category_list_dialog(ctx: AppContext, page: ft.Page) -> None:
    """Show list of all categories with edit/delete actions.

    This provides a management interface for all categories.
    """
    uid = ctx.require_user_id()

    # Category list container (will be updated)
    category_list_ref = ft.Ref[ft.Column]()

    def _load_categories():
        """Load and display categories."""
        try:
            categories = ctx.category_repo.list_all(user_id=uid)

            # Group by type
            income_cats = [c for c in categories if c.category_type == "income"]
            expense_cats = [c for c in categories if c.category_type == "expense"]

            controls = []

            # Income section
            if income_cats:
                controls.append(
                    ft.Text("Income Categories", size=14, weight=ft.FontWeight.BOLD)
                )
                for cat in income_cats:
                    controls.append(_build_category_row(cat))
                controls.append(ft.Divider())

            # Expense section
            if expense_cats:
                controls.append(
                    ft.Text("Expense Categories", size=14, weight=ft.FontWeight.BOLD)
                )
                for cat in expense_cats:
                    controls.append(_build_category_row(cat))

            if not controls:
                controls.append(
                    ft.Text(
                        "No categories yet. Create one to get started!",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    )
                )

            if category_list_ref.current:
                category_list_ref.current.controls = controls
                category_list_ref.current.update()

        except Exception as exc:
            logger.error(f"Failed to load categories: {exc}", exc_info=True)
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Failed to load categories: {exc}"),
                bgcolor=ft.Colors.ERROR,
            )
            page.snack_bar.open = True
            page.update()

    def _build_category_row(cat: Category) -> ft.Control:
        """Build a row for a single category."""

        def _edit_category(_):
            """Open edit dialog for this category."""
            show_category_dialog(ctx, page, category=cat, on_save_callback=_load_categories)

        def _delete_category(_):
            """Delete this category after confirmation."""
            # Check if category is in use
            try:
                transactions = ctx.transaction_repo.list_by_category(
                    cat.id, user_id=uid
                )
                if transactions:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(
                            f"Cannot delete '{cat.name}': {len(transactions)} transactions use this category"
                        ),
                        bgcolor=ft.Colors.WARNING,
                    )
                    page.snack_bar.open = True
                    page.update()
                    return

                # Show confirmation dialog
                def _confirm_delete(_):
                    try:
                        ctx.category_repo.delete(cat.id, user_id=uid)
                        logger.info(f"Category deleted: {cat.name}")

                        # Close confirmation dialog
                        confirm_dialog.open = False
                        page.dialog = None

                        # Reload list
                        _load_categories()

                        # Show success
                        page.snack_bar = ft.SnackBar(
                            content=ft.Text(f"Category '{cat.name}' deleted")
                        )
                        page.snack_bar.open = True
                        page.update()

                    except Exception as exc:
                        logger.error(f"Failed to delete category: {exc}", exc_info=True)
                        page.snack_bar = ft.SnackBar(
                            content=ft.Text(f"Failed to delete: {exc}"),
                            bgcolor=ft.Colors.ERROR,
                        )
                        page.snack_bar.open = True
                        page.update()

                def _cancel_delete(_):
                    confirm_dialog.open = False
                    page.dialog = None
                    page.update()

                confirm_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Delete Category"),
                    content=ft.Text(
                        f"Are you sure you want to delete '{cat.name}'?\n\n"
                        "This action cannot be undone."
                    ),
                    actions=[
                        ft.TextButton("Cancel", on_click=_cancel_delete),
                        ft.FilledButton(
                            "Delete",
                            on_click=_confirm_delete,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.ERROR,
                                color=ft.Colors.ON_ERROR,
                            ),
                        ),
                    ],
                )

                page.dialog = confirm_dialog
                confirm_dialog.open = True
                page.update()

            except Exception as exc:
                logger.error(f"Failed to check category usage: {exc}", exc_info=True)
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Error: {exc}"),
                    bgcolor=ft.Colors.ERROR,
                )
                page.snack_bar.open = True
                page.update()

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.CATEGORY,
                        color=ft.Colors.PRIMARY if cat.category_type == "expense" else ft.Colors.GREEN,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(cat.name, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                f"{cat.slug} • {cat.category_type}",
                                size=11,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        tooltip="Edit category",
                        on_click=_edit_category,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        tooltip="Delete category",
                        icon_color=ft.Colors.ERROR,
                        on_click=_delete_category,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=8,
            border_radius=8,
            bgcolor=ft.Colors.SURFACE_VARIANT,
        )

    def _add_new_category(_):
        """Open dialog to create new category."""
        show_category_dialog(ctx, page, on_save_callback=_load_categories)

    def _close_list(_):
        """Close the list dialog."""
        dialog.open = False
        page.dialog = None
        page.update()

    # Build list dialog
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Text("Manage Categories"),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.ADD,
                    tooltip="Add new category",
                    on_click=_add_new_category,
                ),
            ],
        ),
        content=ft.Container(
            content=ft.Column(
                ref=category_list_ref,
                controls=[],
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=500,
            height=400,
        ),
        actions=[
            ft.TextButton("Close", on_click=_close_list),
        ],
    )

    page.dialog = dialog
    dialog.open = True
    page.update()

    # Load categories after dialog is shown
    _load_categories()
