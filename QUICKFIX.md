# Quick Fix for Button Issues

## Problem
The buttons weren't working because your database had stale user accounts created before the authentication system was properly implemented.

## Solution
Delete your old database and start fresh with the correct default accounts.

### Steps:

1. **Close the running app** (if open)

2. **Delete the old database:**
   ```powershell
   Remove-Item -Path instance\pocketsage.db -Force
   ```

3. **Run the app:**
   ```powershell
   python run_desktop.py
   ```

4. **Login with default credentials:**
   - **Admin account:** username `admin`, password `admin123`
   - **Local account:** username `local`, password `local123`

5. **Test the buttons:**
   - Navigate to Ledger (Ctrl+2)
   - Click the + button or press Ctrl+N
   - Fill in the transaction form
   - Click Save
   - Verify the transaction appears in the list

## What Was Fixed

1. **Authentication System:**
   - Local user now has correct password hash for "local123"
   - Local user now has correct role "user" (was "admin" before)
   - Admin user works correctly with "admin123" password

2. **Transaction Creation:**
   - Code already uses `occurred_at` field correctly
   - ledger_service.save_transaction() properly handles datetime
   - No code changes needed for transaction persistence

## Verification

Run the test script to verify everything works:
```powershell
python test_auth.py
```

Expected output:
```
✓ Admin login successful: admin (role: admin, id: 1)
✓ Local login successful: local (role: user, id: 2)
✓ Transaction created successfully: Test transaction (id: 1)
```

## Why This Happened

The database stored user accounts created during early development when the authentication code was incomplete. The new authentication system creates accounts with proper password hashes and roles, but the old records in the database conflicted with the new code.

Deleting the database forces the app to recreate the default accounts with the correct credentials.
