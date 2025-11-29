continue making the app

## Phase 1: Core Infrastructure & Login System Stabilization

**Goal:** Ensure the authentication system, database initialization, and app context work correctly.

### 1.1 Audit Authentication Flow

**Files to examine:**

- `src/pocketsage/services/auth.py`
- `src/pocketsage/desktop/views/auth.py` (if exists)
- `src/pocketsage/desktop/app.py` (login handling)

**Tasks:**

1. **Verify admin login works:**
   - Username: `admin`, Password: `admin123`
   - Should redirect to main app with admin privileges
   - Admin toggle in app bar should be visible

2. **Verify user account creation:**
   - Admin can create new users
   - New users can log in with their credentials
   - User data is isolated (transactions, habits, etc. scoped to user_id)

3. **Verify password management:**
   - Admin can reset user passwords
   - Password hashing uses Argon2 (check `auth.py`)

4. **Fix any login issues:**

   ```python
   # If login bypass is needed for testing, ensure it's dev-only:
   # TODO(@Bloodawn): Verify login flow works with admin/admin123
   ```

### 1.2 Database & Context Initialization

**Files to examine:**

- `src/pocketsage/infra/database.py`
- `src/pocketsage/desktop/context.py` (AppContext)

**Tasks:**

1. **Ensure single database engine instance:**
   - All modules should share the same SQLModel engine
   - No duplicate connections or session leaks

2. **Verify AppContext provides:**
   - `ctx.current_user` — Current logged-in user
   - `ctx.require_user_id()` — Throws if no user
   - `ctx.is_admin` — Boolean for admin check
   - All repository instances (transaction_repo, habit_repo, etc.)

3. **Add missing repositories to context if needed:**

   ```python
   # Example pattern in context.py:
   @property
   def holding_repo(self) -> HoldingRepository:
       if self._holding_repo is None:
           self._holding_repo = HoldingRepository(self.session)
       return self._holding_repo
   ```

### 1.3 User/Admin Mode Toggle

**Tasks:**

1. **Verify app bar contains admin toggle switch**
2. **When toggled to admin:**
   - Show Admin nav item
   - Enable admin-only features
3. **When toggled to user:**
   - Hide Admin nav item
   - Restrict to user features
4. **Ensure toggle state persists during session**

---

## Phase 2: Ledger Module Completion

**Goal:** Full transaction CRUD, filtering, CSV import/export, budget integration, and spending charts.

**Requirements satisfied:** UR-1, UR-2, UR-7, FR-7 through FR-13, FR-30

### 2.1 Audit Current Ledger State

**Files:**

- `src/pocketsage/desktop/views/ledger.py`
- `src/pocketsage/infra/repositories/transaction.py`
- `src/pocketsage/services/ledger.py` (if exists)
- `src/pocketsage/services/importers.py`

**Check each button/action:**

| UI Element | Expected Behavior | Status |
|------------|-------------------|--------|
| Add Transaction button | Opens dialog, saves to DB, refreshes list | ☐ Check |
| Edit Transaction | Opens pre-filled dialog, updates DB | ☐ Check |
| Delete Transaction | Confirms, deletes from DB, refreshes | ☐ Check |
| Category filter dropdown | Filters transactions by category | ☐ Check |
| Date range filter | Filters by start/end date | ☐ Check |
| Type filter (income/expense/all) | Filters by transaction type | ☐ Check |
| Import CSV button | Opens file picker, imports transactions | ☐ Check |
| Export CSV button | Saves transactions to CSV file | ☐ Check |
| CSV Help button | Opens help view with format info | ☐ Check |
| Spending chart | Displays category breakdown chart | ☐ Check |
| Pagination controls | Navigate through transaction pages | ☐ Check |

### 2.2 Fix Filter "All" Option Bug

**Known issue:** `ValueError: invalid literal for int() with base 10: 'All'`

**Location:** Likely in `ledger.py` in `apply_filters()` or similar

**Fix pattern:**

```python
def apply_filters(self, e=None):
    # Category filter - handle "All" option
    category_id = None
    if self.category_filter.value and self.category_filter.value.isdigit():
        category_id = int(self.category_filter.value)
    
    # Type filter - already uses strings, should be fine
    tx_type = self.type_filter.value if self.type_filter.value != "all" else None
    
    # Apply filters via repository
    transactions = self.ctx.transaction_repo.search(
        user_id=self.ctx.require_user_id(),
        category_id=category_id,
        tx_type=tx_type,
        start_date=self.start_date.value,
        end_date=self.end_date.value,
        page=self.current_page,
        per_page=25
    )
    self.refresh_transaction_list(transactions)
```

### 2.3 Wire Add Transaction Dialog

**Ensure the dialog:**

1. Opens with proper form fields (date, description, amount, category, account, type)
2. Validates inputs (amount is numeric, date is valid, required fields present)
3. Calls `ctx.transaction_repo.create()` on submit
4. Shows success snackbar: "Transaction added successfully"
5. Refreshes the transaction list
6. Updates monthly summaries
7. Handles errors with `show_error_dialog()`

```python
def save_transaction(self, e):
    try:
        # Validate
        if not self.amount_field.value or not self.description_field.value:
            self.notify("Please fill in all required fields", error=True)
            return
        
        amount = float(self.amount_field.value)
        if self.type_field.value == "expense":
            amount = -abs(amount)
        
        # Create transaction
        tx = Transaction(
            user_id=self.ctx.require_user_id(),
            date=self.date_field.value or date.today(),
            amount=amount,
            description=self.description_field.value,
            category_id=int(self.category_field.value) if self.category_field.value else None,
            account_id=int(self.account_field.value) if self.account_field.value else None,
        )
        self.ctx.transaction_repo.create(tx)
        
        self.close_dialog()
        self.apply_filters()  # Refresh list
        self.update_summaries()
        self.notify("Transaction added successfully")
        
    except ValueError as ve:
        self.notify(f"Invalid input: {ve}", error=True)
    except Exception as ex:
        self.show_error_dialog(f"Failed to add transaction: {ex}")
```

### 2.4 Wire CSV Import/Export

**Import (idempotent via external_id/transaction_id):**

```python
def import_csv(self, file_path: str):
    try:
        count = importers.import_transactions(
            file_path=file_path,
            user_id=self.ctx.require_user_id(),
            session=self.ctx.session
        )
        self.notify(f"Imported {count} transactions (duplicates skipped)")
        self.apply_filters()
    except Exception as ex:
        self.show_error_dialog(f"Import failed: {ex}")
```

**Export:**

