# PocketSage Demo Script
## Comprehensive Demonstration Guide

**Application:** PocketSage - Offline Personal Finance & Habit Tracker  
**Team:** Kheiven D'Haiti, Dossell Sinclair, Jennifer Ginther, Lucas Vega, Vedell Jones  
**Estimated Demo Time:** 15-20 minutes (can be condensed to 10 minutes for shorter presentations)

---

## Pre-Demo Checklist

Before starting your demonstration, complete these preparation steps:

**Environment Setup:**
- Ensure Python 3.11+ is installed
- Activate your virtual environment: `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows)
- Verify the app launches: `python run_desktop.py`

**Demo Data Preparation:**
- Run demo seed to populate realistic data: `make demo-seed` or navigate to Settings > "Run Demo Seed"
- Alternatively, start fresh and add data live during the demo to show real-time functionality

**Display Settings:**
- Set your display to a resolution that showcases the full application window
- Consider using Light mode for projector visibility (toggle in Settings if needed)
- Close unnecessary background applications

**Materials Ready:**
- Sample CSV file for import demonstration (located in `scripts/csv_samples/`)
- These speaker notes accessible but not visible to audience

---

## Part 1: Opening Hook (2 minutes)

### The Problem Statement

*Begin with the audience, not the product:*

> "How many of you use a personal finance app? Now, how many of you have wondered where your financial data actually goes? Who can see your spending habits, your debts, your investment portfolio?"

> "Most finance apps require cloud accounts, sync your data to external servers, and often monetize your information. For students and privacy-conscious individuals, this creates a fundamental tension: you need to track your money, but you don't want your financial life exposed."

### The Solution

> "PocketSage solves this by keeping everything local. No cloud. No login required. No telemetry. Your financial data never leaves your machine."

**Key Differentiator (say this clearly):**
> "This is a desktop application that works completely offline. Once installed, you don't need internet access to manage your finances, track your habits, or plan your debt payoff."

### Quick Architecture Note

> "Under the hood, we're using Python with Flet for the UI, SQLite for storage with an upgrade path to SQLCipher for encryption, and Matplotlib for generating charts. But you don't need to know any of that to use it—let me show you."

**[Launch the application now]**

---

## Part 2: Dashboard Overview (2 minutes)

### First Impressions

*As the app opens, narrate what the audience sees:*

> "When you open PocketSage, you land on the Dashboard. This gives you an at-a-glance view of your financial health for the current month."

**Point out these elements:**

1. **Monthly Summary Cards:**
   > "At the top, you see your income, expenses, and net for this month. These update automatically as you add transactions."

2. **Quick Actions:**
   > "These buttons let you jump straight into adding a new transaction or habit without navigating through menus."

3. **Recent Transactions:**
   > "Your most recent activity appears here—helpful for spotting duplicates or remembering recent purchases."

4. **Habit Progress:**
   > "If you're tracking habits, you'll see how many you've completed today."

5. **Debt Summary:**
   > "A quick view of your total outstanding debt and projected payoff timeline."

### Navigation Introduction

> "On the left, you have the navigation rail. You can click these icons, or use keyboard shortcuts—Ctrl+1 through Ctrl+7—to jump between sections. Power users appreciate this."

**Demonstrate one shortcut:** Press `Ctrl+2` to jump to Ledger.

---

## Part 3: Ledger & Transactions (4 minutes)

### Viewing Transactions

> "The Ledger is your central hub for all income and expenses. Let's look at what's already here."

**Scroll through the transaction list, pointing out:**
- Date column
- Description
- Category assignment
- Amount (with income/expense color coding)
- Account assignment

### Adding a Transaction Live

> "Let me add a transaction right now so you can see the workflow."

**Step-by-step narration:**

1. **Click "Add Transaction" button** (or press `Ctrl+N`)
   > "I'll click Add Transaction—or I could press Ctrl+N."

2. **Fill in the form:**
   - **Date:** Select today's date
   - **Description:** "Coffee at campus cafe"
   - **Amount:** 5.50
   - **Type:** Expense
   - **Category:** Food (or create a new "Coffee" category if demonstrating category management)
   - **Account:** Cash

   > "Notice the form validates as I type. If I leave a required field empty or enter an invalid amount, I'll see an error message before I can save."

3. **Save the transaction**
   > "When I save, watch the monthly summary update..."

**[Save and pause for the audience to see the update]**

> "The expense total just increased by $5.50, and the net decreased accordingly. This happens instantly, no refresh needed."

### Filtering Transactions

> "With months or years of data, you need good filtering. Let me show you."

**Demonstrate each filter:**

1. **Date Range:**
   > "I can narrow down to just this week, this month, or set custom dates."

2. **Category Filter:**
   > "If I want to see only Food expenses, I select that category. Notice 'All' is always available to reset."

3. **Type Filter:**
   > "I can view just income, just expenses, or both."

4. **Search:**
   > "And there's text search for finding specific merchants or descriptions."

### CSV Import/Export

> "For those migrating from another app or wanting backups, we support CSV import and export."

**If time permits, demonstrate:**

1. **Export:** Click the export button, show the CSV file location
   > "Exports go to your data directory with timestamps, so you never accidentally overwrite previous exports."

2. **Import:** Navigate to File > Import CSV (or use the FilePicker from Settings)
   > "Imports are idempotent—if you import the same file twice, it won't create duplicates. We use transaction hashing to detect existing records."

### Spending Chart

> "At the bottom of the Ledger, you'll see a spending breakdown chart. This automatically generates based on your transactions."

**Point to the chart:**
> "This shows spending by category using a colorblind-friendly palette. You can export this as a PNG image for reports or personal records."

---

## Part 4: Budgets (3 minutes)

### Navigating to Budgets

> "Let's see how budgets integrate with what we just saw. I'll navigate to Budgets."

**[Press Ctrl+3 or click Budgets in nav rail]**

### Budget Overview

> "The Budgets view shows your planned spending versus actual spending for each category."

**Explain the visual elements:**

1. **Progress Bars:**
   > "Each category shows a progress bar. Green means you're under budget. As you approach your limit, it shifts toward yellow, then red when you exceed it."

2. **Percentage Display:**
   > "The percentage tells you exactly where you stand. 75% means you've spent three-quarters of your allocated budget."

3. **Month Selector:**
   > "Budgets are monthly. Use the month selector to review previous months or plan future ones."

### Creating/Editing a Budget

> "Let me adjust a budget to show you the workflow."

**Click Edit on a budget category (or Add Budget if empty):**

1. > "I can set a specific amount for any category. Let's say I want to limit Food spending to $300 this month."

2. > "There's also a 'Copy from Previous Month' feature—helpful for maintaining consistent budgets without re-entering everything."

3. > "And rollover support means if I underspend this month, that amount can roll forward."

### Budget Warnings in Ledger

> "Now here's where it gets smart. When I add a transaction in the Ledger, if that expense pushes a category over budget, I see a warning immediately."

**[Navigate back to Ledger and point to any budget warning indicators]**

> "This real-time feedback helps you make conscious spending decisions."

---

## Part 5: Habit Tracking (3 minutes)

### Why Habits in a Finance App?

> "You might wonder why a finance app includes habit tracking. The answer is behavioral: financial health often correlates with other habits. Tracking them together reveals patterns."

**[Navigate to Habits: Ctrl+4 or click nav rail]**

### Habit List View

> "Here are the habits being tracked. Each shows the name, current streak, and completion status for today."

### Adding a New Habit

> "Let me add a new habit."

**Click "Add Habit" and fill in:**
- **Name:** "Pack lunch instead of buying"
- **Reminder Time:** (optional) 7:00 AM

> "This habit directly impacts my Food budget. By tracking it here, I can correlate habit streaks with spending trends."

### Daily Toggle

> "The primary interaction is simple—toggle whether you completed the habit today."

**Click the toggle for a habit:**

> "One click. The streak updates instantly. Watch this habit's current streak..."

**[Toggle and show streak increment]**

> "It went from 5 days to 6. If I miss a day, the streak resets, but my longest streak record is preserved."

### Heatmap Visualization

> "Each habit has a heatmap showing your completion history."

**Click on a habit to show details (or scroll to heatmap if visible):**

> "The last 30 days displayed as a grid—green for completed days, empty for missed. This visual pattern helps identify when habits slip, often around weekends or busy periods."

### Archive/Reactivate

> "If you've mastered a habit and no longer need to track it, you can archive it without losing the data. It moves to an inactive list and can be reactivated later."

---

## Part 6: Debt Management (4 minutes)

### The Debt Problem

> "For students and new earners, debt is often the biggest financial stressor. PocketSage provides tools to not just track debt, but strategically eliminate it."

**[Navigate to Debts: Ctrl+5 or click nav rail]**

### Liability List

> "Here are the current debts being tracked. Each shows the creditor name, balance, APR, and minimum payment."

### Adding a Debt

> "Let me add a credit card debt to demonstrate."

**Click "Add Debt" and fill in:**
- **Name:** "Student Credit Card"
- **Balance:** 2,500.00
- **APR:** 19.99%
- **Minimum Payment:** 50.00

> "With this information, PocketSage can calculate exactly how long payoff will take and how much interest you'll pay."

### Payoff Strategies Explained

> "This is where it gets interesting. There are two main strategies for paying off multiple debts:"

**Point to the strategy selector:**

1. **Snowball Method:**
   > "Pay minimums on everything, then throw extra money at the smallest balance first. Psychologically rewarding because you eliminate individual debts faster."

2. **Avalanche Method:**
   > "Pay minimums on everything, then attack the highest interest rate first. Mathematically optimal because you pay less interest overall."

> "PocketSage calculates both and shows you the difference in total interest paid."

### Payoff Timeline Chart

> "This chart visualizes your path to debt freedom."

**Point to the chart:**

> "The X-axis is time—months or years. The Y-axis is total debt balance. The line shows how your debt decreases over time with consistent payments."

> "Notice this date here—that's your projected debt-free date. If you switch strategies or increase payments, this date updates."

### Recording Payments

> "When you make a payment, record it here."

**Click "Record Payment" on a debt:**

> "I enter the amount—let's say $100. The system recalculates the remaining balance and adjusts the payoff timeline."

> "There's also an option to create a corresponding Ledger transaction, so your payment appears in your expense history."

### Interest Calculations

> "At the bottom, you see projected total interest. This shows how much you'll pay over the life of your debts if you stick to the current plan. It's a powerful motivator to see that number decrease when you pay extra."

---

## Part 7: Portfolio Tracking (2 minutes)

### Optional Module Introduction

> "Portfolio tracking is optional—not everyone holds investments. But for those who do, PocketSage provides basic tracking without connecting to external APIs."

**[Navigate to Portfolio: Ctrl+6 or click nav rail]**

### Holdings Overview

> "The portfolio shows your holdings—stocks, ETFs, crypto, whatever you own."

**Point to the columns:**
- Symbol
- Quantity
- Average Cost (what you paid)
- Current Price (what you update manually or via CSV)
- Gain/Loss

### CSV Import for Holdings

> "Rather than entering each holding manually, you can import from your broker's CSV export."

**If demonstrating:**
> "The import maps columns automatically and prevents duplicates on reimport."

### Allocation Chart

> "The donut chart shows your allocation across holdings. This helps visualize diversification—or lack thereof."

> "Like other charts, this can be exported as PNG."

### Gain/Loss Summary

> "At the bottom, you see total cost basis, total market value, and overall gain or loss. This gives you a quick health check without logging into your brokerage."

---

## Part 8: Reports & Analytics (2 minutes)

### Consolidated View

> "The Reports section aggregates insights from all modules."

**[Navigate to Reports: Click nav rail]**

### Available Reports

**Walk through each card:**

1. **Spending by Category:**
   > "Same chart from Ledger, but here with export options."

2. **Budget Usage:**
   > "Visual comparison of budgeted versus actual across all categories."

3. **Habit Completion:**
   > "Aggregate view of all habit streaks and completion rates."

4. **Debt Payoff Timeline:**
   > "The consolidated debt chart with projections."

5. **Portfolio Allocation:**
   > "Investment distribution visualization."

6. **Cashflow Trends:**
   > "Income versus expenses over time—helpful for spotting seasonal patterns."

### Export Bundle

> "The most powerful feature here is the Export Bundle."

**Click "Export All" or the bundle button:**

> "This creates a ZIP file containing CSV exports of all your data plus PNG images of every chart. Perfect for creating personal financial reports or backing up everything at once."

---

## Part 9: Settings & Admin (2 minutes)

### Theme Toggle

> "First, the basics—light and dark mode."

**Toggle the theme:**
> "Your preference persists across sessions."

### Demo Seed / Reset

> "For testing or demonstrations like this one, you can seed demo data or reset to a clean state."

**Point to the buttons:**
- **Run Demo Seed:** Populates realistic sample data
- **Reset Demo Data:** Clears everything and reseeds

> "This is idempotent—running seed multiple times doesn't create duplicates."

### Backup and Restore

> "Since all data is local, backups matter."

**Click Backup:**
> "This creates a ZIP archive of your database in the backups folder. We keep the 5 most recent backups automatically."

**Point to Restore:**
> "If something goes wrong, you can restore from any backup. The app validates the archive before restoring."

### Data Directory

> "You can view and access your data directory directly. Everything lives here—database, exports, backups, charts."

---

## Part 10: Security & Privacy Emphasis (1 minute)

### Recap the Privacy Model

> "Let me emphasize what makes PocketSage different:"

**Tick these off:**

1. > "**No cloud accounts.** Your data stays on your machine. Period."

2. > "**No login required.** The app works in guest mode by default."

3. > "**No telemetry.** We don't collect usage data, crash reports, or analytics."

4. > "**No external APIs.** Portfolio prices are manual or CSV-imported, not fetched from the internet."

5. > "**Encryption ready.** The architecture supports SQLCipher for encrypted-at-rest storage. When enabled, your database file is encrypted and cannot be read without the key."

### Who This Is For

> "This is ideal for students managing their first budgets, privacy-conscious individuals who don't trust cloud services, and anyone who wants their financial data truly private."

---

## Part 11: Technical Highlights (1 minute)

*For technically-oriented audiences or Q&A:*

### Stack Summary

> "Quick technical overview:"
- **UI Framework:** Flet (Flutter-based Python UI)
- **Database:** SQLModel over SQLite, with SQLCipher upgrade path
- **Charts:** Matplotlib server-rendered PNG
- **Packaging:** PyInstaller for standalone executables
- **Testing:** 184 tests passing, full pytest suite

### Keyboard Shortcuts

> "Power users can navigate entirely via keyboard:"
- `Ctrl+1` through `Ctrl+7`: Navigate sections
- `Ctrl+N`: New transaction
- `Ctrl+Shift+H`: New habit
- `Ctrl+I`: Import CSV
- `Ctrl+Q`: Quit

### Cross-Platform

> "The app runs on Windows, macOS, and Linux. Same codebase, same features."

---

## Part 12: Closing (1 minute)

### Summary

> "To recap, PocketSage provides:"
- Complete transaction and budget management
- Habit tracking correlated with financial behavior
- Strategic debt payoff with snowball and avalanche methods
- Optional investment portfolio tracking
- Comprehensive reporting and exports
- All completely offline and private

### Call to Action

> "The source code is available on GitHub. You can clone it, install with pip, and start using it today. Or download a pre-built executable for your platform."

### Questions

> "I'm happy to take questions—whether about the features, the technical implementation, or our development process."

---

## Appendix: Common Questions & Answers

**Q: Why not just use a spreadsheet?**
> A: You could, but PocketSage provides structure, validation, visualizations, and calculated insights (like debt payoff projections) that would require complex spreadsheet formulas to replicate.

**Q: What if I want to sync across devices?**
> A: The current version is single-device. However, the data directory can be placed on a sync service like Dropbox or OneDrive at your own risk—just don't run the app simultaneously on two machines.

**Q: How does SQLCipher encryption work?**
> A: When enabled via environment variable, the SQLite database is encrypted using AES-256. The encryption key is derived from a passphrase you set. Without the key, the database file is unreadable.

**Q: Can I import from Mint/YNAB/other apps?**
> A: If you can export your data as CSV, you can import it. The import system maps columns flexibly and handles various date formats.

**Q: What about mobile?**
> A: Currently desktop-only. Flet supports mobile compilation, so it's technically possible for future versions, but not in the current scope.

**Q: How do you prevent data loss?**
> A: Regular backups (manual or scheduled), export bundles, and the fact that SQLite is a very robust file format. We also validate all imports and reject malformed data rather than corrupting the database.

---

## Appendix: Quick Reference Checklist

Use this during the demo:

- [ ] App launches successfully
- [ ] Dashboard shows summary data
- [ ] Add transaction live → watch summary update
- [ ] Show transaction filtering (date, category, type)
- [ ] Show or mention CSV import/export
- [ ] Navigate to Budgets → show progress bars
- [ ] Toggle a habit → show streak update
- [ ] Show habit heatmap
- [ ] Navigate to Debts → explain snowball vs avalanche
- [ ] Show payoff timeline chart
- [ ] Show Portfolio (if time permits)
- [ ] Show Reports → mention export bundle
- [ ] Show Settings → demonstrate backup
- [ ] Emphasize privacy model
- [ ] Close with call to action

---

*Demo script prepared for PocketSage v1.0 - Fall 2025*
