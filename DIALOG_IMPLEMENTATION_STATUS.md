# Dialog Implementation Status

## Overview
PocketSage now has reusable dialog components for all critical CRUD operations. This document tracks implementation status and integration points.

## Completed Dialog Components

### 1. Category Management Dialog (FR-9) ✅
**File**: `src/pocketsage/desktop/components/dialogs/category_dialog.py`

**Features**:
- Create new categories with name, slug, type validation
- Edit existing categories
- Delete categories (with transaction usage check)
- List all categories in searchable/filterable view
- Duplicate slug detection
- Auto-slug generation from name

**Integration Points**:
- Menu bar: Manage > Categories calls `show_category_list_dialog()`
- All CRUD operations accessible from list view

**Status**: ✅ **Complete and integrated**

### 2. Habit Creation Dialog (FR-15) ✅
**File**: `src/pocketsage/desktop/components/dialogs/habit_dialog.py`

**Features**:
- Create new habits with name, description, reminder_time, cadence
- Edit existing habits
- Validation: name required (max 100 chars), HH:MM time format
- Cadence selection: daily, weekly, monthly, yearly

**Integration Points**:
- **TODO**: Replace inline habit dialog in `src/pocketsage/desktop/views/habits.py` with call to `show_habit_dialog()`
- Currently: Habits view has `open_create_dialog()` at line 315 - should be replaced

**Status**: ⚠️ **Dialog created, needs wiring to habits view**

### 3. Budget Creation Dialog (FR-13) ✅
**File**: `src/pocketsage/desktop/components/dialogs/budget_dialog.py`

**Features**:
- Create monthly budget with multiple category allocations
- Add/remove budget lines dynamically
- Edit existing budgets (replaces all lines)
- Shows running total as lines are added
- Prevents duplicate categories in same budget
- Amount validation (must be > 0)

**Integration Points**:
- **TODO**: Replace inline budget dialog in `src/pocketsage/desktop/views/budgets.py` with call to `show_budget_dialog()`
- Currently: Budgets view has `show_create_budget_dialog()` at line 42 - should be replaced

**Status**: ⚠️ **Dialog created, needs wiring to budgets view**

## Architecture Pattern

All dialogs follow this pattern:

```python
def show_{entity}_dialog(
    ctx: AppContext,
    page: ft.Page,
    entity_id: int | None = None,  # None for create, ID for edit
    on_save_callback=None,         # Optional refresh callback
) -> None:
    """Show dialog for creating/editing entity."""
    # 1. Load existing entity if editing
    # 2. Build form controls (TextFields, Dropdowns, etc.)
    # 3. Validate inputs
    # 4. Save to database via ctx.{entity}_repo
    # 5. Show success snackbar
    # 6. Call optional callback
    # 7. Close dialog
```

## Integration Steps

### To Replace Inline Habit Dialog:

1. Open `src/pocketsage/desktop/views/habits.py`
2. Import at top:
   ```python
   from ..components.dialogs import show_habit_dialog
   ```
3. Replace `open_create_dialog()` function (line 315-395) with:
   ```python
   def open_create_dialog(_=None, *, habit: Habit | None = None):
       show_habit_dialog(
           ctx=ctx,
           page=page,
           habit_id=habit.id if habit else None,
           on_save_callback=refresh_view
       )
   ```
4. Remove old dialog code (lines 316-395)

### To Replace Inline Budget Dialog:

1. Open `src/pocketsage/desktop/views/budgets.py`
2. Import at top:
   ```python
   from ..components.dialogs import show_budget_dialog
   ```
3. Replace `show_create_budget_dialog()` function (line 42-115) with:
   ```python
   def show_create_budget_dialog():
       show_budget_dialog(
           ctx=ctx,
           page=page,
           target_month=ctx.current_month,
           on_save_callback=refresh_view
       )
   ```
4. Remove old dialog code (lines 43-115)

## Next Steps

### High Priority
- [ ] Wire habit dialog to habits view (replace inline dialog)
- [ ] Wire budget dialog to budgets view (replace inline dialog)
- [ ] Test all three dialogs end-to-end
- [ ] Add archive/reactivate buttons to habits list (FR-18)

### Medium Priority
- [ ] Create transaction dialog component (consolidate ledger add/edit)
- [ ] Create debt dialog component (consolidate debt CRUD)
- [ ] Create holding dialog component (consolidate portfolio CRUD)
- [ ] Add export folder picker to Reports/Settings views

### Low Priority
- [ ] Add keyboard shortcuts to dialogs (Ctrl+S to save, Esc to cancel)
- [ ] Add tooltips to form fields
- [ ] Improve validation error messages
- [ ] Add loading indicators for slow save operations

## Testing Checklist

### Category Dialog
- [x] Create new category
- [x] Edit existing category
- [x] Delete unused category
- [x] Prevent delete when category has transactions
- [x] Duplicate slug detection
- [x] Auto-slug generation

### Habit Dialog (Pending Integration)
- [ ] Create new habit with all fields
- [ ] Edit existing habit
- [ ] Name validation (required, max length)
- [ ] Time format validation (HH:MM)
- [ ] Cadence dropdown selection

### Budget Dialog (Pending Integration)
- [ ] Create budget for current month
- [ ] Add multiple category lines
- [ ] Remove budget line
- [ ] Edit existing budget
- [ ] Amount validation (> 0)
- [ ] Prevent duplicate categories
- [ ] Show running total

## Known Issues
None currently. Type checker warnings about `page.snack_bar` and `page.dialog` are expected (runtime attributes).

## References
- Requirements: `docs/POCKETSAGE_MASTER_TODO.md`
  - FR-9: Category management (CRITICAL)
  - FR-13: Budget creation (CRITICAL)
  - FR-15: Habit creation (CRITICAL)
  - FR-18: Habit archiving (HIGH)
- Architecture: `docs/FLET_ARCHITECTURE.md`
- Component pattern: `src/pocketsage/desktop/components/dialogs/`