```python
def export_csv(self, e):
    try:
        # Get filtered transactions or all
        transactions = self.ctx.transaction_repo.list_all(
            user_id=self.ctx.require_user_id()
        )
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = Path(self.ctx.config.exports_dir) / f"transactions_{timestamp}.csv"
        
        # Write CSV
        exporters.export_transactions_csv(transactions, export_path)
        
        self.notify(f"Exported to: {export_path}")
    except Exception as ex:
        self.show_error_dialog(f"Export failed: {ex}")
```

### 2.5 Spending Chart Integration

**Ensure:**

1. Chart generates from current month's transactions
2. Uses `services/reports.py` `build_spending_chart()` or similar
3. Chart updates when transactions change
4. Uses colorblind-friendly palette (NFR-18)
5. Displays as embedded image in Ledger view

```python
def refresh_spending_chart(self):
    try:
        transactions = self.ctx.transaction_repo.search(
            user_id=self.ctx.require_user_id(),
            start_date=self.current_month_start,
            end_date=self.current_month_end,
            tx_type="expense"
        )
        
        if transactions:
            chart_path = reports.build_spending_chart(
                transactions=transactions,
                output_dir=self.ctx.config.temp_dir
            )
            self.spending_chart_image.src = chart_path
        else:
            self.spending_chart_image.src = None  # Or placeholder
            
        self.page.update()
    except Exception as ex:
        logger.error(f"Failed to generate spending chart: {ex}")
```

### 2.6 Monthly Summaries

**Display at top or bottom of ledger:**

- Total Income (green)
- Total Expenses (red)  
- Net Cash Flow (positive=green, negative=red)

```python
def update_summaries(self):
    txs = self.ctx.transaction_repo.search(
        user_id=self.ctx.require_user_id(),
        start_date=self.current_month_start,
        end_date=self.current_month_end
    )
    
    income = sum(t.amount for t in txs if t.amount > 0)
    expenses = sum(abs(t.amount) for t in txs if t.amount < 0)
    net = income - expenses
    
    self.income_label.value = f"Income: ${income:,.2f}"
    self.expense_label.value = f"Expenses: ${expenses:,.2f}"
    self.net_label.value = f"Net: ${net:,.2f}"
    self.net_label.color = ft.colors.GREEN if net >= 0 else ft.colors.RED
```

---

## Phase 3: Budgets Module Completion

**Goal:** Create, edit, view budgets with progress bars and category breakdown.

**Requirements satisfied:** UR-3, FR-13

### 3.1 Audit Current Budgets State

**Files:**

- `src/pocketsage/desktop/views/budgets.py`
- `src/pocketsage/infra/repositories/budget.py`
- `src/pocketsage/models/budget.py`

**Check each button/action:**

| UI Element | Expected Behavior | Status |
|------------|-------------------|--------|
| Create Budget button | Opens form for new monthly budget | ☐ Check |
| Edit Budget | Modify existing budget amounts | ☐ Check |
| Category budget lines | Show budget vs actual per category | ☐ Check |
| Progress bars | Visual fill based on % spent | ☐ Check |
| Overspend highlighting | Red when over budget | ☐ Check |
| Month selector sync | Changes month updates budget view | ☐ Check |
| Copy from previous month | Copies budget template | ☐ Check |

### 3.2 Wire Create Budget Button

**If currently shows "Coming soon" or does nothing:**

```python
def create_budget_dialog(self, e):
    # Get all categories
    categories = self.ctx.category_repo.list_all(user_id=self.ctx.require_user_id())
    
    # Build form with one input per category
    category_inputs = []
    for cat in categories:
        tf = ft.TextField(
            label=cat.name,
            value="0.00",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=150,
            data=cat.id  # Store category ID
        )
        category_inputs.append(tf)
    
    # Create dialog
    self.budget_dialog = ft.AlertDialog(
        title=ft.Text(f"Create Budget for {self.current_month}"),
        content=ft.Column(category_inputs, scroll=ft.ScrollMode.AUTO, height=400),
        actions=[
            ft.TextButton("Cancel", on_click=self.close_budget_dialog),
            ft.ElevatedButton("Save", on_click=lambda e: self.save_budget(category_inputs))
        ]
    )
    self.page.dialog = self.budget_dialog
    self.budget_dialog.open = True
    self.page.update()

def save_budget(self, inputs):
    try:
        # Create or update budget for current month
        budget = self.ctx.budget_repo.get_or_create(
            user_id=self.ctx.require_user_id(),
            month=self.current_month
        )
        
        for inp in inputs:
            amount = float(inp.value or 0)
            if amount > 0:
                self.ctx.budget_line_repo.upsert(
                    budget_id=budget.id,
                    category_id=inp.data,
                    amount=amount
                )
        
        self.close_budget_dialog()
        self.refresh_budget_view()
        self.notify("Budget saved successfully")
    except Exception as ex:
        self.show_error_dialog(f"Failed to save budget: {ex}")
```

### 3.3 Wire Month Selector to Budget View

**In the app bar or layout, when month changes:**

```python
def set_month(self, e):
    self.ctx.current_month = e.control.value  # e.g., "2025-01"
    self.notify(f"Switched to {self.ctx.current_month}")
    
    # Refresh current view if it's budgets
    if self.page.route == "/budgets":
        self.refresh_budget_view()
    
    self.page.update()
```

### 3.4 Budget Progress Visualization

```python
def build_budget_progress(self, budget_line, actual_spent):
    percentage = (actual_spent / budget_line.amount * 100) if budget_line.amount > 0 else 0
    is_over = percentage > 100
    
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text(budget_line.category.name, weight=ft.FontWeight.BOLD),
                ft.Text(f"${actual_spent:.2f} / ${budget_line.amount:.2f}"),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.ProgressBar(
                value=min(percentage / 100, 1.0),
                color=ft.colors.RED if is_over else ft.colors.GREEN,
                bgcolor=ft.colors.GREY_300,
            ),
            ft.Text(
                f"{percentage:.1f}% {'(OVER)' if is_over else ''}",
                color=ft.colors.RED if is_over else None,
                size=12
            ),
        ]),
        padding=10,
        border=ft.border.all(1, ft.colors.GREY_400),
        border_radius=5,
        margin=ft.margin.only(bottom=10),
    )
```

---

## Phase 4: Habits Module Completion

**Goal:** Full habit CRUD, daily toggle, streak tracking, heatmap visualization.

**Requirements satisfied:** UR-4, UR-11 through UR-14, FR-14 through FR-18

### 4.1 Audit Current Habits State

