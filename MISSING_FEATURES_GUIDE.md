# PocketSage Missing Features Implementation Guide

## Overview

This document tracks the features identified in the requirements but not yet implemented in the desktop app. Each feature includes FR (Functional Requirement) references, current state, and implementation steps.

## High Priority - Core Feature Gaps

### 1. Category Management UI (FR-9) ⚠️ CRITICAL

**Current State:** 
- Categories exist in database
- Ledger uses categories in dropdowns
- NO UI to add/edit/delete categories
- Menu item shows placeholder

**Requirements:**
- FR-9: "Manage categories (CRUD interface & persistence)"
- NFR-17: "Clear validation error messages on forms"

**Implementation Steps:**

1. Create `src/pocketsage/desktop/components/dialogs/category_dialog.py`
   ```python
   def show_category_dialog(ctx, page, category=None):
       """Show create/edit category dialog.
       
       Args:
           ctx: AppContext
           page: Flet page
           category: Existing Category to edit, or None for new
       """
   ```

2. Dialog fields:
   - Name (TextField, required)
   - Slug (TextField, auto-generated from name, unique check)
   - Type (Dropdown: "income" or "expense")
   - Icon (optional, icon picker or text field)

3. Validation:
   - Name must not be empty
   - Slug must be unique per user
   - Show inline error messages (NFR-17)

4. Actions:
   - Save: `ctx.category_repo.create()` or `update()`
   - Delete: Show confirm, then `ctx.category_repo.delete()` (prevent if in use)
   - Cancel: Close dialog

5. Update menu handler in `menubar.py`:
   ```python
   def _open_categories_dialog(ctx, page):
       from ..components.dialogs import show_category_dialog
       show_category_dialog(ctx, page)
   ```

6. Optional: Add category list view to Settings page

**Priority:** CRITICAL - Blocking full ledger functionality

---

### 2. Budget Creation/Edit UI (FR-13) ⚠️ CRITICAL

**Current State:**
- Budget model exists
- Budgets view displays existing budgets (read-only)
- NO UI to create new budgets
- NO UI to edit budget amounts

**Requirements:**
- FR-13: "Support budget definitions and threshold notifications"
- UR-3: "Define and monitor budgets"
- NFR-17: "Clear validation error messages"

**Implementation Steps:**

1. Add "Create Budget" button to budgets view
2. Create budget dialog with fields:
   - Month selector (default: current month)
   - Overall monthly budget amount (optional)
   - Per-category budget lines:
     - Category dropdown
     - Planned amount (float, must be > 0)
     - Add/remove line buttons

3. Save logic:
   ```python
   budget = ctx.budget_repo.create(
       Budget(month=selected_month, user_id=uid)
   )
   for line in budget_lines:
       ctx.budget_repo.add_line(budget.id, category_id, amount)
   ```

4. Edit existing budget:
   - Load budget for selected month
   - Pre-populate form
   - Allow updating line amounts or adding new lines

5. Delete budget:
   - Confirm dialog
   - Delete all budget lines first, then budget

6. Visual feedback:
   - Show budget threshold warnings (FR-13)
   - Color-code progress bars (green/yellow/red)
   - Mark exceeded categories

**Priority:** CRITICAL - Core user requirement (UR-3)

---

### 3. Habit Creation Dialog (FR-15) ⚠️ HIGH

**Current State:**
- Habits view shows existing habits
- Daily toggle works
- Streak calculation works
- NO UI to add new habits

**Requirements:**
- FR-14: "Persist habit entries with streak recalculation logic"
- FR-15: "Validate habit form submissions with error messaging"
- UR-11: "Toggle daily completion quickly"

**Implementation Steps:**

1. Add "Add Habit" button to habits view (top or in app bar)

2. Create habit dialog:
   ```python
   def show_habit_dialog(ctx, page, habit=None):
       """Show create/edit habit dialog."""
   ```

3. Dialog fields:
   - Name (TextField, required, max 100 chars)
   - Description (TextField, optional, multiline)
   - Reminder time (TextField, HH:MM format, optional)
   - Cadence (Dropdown: "daily", future: "weekly")

4. Validation:
   - Name cannot be empty
   - Reminder time must be valid HH:MM or empty
   - Show inline errors (NFR-17)

5. Save:
   ```python
   habit = ctx.habit_repo.create(
       Habit(name=name, description=desc, reminder_time=time, user_id=uid)
   )
   ```

6. Refresh habits list after save

7. Also allow editing existing habits (pass habit parameter)

**Priority:** HIGH - Users can't add habits currently

---

### 4. Habit Archive/Reactivate (FR-18) 🔹 MEDIUM

**Current State:**
- Habits have `is_active` field
- Inactive habits hidden from main list
- NO UI to archive/reactivate

**Requirements:**
- FR-18: "Archive/reactivate habits without data loss"
- UR-13: "Archive/reactivate habits"

**Implementation Steps:**

1. Add "Archive" button/icon to each habit row

2. Archive action:
   ```python
   habit.is_active = False
   ctx.habit_repo.update(habit)
   ```

3. Add "Archived Habits" section (collapsible or separate tab)
   - Query: `ctx.habit_repo.list_inactive(user_id=uid)`
   - Show archived habits with "Reactivate" button

4. Reactivate action:
   ```python
   habit.is_active = True
   ctx.habit_repo.update(habit)
   ```