**Files:**

- `src/pocketsage/desktop/views/habits.py`
- `src/pocketsage/infra/repositories/habit.py`
- `src/pocketsage/services/habits.py`
- `src/pocketsage/models/habit.py`

**Check each button/action:**

| UI Element | Expected Behavior | Status |
|------------|-------------------|--------|
| Add Habit button | Opens form for new habit | ☐ Check |
| Daily toggle checkbox | Creates/removes today's entry | ☐ Check |
| Streak display | Shows current/longest streak | ☐ Check |
| Heatmap/calendar | Visual of last 30 days | ☐ Check |
| Archive habit | Removes from active list | ☐ Check |
| Reactivate habit | Returns to active list | ☐ Check |
| Edit habit | Modify name/details | ☐ Check |

### 4.2 Wire Add Habit Button

```python
def add_habit_dialog(self, e):
    self.habit_name_field = ft.TextField(label="Habit Name", autofocus=True)
    self.habit_description_field = ft.TextField(label="Description (optional)", multiline=True)
    self.habit_reminder_field = ft.TextField(label="Reminder Time (optional)", hint_text="e.g., 08:00")
    
    self.habit_dialog = ft.AlertDialog(
        title=ft.Text("Add New Habit"),
        content=ft.Column([
            self.habit_name_field,
            self.habit_description_field,
            self.habit_reminder_field,
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Cancel", on_click=self.close_habit_dialog),
            ft.ElevatedButton("Add Habit", on_click=self.save_new_habit)
        ]
    )
    self.page.dialog = self.habit_dialog
    self.habit_dialog.open = True
    self.page.update()

def save_new_habit(self, e):
    try:
        name = self.habit_name_field.value.strip()
        if not name:
            self.notify("Habit name is required", error=True)
            return
        
        habit = Habit(
            user_id=self.ctx.require_user_id(),
            name=name,
            description=self.habit_description_field.value or None,
            reminder_time=self.habit_reminder_field.value or None,
            is_active=True
        )
        self.ctx.habit_repo.create(habit)
        
        self.close_habit_dialog()
        self.refresh_habits_list()
        self.notify(f"Habit '{name}' added!")
    except Exception as ex:
        self.show_error_dialog(f"Failed to add habit: {ex}")
```

### 4.3 Wire Daily Toggle

```python
def toggle_habit_today(self, habit_id: int, completed: bool):
    try:
        today = date.today()
        
        if completed:
            # Create entry for today
            entry = HabitEntry(
                habit_id=habit_id,
                date=today,
                completed=True
            )
            self.ctx.habit_entry_repo.upsert(entry)
        else:
            # Remove today's entry
            self.ctx.habit_entry_repo.delete_for_date(habit_id, today)
        
        # Recalculate streaks
        self.recalculate_streak(habit_id)
        
        # Refresh display
        self.refresh_habit_row(habit_id)
        
    except Exception as ex:
        self.show_error_dialog(f"Failed to toggle habit: {ex}")

def recalculate_streak(self, habit_id: int):
    entries = self.ctx.habit_entry_repo.list_for_habit(habit_id, limit=365)
    
    # Calculate current streak (consecutive days ending today or yesterday)
    current_streak = 0
    check_date = date.today()
    entry_dates = {e.date for e in entries if e.completed}
    
    while check_date in entry_dates:
        current_streak += 1
        check_date -= timedelta(days=1)
    
    # If today not done but yesterday was, streak continues from yesterday
    if date.today() not in entry_dates and (date.today() - timedelta(days=1)) in entry_dates:
        check_date = date.today() - timedelta(days=1)
        current_streak = 0
        while check_date in entry_dates:
            current_streak += 1
            check_date -= timedelta(days=1)
    
    # Calculate longest streak
    longest_streak = calculate_longest_streak(entries)
    
    # Update habit record
    self.ctx.habit_repo.update_streaks(habit_id, current_streak, longest_streak)
```

### 4.4 Heatmap Visualization

```python
def build_habit_heatmap(self, habit_id: int, days: int = 30):
    """Build a 7xN grid showing completion history."""
    entries = self.ctx.habit_entry_repo.list_for_habit(
        habit_id, 
        start_date=date.today() - timedelta(days=days),
        end_date=date.today()
    )
    completed_dates = {e.date for e in entries if e.completed}
    
    # Build 7-column grid (Sun-Sat)
    grid_rows = []
    current_date = date.today() - timedelta(days=days-1)
    
    week_row = []
    # Pad first week
    for _ in range((current_date.weekday() + 1) % 7):
        week_row.append(ft.Container(width=20, height=20))
    
    while current_date <= date.today():
        is_completed = current_date in completed_dates
        cell = ft.Container(
            width=20,
            height=20,
            bgcolor=ft.colors.GREEN_400 if is_completed else ft.colors.GREY_300,
            border_radius=3,
            tooltip=current_date.strftime("%Y-%m-%d"),
        )
        week_row.append(cell)
        
        if len(week_row) == 7:
            grid_rows.append(ft.Row(week_row, spacing=2))
            week_row = []
        
        current_date += timedelta(days=1)
    
    if week_row:
        grid_rows.append(ft.Row(week_row, spacing=2))
    
    return ft.Column(grid_rows, spacing=2)
```

### 4.5 Archive/Reactivate

```python
def archive_habit(self, habit_id: int):
    try:
        self.ctx.habit_repo.update(habit_id, is_active=False)
        self.refresh_habits_list()
        self.notify("Habit archived")
    except Exception as ex:
        self.show_error_dialog(f"Failed to archive: {ex}")

def reactivate_habit(self, habit_id: int):
    try:
        self.ctx.habit_repo.update(habit_id, is_active=True)
        self.refresh_habits_list()
        self.notify("Habit reactivated")
    except Exception as ex:
        self.show_error_dialog(f"Failed to reactivate: {ex}")
```

---

## Phase 5: Debts (Liabilities) Module Completion

**Goal:** Full debt CRUD, payoff strategies (snowball/avalanche), payment recording, timeline charts.

**Requirements satisfied:** UR-5, UR-15 through UR-18, FR-19 through FR-24

### 5.1 Audit Current Debts State

**Files:**

- `src/pocketsage/desktop/views/debts.py`
- `src/pocketsage/infra/repositories/liability.py`
- `src/pocketsage/services/debts.py`
- `src/pocketsage/models/liability.py`

**Check each button/action:**

| UI Element | Expected Behavior | Status |
|------------|-------------------|--------|
| Add Debt button | Opens form for new liability | ☐ Check |
| Edit Debt | Modify balance/rate/payment | ☐ Check |
| Delete Debt | Removes liability | ☐ Check |
| Snowball button | Shows snowball payoff plan | ☐ Check |
| Avalanche button | Shows avalanche payoff plan | ☐ Check |
| Strategy toggle | Switches between strategies | ☐ Check |
| Record Payment | Reduces balance, recalcs | ☐ Check |
| Payoff timeline chart | Visual of balance over time | ☐ Check |
| Projected payoff date | Shows debt-free date | ☐ Check |

### 5.2 Wire Add Debt Button

```python
def add_debt_dialog(self, e):
    self.debt_name = ft.TextField(label="Debt Name", autofocus=True)
    self.debt_balance = ft.TextField(label="Current Balance", keyboard_type=ft.KeyboardType.NUMBER)
    self.debt_apr = ft.TextField(label="APR (%)", keyboard_type=ft.KeyboardType.NUMBER)
    self.debt_min_payment = ft.TextField(label="Minimum Payment", keyboard_type=ft.KeyboardType.NUMBER)
    self.debt_extra_payment = ft.TextField(label="Extra Monthly Payment (optional)", value="0")
    
    self.debt_dialog = ft.AlertDialog(
        title=ft.Text("Add New Debt"),
        content=ft.Column([
            self.debt_name,
            self.debt_balance,
            self.debt_apr,
            self.debt_min_payment,
            self.debt_extra_payment,
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Cancel", on_click=self.close_debt_dialog),
            ft.ElevatedButton("Add Debt", on_click=self.save_new_debt)
        ]
    )
    self.page.dialog = self.debt_dialog
    self.debt_dialog.open = True
    self.page.update()

def save_new_debt(self, e):
    try:
        liability = Liability(
            user_id=self.ctx.require_user_id(),
            name=self.debt_name.value.strip(),
            balance=float(self.debt_balance.value),
            apr=float(self.debt_apr.value),
            min_payment=float(self.debt_min_payment.value),
            extra_payment=float(self.debt_extra_payment.value or 0),
        )
        self.ctx.liability_repo.create(liability)
        
        self.close_debt_dialog()
        self.refresh_debts_list()
        self.recalculate_payoff()
        self.notify("Debt added successfully")
    except ValueError:
        self.notify("Please enter valid numbers", error=True)
    except Exception as ex:
        self.show_error_dialog(f"Failed to add debt: {ex}")
```

### 5.3 Payoff Strategy Implementation

```python
def calculate_payoff_schedule(self, strategy: str = "avalanche"):
    """
    Calculate payoff schedule using snowball or avalanche strategy.
    
    Snowball: Pay smallest balance first (psychological wins)
    Avalanche: Pay highest APR first (mathematically optimal)
    """
    liabilities = self.ctx.liability_repo.list_all(user_id=self.ctx.require_user_id())
    
    if not liabilities:
        return []
    
    # Sort by strategy
    if strategy == "snowball":
        sorted_debts = sorted(liabilities, key=lambda x: x.balance)
    else:  # avalanche
        sorted_debts = sorted(liabilities, key=lambda x: x.apr, reverse=True)
    
    # Calculate extra payment pool (sum of min payments from paid-off debts)
    schedule = debts_service.snowball_schedule(sorted_debts) if strategy == "snowball" else \
               debts_service.avalanche_schedule(sorted_debts)
    
    return schedule

def display_payoff_projection(self, schedule):
    """Display the payoff schedule and summary."""
    if not schedule:
        self.payoff_summary.value = "No debts to calculate"
        return
    
    # Find total months and total interest
    total_months = max(s['month'] for s in schedule) if schedule else 0
    total_interest = sum(s.get('interest_paid', 0) for s in schedule)
    
    payoff_date = date.today() + timedelta(days=total_months * 30)
    
    self.payoff_summary.content = ft.Column([
        ft.Text(f"Debt-free by: {payoff_date.strftime('%B %Y')}", weight=ft.FontWeight.BOLD),
        ft.Text(f"Total months: {total_months}"),
        ft.Text(f"Total interest paid: ${total_interest:,.2f}"),
    ])
    
    # Generate chart
    self.generate_payoff_chart(schedule)
```

### 5.4 Wire Snowball/Avalanche Toggle

```python
def on_strategy_change(self, e):
    strategy = e.control.value  # "snowball" or "avalanche"
    self.current_strategy = strategy
    
    schedule = self.calculate_payoff_schedule(strategy)
    self.display_payoff_projection(schedule)
    
    # Highlight strategy explanation
    if strategy == "snowball":
        self.strategy_info.value = "Snowball: Pay smallest balances first for quick wins!"
    else:
        self.strategy_info.value = "Avalanche: Pay highest interest first to save money!"
    
    self.page.update()
```

### 5.5 Wire Record Payment

```python
def record_payment_dialog(self, liability_id: int):
    liability = self.ctx.liability_repo.get(liability_id)
    
    self.payment_amount = ft.TextField(
        label="Payment Amount",
        keyboard_type=ft.KeyboardType.NUMBER,
        value=str(liability.min_payment)
    )
    self.payment_date = ft.TextField(
        label="Date",
        value=date.today().isoformat()
    )
    
    self.payment_dialog = ft.AlertDialog(
        title=ft.Text(f"Record Payment for {liability.name}"),
        content=ft.Column([
            ft.Text(f"Current Balance: ${liability.balance:,.2f}"),
            self.payment_amount,
            self.payment_date,
        ]),
        actions=[
            ft.TextButton("Cancel", on_click=self.close_payment_dialog),
            ft.ElevatedButton("Record Payment", on_click=lambda e: self.save_payment(liability_id))
        ]
    )
    self.page.dialog = self.payment_dialog
    self.payment_dialog.open = True
    self.page.update()

def save_payment(self, liability_id: int):
    try:
        amount = float(self.payment_amount.value)
        liability = self.ctx.liability_repo.get(liability_id)
        
        # Update balance
        new_balance = max(0, liability.balance - amount)
        self.ctx.liability_repo.update(liability_id, balance=new_balance)
        
        # Optionally log as transaction
        # self.create_payment_transaction(liability, amount)
        
        self.close_payment_dialog()
        self.refresh_debts_list()
        self.recalculate_payoff()
        
        if new_balance == 0:
            self.notify(f"🎉 Congratulations! {liability.name} is paid off!")
        else:
            self.notify(f"Payment of ${amount:,.2f} recorded. New balance: ${new_balance:,.2f}")
            
    except Exception as ex:
        self.show_error_dialog(f"Failed to record payment: {ex}")
```