5. Preserve all habit entries (don't delete on archive)

6. Optional: Show archive date

**Priority:** MEDIUM - Nice to have, not blocking

---

### 5. Enhanced Debt Payment Recording (FR-23) 🔹 MEDIUM

**Current State:**
- Payment dialog updates liability balance
- NO corresponding ledger transaction created
- Disconnected from main ledger

**Requirements:**
- FR-23: "Record actual payments and reconcile balances"
- UR-17: "Record actual payments and reconcile balances"

**Implementation Steps:**

1. Modify payment handler in debts view:
   ```python
   def record_payment(liability_id, amount, date):
       # Update liability balance
       liability = ctx.liability_repo.get_by_id(liability_id)
       liability.balance -= amount
       ctx.liability_repo.update(liability)
       
       # Create corresponding transaction
       ctx.transaction_repo.create(
           Transaction(
               amount=-amount,  # Negative (outflow)
               memo=f"Payment: {liability.name}",
               occurred_at=date,
               category_id=debt_payment_category_id,  # Create special category
               liability_id=liability_id,  # Link back to debt
               user_id=uid,
           )
       )
   ```

2. Create special "Debt Payment" category on first use

3. Show link in ledger transactions that have `liability_id`

4. Optional: Show payment history on debt detail view

**Priority:** MEDIUM - Improves data consistency

---

### 6. Account Management Dialog 🔹 MEDIUM

**Current State:**
- Account model exists
- Default account auto-created
- NO UI to add/edit accounts

**Implementation Steps:**

1. Create account dialog similar to category dialog

2. Fields:
   - Name (required)
   - Currency (dropdown, default "USD")
   - Account type (checking, savings, credit card, etc.)

3. List accounts on Settings page

4. Allow editing/deleting (with validation - can't delete if has transactions)

**Priority:** MEDIUM - Multi-account support

---

## Medium Priority - UX Improvements

### 7. Centralized Transaction Dialog

**Current:** Menu > File > New Transaction redirects to ledger  
**Goal:** Open dialog from anywhere  
**Benefit:** True global quick add

**Steps:**
1. Extract transaction dialog logic from ledger view to shared component
2. Update menubar handler to show dialog directly
3. After save, optionally navigate to ledger or stay on current page

---

### 8. Export Destination Picker

**Current:** Exports hardcoded to `instance/exports/`  
**Goal:** User chooses destination folder  

**Steps:**
1. Use `FilePicker` with directory mode
2. Update export handlers to accept destination parameter
3. Remember last destination in settings

---

### 9. Habit Reminders (FR-17, FR-51)

**Current:** Reminder time field exists, but no actual notifications  
**Future:** Local OS notifications or email

**Steps:**
1. Use scheduler to check reminder times daily
2. Trigger OS notification (platform-specific)
3. Or: Queue email reminders (requires SMTP config)

**Priority:** LOW - Nice to have, complex implementation

---

## Feature Completion Checklist

Use this checklist to track implementation progress:

- [ ] Category Management UI (FR-9)
- [ ] Budget Creation/Edit (FR-13)  
- [ ] Habit Creation Dialog (FR-15)
- [ ] Habit Archiving (FR-18)
- [ ] Enhanced Debt Payments (FR-23)
- [ ] Account Management
- [ ] Centralized Transaction Dialog
- [ ] Export Destination Picker
- [ ] Habit Reminders (FR-17, FR-51)

## Requirements Traceability

### Fully Implemented:
- ✅ FR-7: Transaction filtering/pagination
- ✅ FR-8: Transaction validation
- ✅ FR-10: Rollup summaries (income, expense, net)
- ✅ FR-11: Spending chart rendering
- ✅ FR-14: Habit entry persistence + streaks
- ✅ FR-16: Habit heatmap visualization (TODO: verify)
- ✅ FR-19: Liability CRUD
- ✅ FR-20: Snowball payoff
- ✅ FR-21: Avalanche payoff
- ✅ FR-22: Payoff timeline chart
- ✅ FR-24: Debt-free projection display
- ✅ FR-25: Portfolio CSV import
- ✅ FR-27: Portfolio allocation chart
- ✅ FR-28: Portfolio gain/loss calculation
- ✅ FR-29: Portfolio export
- ✅ FR-30: Idempotent transaction import
- ✅ FR-37: Demo seed
- ✅ FR-38: Export bundling

### Partially Implemented:
- ⚠️ FR-9: Categories exist, no CRUD UI
- ⚠️ FR-13: Budgets display, no creation UI
- ⚠️ FR-15: Habits exist, no creation UI
- ⚠️ FR-23: Payments update balance, no ledger link

### Not Implemented:
- ❌ FR-12: Optimistic locking (version field exists, not enforced)
- ❌ FR-17: Habit reminders (stub only)
- ❌ FR-18: Habit archiving (field exists, no UI)
- ❌ FR-31: Auto CSV column mapping
- ❌ FR-32: File system watcher
- ❌ FR-51: Budget threshold alerts (notifications)
- ❌ FR-52: Habit reminders (notifications)

## Next Steps

1. **Start with Category Management** - Blocking full ledger usability
2. **Then Budget Creation** - High user value (UR-3)
3. **Then Habit Creation** - Currently can't add habits
4. **Then smaller improvements** - Archive, account management, etc.

Each feature should follow this workflow:
1. Create dialog component
2. Add validation
3. Wire to repository
4. Update view to show dialog
5. Test CRUD operations
6. Update this document

## Testing Checklist

For each implemented feature:

- [ ] Unit tests for repository methods
- [ ] Manual UI testing (create, edit, delete)
- [ ] Validation error messages display correctly  
- [ ] Data persists to database
- [ ] UI refreshes after changes
- [ ] Edge cases handled (empty fields, duplicates, etc.)

---

**Last Updated:** November 25, 2025  
**Phase:** Post-HomeBank Menu Bar Implementation