### 5.6 Payoff Timeline Chart

```python
def generate_payoff_chart(self, schedule):
    """Generate matplotlib chart showing balance over time."""
    try:
        if not schedule:
            self.payoff_chart.src = None
            return
        
        months = [s['month'] for s in schedule]
        balances = [s['total_balance'] for s in schedule]
        
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.fill_between(months, balances, alpha=0.3, color='#2196F3')
        ax.plot(months, balances, color='#1976D2', linewidth=2)
        ax.set_xlabel('Months')
        ax.set_ylabel('Total Debt ($)')
        ax.set_title('Debt Payoff Timeline')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
        ax.grid(True, alpha=0.3)
        
        # Save to temp file
        chart_path = Path(self.ctx.config.temp_dir) / "payoff_chart.png"
        fig.savefig(chart_path, dpi=100, bbox_inches='tight')
        plt.close(fig)
        
        self.payoff_chart.src = str(chart_path)
        self.page.update()
        
    except Exception as ex:
        logger.error(f"Failed to generate payoff chart: {ex}")
```

---

## Phase 6: Portfolio Module Completion

**Goal:** Full holdings CRUD, CSV import/export, allocation chart, gain/loss tracking.

**Requirements satisfied:** UR-6, UR-19 through UR-21, FR-25 through FR-29

**NOTE:** User indicates most of this is complete; focus on verifying wiring.

### 6.1 Audit Current Portfolio State

**Files:**

- `src/pocketsage/desktop/views/portfolio.py`
- `src/pocketsage/infra/repositories/holding.py`
- `src/pocketsage/models/holding.py`
- `src/pocketsage/services/importers.py` (portfolio import)

**Check each button/action:**

| UI Element | Expected Behavior | Status |
|------------|-------------------|--------|
| Add Holding button | Opens form for new holding | ☐ Check |
| Edit Holding | Modify quantity/prices | ☐ Check |
| Delete Holding | Removes holding | ☐ Check |
| Import CSV button | Opens file picker, imports | ☐ Check |
| Export CSV button | Exports holdings to CSV | ☐ Check |
| Allocation chart | Donut/pie chart of holdings | ☐ Check |
| Gain/Loss display | Shows P/L per holding | ☐ Check |
| Total value display | Sum of all holdings | ☐ Check |
| Account filter | Filter by brokerage account | ☐ Check |

### 6.2 Verify Add Holding Wiring

```python
# Ensure this pattern exists and is wired:
def add_holding_dialog(self, e):
    self.holding_symbol = ft.TextField(label="Symbol/Name", autofocus=True)
    self.holding_quantity = ft.TextField(label="Quantity", keyboard_type=ft.KeyboardType.NUMBER)
    self.holding_cost = ft.TextField(label="Cost Basis (per share)", keyboard_type=ft.KeyboardType.NUMBER)
    self.holding_price = ft.TextField(label="Current Price", keyboard_type=ft.KeyboardType.NUMBER)
    self.holding_account = ft.Dropdown(
        label="Account",
        options=[ft.dropdown.Option(a.id, a.name) for a in self.get_accounts()]
    )
    
    dialog = ft.AlertDialog(
        title=ft.Text("Add Holding"),
        content=ft.Column([
            self.holding_symbol,
            self.holding_quantity,
            self.holding_cost,
            self.holding_price,
            self.holding_account,
        ], tight=True),
        actions=[
            ft.TextButton("Cancel", on_click=self.close_dialog),
            ft.ElevatedButton("Add", on_click=self.save_holding)
        ]
    )
    # ... show dialog
```

### 6.3 Verify CSV Import Wiring

```python
def start_portfolio_import(self, e):
    """Triggered by Import CSV button."""
    # File picker should already be attached to page
    self.file_picker.pick_files(
        allowed_extensions=["csv"],
        dialog_title="Select Portfolio CSV"
    )

def on_portfolio_file_picked(self, e: ft.FilePickerResultEvent):
    if e.files:
        file_path = e.files[0].path
        try:
            count = importers.import_portfolio_holdings(
                file_path=file_path,
                user_id=self.ctx.require_user_id(),
                session=self.ctx.session
            )
            self.refresh_holdings_list()
            self.refresh_allocation_chart()
            self.notify(f"Imported {count} holdings")
        except Exception as ex:
            self.show_error_dialog(f"Import failed: {ex}")
```

### 6.4 Verify Allocation Chart

```python
def refresh_allocation_chart(self):
    holdings = self.ctx.holding_repo.list_all(user_id=self.ctx.require_user_id())
    
    if not holdings:
        self.allocation_chart.src = None
        return
    
    chart_path = reports.allocation_chart_png(
        holdings=holdings,
        output_dir=self.ctx.config.temp_dir
    )
    
    self.allocation_chart.src = str(chart_path)
    self.page.update()
```

### 6.5 Verify Gain/Loss Calculations

```python
def build_holdings_table(self):
    holdings = self.ctx.holding_repo.list_all(user_id=self.ctx.require_user_id())
    
    rows = []
    total_cost = 0
    total_value = 0
    
    for h in holdings:
        cost_basis = h.quantity * h.cost_price
        market_value = h.quantity * h.market_price
        gain_loss = market_value - cost_basis
        gain_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0
        
        total_cost += cost_basis
        total_value += market_value
        
        rows.append(ft.DataRow(cells=[
            ft.DataCell(ft.Text(h.symbol)),
            ft.DataCell(ft.Text(f"{h.quantity:,.4f}")),
            ft.DataCell(ft.Text(f"${h.cost_price:,.2f}")),
            ft.DataCell(ft.Text(f"${h.market_price:,.2f}")),
            ft.DataCell(ft.Text(f"${cost_basis:,.2f}")),
            ft.DataCell(ft.Text(f"${market_value:,.2f}")),
            ft.DataCell(ft.Text(
                f"${gain_loss:+,.2f} ({gain_pct:+.1f}%)",
                color=ft.colors.GREEN if gain_loss >= 0 else ft.colors.RED
            )),
            ft.DataCell(ft.Row([
                ft.IconButton(ft.icons.EDIT, on_click=lambda e, id=h.id: self.edit_holding(id)),
                ft.IconButton(ft.icons.DELETE, on_click=lambda e, id=h.id: self.delete_holding(id)),
            ])),
        ]))
    
    # Summary row
    total_gain = total_value - total_cost
    self.summary_text.value = f"Total: ${total_value:,.2f} | Cost: ${total_cost:,.2f} | P/L: ${total_gain:+,.2f}"
    
    return ft.DataTable(columns=[...], rows=rows)
```

### 6.6 Verify Export CSV

```python
def export_holdings_csv(self, e):
    try:
        holdings = self.ctx.holding_repo.list_all(user_id=self.ctx.require_user_id())
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = Path(self.ctx.config.exports_dir) / f"portfolio_{timestamp}.csv"
        
        exporters.export_holdings_csv(holdings, export_path)
        
        self.notify(f"Exported to: {export_path}")
    except Exception as ex:
        self.show_error_dialog(f"Export failed: {ex}")
```

### 6.7 Fix Any Model Relationship Issues

**Known issue from docs:** Holding <-> Account relationship may have mapping issues.

```python
# In models/holding.py, ensure proper relationship:
class Holding(SQLModel, table=True):
    __tablename__ = "holding"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    account_id: Optional[int] = Field(default=None, foreign_key="account.id")
    symbol: str
    quantity: float
    cost_price: float
    market_price: float
    currency: str = "USD"
    
    # Relationships (use string references to avoid forward ref issues)
    account: Optional["Account"] = Relationship(back_populates="holdings")
```

---

## Phase 7: Reports Module Completion

**Goal:** Comprehensive charts, export bundles, monthly/YTD summaries.

**Requirements satisfied:** UR-7, UR-22, UR-23, FR-38, FR-41, FR-42

### 7.1 Audit Current Reports State

**Files:**

- `src/pocketsage/desktop/views/reports.py`
- `src/pocketsage/services/reports.py`
- `src/pocketsage/services/admin_tasks.py` (export functions)

**Check each button/action:**

| UI Element | Expected Behavior | Status |
|------------|-------------------|--------|
| Monthly Spending Report | Generates spending chart | ☐ Check |
| YTD Summary | Income/expense summary | ☐ Check |
| Debt Payoff Report | Exports payoff schedule | ☐ Check |
| Full Data Export | ZIP with all CSVs + charts | ☐ Check |
| Download buttons | Save files locally | ☐ Check |

### 7.2 Wire Monthly Spending Report

```python
def generate_monthly_report(self, e):
    try:
        transactions = self.ctx.transaction_repo.search(
            user_id=self.ctx.require_user_id(),
            start_date=self.current_month_start,
            end_date=self.current_month_end,
            tx_type="expense"
        )
        
        if not transactions:
            self.notify("No transactions for this month")
            return
        
        chart_path = reports.export_spending_png(
            transactions=transactions,
            output_dir=self.ctx.config.exports_dir,
            filename=f"spending_{self.ctx.current_month}.png"
        )
        
        self.notify(f"Report saved: {chart_path}")
        
        # Also display in view
        self.monthly_chart.src = str(chart_path)
        self.page.update()
        
    except Exception as ex:
        self.show_error_dialog(f"Failed to generate report: {ex}")
```

### 7.3 Wire YTD Summary

```python
def generate_ytd_summary(self, e):
    try:
        year_start = date(date.today().year, 1, 1)
        
        transactions = self.ctx.transaction_repo.search(
            user_id=self.ctx.require_user_id(),
            start_date=year_start,
            end_date=date.today()
        )
        
        income = sum(t.amount for t in transactions if t.amount > 0)
        expenses = sum(abs(t.amount) for t in transactions if t.amount < 0)
        net = income - expenses
        
        # Export to CSV
        export_path = Path(self.ctx.config.exports_dir) / f"ytd_summary_{date.today().year}.csv"
        with open(export_path, 'w') as f:
            f.write("Category,Amount\n")
            f.write(f"Total Income,{income:.2f}\n")
            f.write(f"Total Expenses,{expenses:.2f}\n")
            f.write(f"Net Savings,{net:.2f}\n")
        
        self.notify(f"YTD summary exported: {export_path}")
        
        # Display summary
        self.ytd_display.content = ft.Column([
            ft.Text(f"Year-to-Date Summary ({date.today().year})", weight=ft.FontWeight.BOLD),
            ft.Text(f"Total Income: ${income:,.2f}", color=ft.colors.GREEN),
            ft.Text(f"Total Expenses: ${expenses:,.2f}", color=ft.colors.RED),
            ft.Text(f"Net Savings: ${net:,.2f}", 
                    color=ft.colors.GREEN if net >= 0 else ft.colors.RED),
        ])
        self.page.update()
        
    except Exception as ex:
        self.show_error_dialog(f"Failed to generate YTD summary: {ex}")
```

### 7.4 Wire Full Data Export

```python
def export_all_data(self, e):
    try:
        self.notify("Generating export bundle...")
        
        export_path = admin_tasks.run_export(
            user_id=self.ctx.require_user_id(),
            session=self.ctx.session,
            config=self.ctx.config
        )
        
        self.notify(f"Export complete: {export_path}")
        
    except Exception as ex:
        self.show_error_dialog(f"Export failed: {ex}")
```

---

## Phase 8: Admin & Settings Module Completion

**Goal:** User management, demo seeding, backup/restore, theme toggle.

**Requirements satisfied:** UR-24 through UR-27, FR-37 through FR-40

### 8.1 Audit Current Admin State

**Files:**

- `src/pocketsage/desktop/views/admin.py`
- `src/pocketsage/desktop/views/settings.py`
- `src/pocketsage/services/admin_tasks.py`

**Check each button/action:**

| UI Element | Expected Behavior | Status |
|------------|-------------------|--------|
| User list dropdown | Shows all users | ☐ Check |
| Create user button | Creates new local user | ☐ Check |
| Change password | Resets user password | ☐ Check |
| Promote/Demote admin | Toggles admin status | ☐ Check |
| Seed Demo Data | Populates all tables | ☐ Check |
| Reset Demo Data | Clears and re-seeds | ☐ Check |
| Backup button | Creates ZIP archive | ☐ Check |
| Restore button | Loads from backup | ☐ Check |
| Theme toggle | Light/dark mode switch | ☐ Check |
| Data directory display | Shows instance/ path | ☐ Check |

### 8.2 Verify Admin Access Control

```python
# In navigation_helpers.py or app.py:
def get_nav_destinations(is_admin: bool):
    destinations = [
        ("/dashboard", "Dashboard", ft.icons.DASHBOARD),
        ("/ledger", "Ledger", ft.icons.RECEIPT_LONG),
        ("/budgets", "Budgets", ft.icons.SAVINGS),
        ("/habits", "Habits", ft.icons.CHECK_CIRCLE),
        ("/debts", "Debts", ft.icons.CREDIT_CARD),
        ("/portfolio", "Portfolio", ft.icons.TRENDING_UP),
        ("/reports", "Reports", ft.icons.BAR_CHART),
        ("/settings", "Settings", ft.icons.SETTINGS),
    ]
    
    if is_admin:
        destinations.append(("/admin", "Admin", ft.icons.ADMIN_PANEL_SETTINGS))
    
    return destinations
```

### 8.3 Verify Seed Demo Data

```python
def seed_demo_data(self, e):
    try:
        self.notify("Seeding demo data...")
        
        result = admin_tasks.seed_demo_database(
            user_id=self.ctx.require_user_id(),
            session=self.ctx.session
        )
        
        # Refresh all views
        self.page.go("/dashboard")
        
        self.notify(f"Seeded: {result['transactions']} transactions, "
                   f"{result['habits']} habits, {result['debts']} debts, "
                   f"{result['holdings']} holdings")
                   
    except Exception as ex:
        self.show_error_dialog(f"Seeding failed: {ex}")
```

### 8.4 Verify Reset Demo Data

```python
def reset_demo_data(self, e):
    # Show confirmation dialog first
    def confirm_reset(e):
        try:
            result = admin_tasks.reset_demo_database(
                user_id=self.ctx.require_user_id(),
                session=self.ctx.session
            )
            
            self.close_confirm_dialog()
            self.page.go("/dashboard")
            self.notify(f"Reset complete: {result['transactions_deleted']} transactions removed")
            
        except Exception as ex:
            self.show_error_dialog(f"Reset failed: {ex}")
    
    self.show_confirm_dialog(
        "Reset Demo Data",
        "This will DELETE all your data and optionally reseed. Continue?",
        on_confirm=confirm_reset
    )
```

### 8.5 Verify Theme Toggle

```python
def toggle_theme(self, e):
    if self.page.theme_mode == ft.ThemeMode.LIGHT:
        self.page.theme_mode = ft.ThemeMode.DARK
    else:
        self.page.theme_mode = ft.ThemeMode.LIGHT
    
    # Persist preference
    self.ctx.settings_repo.set("theme_mode", self.page.theme_mode.value)
    
    self.page.update()
```

### 8.6 Verify Backup/Restore

```python
def create_backup(self, e):
    try:
        backup_path = admin_tasks.create_backup(
            user_id=self.ctx.require_user_id(),
            session=self.ctx.session,
            config=self.ctx.config
        )
        self.notify(f"Backup created: {backup_path}")
    except Exception as ex:
        self.show_error_dialog(f"Backup failed: {ex}")

def restore_backup(self, e):
    self.file_picker.pick_files(
        allowed_extensions=["zip"],
        dialog_title="Select Backup ZIP"
    )

def on_backup_file_picked(self, e: ft.FilePickerResultEvent):
    if e.files:
        # Show confirmation first
        self.show_confirm_dialog(
            "Restore Backup",
            "This will REPLACE all current data. Continue?",
            on_confirm=lambda _: self.do_restore(e.files[0].path)
        )

def do_restore(self, backup_path: str):
    try:
        admin_tasks.restore_backup(
            backup_path=backup_path,
            user_id=self.ctx.require_user_id(),
            session=self.ctx.session
        )
        self.page.go("/dashboard")
        self.notify("Restore complete!")
    except Exception as ex:
        self.show_error_dialog(f"Restore failed: {ex}")
```

---

## Phase 9: Navigation & Global UI Fixes

**Goal:** Ensure all navigation paths work, keyboard shortcuts function, and UI is consistent.

### 9.1 Verify All Navigation Routes

```python
# In app.py Router configuration:
routes = {
    "/": build_dashboard_view,
    "/dashboard": build_dashboard_view,
    "/ledger": build_ledger_view,
    "/budgets": build_budgets_view,
    "/habits": build_habits_view,
    "/debts": build_debts_view,
    "/portfolio": build_portfolio_view,
    "/reports": build_reports_view,
    "/settings": build_settings_view,
    "/admin": build_admin_view,
    "/help": build_help_view,
    "/login": build_login_view,
}
```

### 9.2 Verify Keyboard Shortcuts

```python
# In app.py keyboard handler:
def on_keyboard(self, e: ft.KeyboardEvent):
    if e.ctrl:
        shortcuts = {
            "1": "/dashboard",
            "2": "/ledger",
            "3": "/budgets",
            "4": "/habits",
            "5": "/debts",
            "6": "/portfolio",
            "7": "/settings",
            "n": "new_transaction",
        }
        
        if e.key in shortcuts:
            if shortcuts[e.key].startswith("/"):
                self.page.go(shortcuts[e.key])
            elif shortcuts[e.key] == "new_transaction":
                self.controllers.add_transaction_dialog(None)
    
    if e.ctrl and e.shift:
        if e.key == "h":
            self.controllers.add_habit_dialog(None)
```

### 9.3 Fix Any Dead Buttons

Search codebase for buttons with empty or stubbed handlers:

```bash
grep -r "on_click=lambda" src/pocketsage/desktop/
grep -r "pass$" src/pocketsage/desktop/views/
grep -r "# TODO" src/pocketsage/desktop/
```

For each dead button found, implement proper handler or remove if not needed.

### 9.4 Consistent Snackbar/Notification Pattern

```python
# Ensure all views use consistent notification:
def notify(self, message: str, error: bool = False):
    self.page.snack_bar = ft.SnackBar(
        content=ft.Text(message),
        bgcolor=ft.colors.RED_400 if error else ft.colors.GREEN_400,
        duration=3000,
    )
    self.page.snack_bar.open = True
    self.page.update()

def show_error_dialog(self, message: str):
    dialog = ft.AlertDialog(
        title=ft.Text("Error", color=ft.colors.RED),
        content=ft.Text(message),
        actions=[ft.TextButton("OK", on_click=lambda e: self.close_error_dialog())]
    )
    self.page.dialog = dialog
    dialog.open = True
    self.page.update()
```

---

## Phase 10: Testing & Quality Assurance

**Goal:** Comprehensive test coverage, all tests passing, linting clean.

### 10.1 Run Full Test Suite

```bash
# All tests with verbose output
pytest -v --tb=long

# With coverage report
pytest --cov=src/pocketsage --cov-report=html --cov-report=term

# Just the fast tests
pytest -m "not slow"
```

### 10.2 Add Missing Tests

For each module, ensure tests exist for:

**Ledger Tests:**

```python
def test_add_transaction():
    """Test creating a transaction."""
    
def test_delete_transaction():
    """Test deleting a transaction."""
    
def test_filter_by_category():
    """Test filtering works, including 'All' option."""
    
def test_csv_import_idempotent():
    """Test reimporting same CSV doesn't duplicate."""
    
def test_csv_export():
    """Test export creates valid CSV."""
```

**Habits Tests:**

```python
def test_toggle_habit_today():
    """Test toggling creates/removes entry."""
    
def test_streak_calculation():
    """Test streak logic handles gaps correctly."""
    
def test_archive_habit():
    """Test archiving removes from active list."""
```

**Debts Tests:**

```python
def test_snowball_order():
    """Test snowball sorts by balance ascending."""
    
def test_avalanche_order():
    """Test avalanche sorts by APR descending."""
    
def test_payoff_calculation():
    """Test payoff dates are reasonable."""
    
def test_record_payment():
    """Test payment reduces balance."""
```

**Portfolio Tests:**

```python
def test_add_holding():
    """Test creating a holding."""
    
def test_gain_loss_calculation():
    """Test P/L is correct."""
    
def test_csv_import_holdings():
    """Test importing portfolio CSV."""
```

### 10.3 Linting & Formatting

```bash
# Check linting
ruff check src/ tests/

# Auto-fix linting issues
ruff check --fix src/ tests/

# Format code
black src/ tests/

# Type checking (if configured)
mypy src/pocketsage/
```

### 10.4 Manual QA Checklist

Run through this checklist before finalizing:

- [ ] Login as admin (admin/admin123)
- [ ] Create a new user account
- [ ] Login as the new user
- [ ] Add 3 transactions (2 expenses, 1 income)
- [ ] Verify monthly summary updates
- [ ] Create a budget
- [ ] Verify budget progress shows spending
- [ ] Add a habit
- [ ] Toggle habit completion
- [ ] Verify streak updates
- [ ] Add a debt
- [ ] Toggle between snowball/avalanche
- [ ] Record a payment
- [ ] Add a portfolio holding
- [ ] Import a portfolio CSV
- [ ] Verify allocation chart
- [ ] Generate monthly report
- [ ] Export all data as ZIP
- [ ] Toggle dark mode
- [ ] Seed demo data (as admin)
- [ ] Reset demo data (as admin)
- [ ] Test all keyboard shortcuts
- [ ] Test navigation rail
- [ ] Check Help page loads

---

## Phase 11: Documentation & Final Polish

### 11.1 Update README if Needed

Ensure README accurately reflects:

- Current feature set
- Installation steps
- Usage instructions
- Keyboard shortcuts
- Configuration options

### 11.2 Update ROADMAP/TODO

Mark completed items:

```markdown
## Completed
- [x] Ledger CRUD with filters
- [x] CSV import/export (idempotent)
- [x] Budget progress bars
- [x] Habit streaks and heatmap
- [x] Debt payoff strategies
- [x] Portfolio allocation chart
- [x] Admin user management
- [x] Theme toggle

## Remaining
- [ ] Habit reminders (infrastructure ready)
- [ ] Budget alerts/notifications
- [ ] Multi-currency support
```

### 11.3 Add Inline Comments

For complex logic, add explanatory comments:

```python
def calculate_longest_streak(entries: list[HabitEntry]) -> int:
    """
    Calculate the longest consecutive streak of completed habits.
    
    Algorithm:
    1. Sort entries by date
    2. Walk through looking for consecutive days
    3. Track current and max streak
    
    Edge cases:
    - Empty entries returns 0
    - Single entry returns 1
    - Gaps reset current streak
    """
    if not entries:
        return 0
    
    # ... implementation
```

---

## Commit Strategy

Since this should be ONE Pull Request, organize commits logically:

```bash
# After completing each phase:
git add -A
git commit -m "Phase X: [Description]"

# Example commit sequence:
git commit -m "Phase 1: Stabilize auth and app context"
git commit -m "Phase 2: Complete Ledger module - filters, CRUD, CSV"
git commit -m "Phase 3: Complete Budgets module - create, progress bars"
git commit -m "Phase 4: Complete Habits module - toggle, streaks, heatmap"
git commit -m "Phase 5: Complete Debts module - strategies, payments, chart"
git commit -m "Phase 6: Verify Portfolio wiring - CRUD, import, allocation"
git commit -m "Phase 7: Complete Reports module - exports, summaries"
git commit -m "Phase 8: Complete Admin module - users, seed, backup"
git commit -m "Phase 9: Fix navigation and global UI issues"
git commit -m "Phase 10: Add tests and ensure quality"
git commit -m "Phase 11: Documentation and polish"

# Then create PR
git push origin feature/complete-pocketsage
```

---

## Quick Reference: File Locations

| Module | View File | Service File | Repository File | Model File |
|--------|-----------|--------------|-----------------|------------|
| Ledger | `views/ledger.py` | `services/ledger.py` | `repositories/transaction.py` | `models/transaction.py` |
| Budgets | `views/budgets.py` | — | `repositories/budget.py` | `models/budget.py` |
| Habits | `views/habits.py` | `services/habits.py` | `repositories/habit.py` | `models/habit.py` |
| Debts | `views/debts.py` | `services/debts.py` | `repositories/liability.py` | `models/liability.py` |
| Portfolio | `views/portfolio.py` | — | `repositories/holding.py` | `models/holding.py` |
| Reports | `views/reports.py` | `services/reports.py` | — | — |
| Admin | `views/admin.py` | `services/admin_tasks.py` | `repositories/user.py` | `models/user.py` |
| Settings | `views/settings.py` | — | `repositories/settings.py` | — |

---

## Success Criteria

The PR is ready when:

1. ✅ All buttons and actions work (no dead UI)
2. ✅ All tests pass (`pytest -v`)
3. ✅ Linting is clean (`ruff check src/`)
4. ✅ Code is formatted (`black --check src/`)
5. ✅ Manual QA checklist passes
6. ✅ Demo flows work end-to-end
7. ✅ Admin login works (admin/admin123)
8. ✅ User creation and isolation works
9. ✅ All keyboard shortcuts work
10. ✅ All navigation paths work
11. ✅ Charts generate correctly
12. ✅ CSV import/export works
13. ✅ Backup/restore works
14. ✅ Theme toggle persists

---

## Start Here

1. Clone repo and set up environment (Phase 0)
2. Run app and manually test current state
3. Run `pytest` to see what's failing
4. Work through phases 1-11 in order
5. After each phase, commit with clear message
6. Final test run and manual QA
7. Create PR with summary of changes

Good luck! 🚀
