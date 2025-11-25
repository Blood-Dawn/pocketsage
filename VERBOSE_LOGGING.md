# PocketSage Verbose Development Mode

## Quick Start

### Windows
Run the app with verbose console logging:
```batch
run_verbose.bat
```

Or manually:
```batch
python run_desktop_verbose.py
```

### Linux/macOS
```bash
python run_desktop_verbose.py
```

## What You'll See

The verbose mode logs **everything** to the console, including:

### Button Clicks
- Every button click is logged with the button name
- Admin actions (Seed, Reset, Export, Backup, Restore)
- Dialog open/close events
- Save button clicks in all dialogs

### Navigation
- Route changes (`/dashboard` -> `/admin`)
- Admin mode enabled/disabled status
- View building success/failure
- Missing route handlers

### Admin Mode Issues
- When admin mode is toggled
- Why admin view shows gray screen (will see view build errors)
- Button handler execution
- Database operation progress

### Dialog Operations
- Dialog opening
- Dialog closing  
- Field validation
- Save operation start/completion
- Error messages

## Example Output

```
================================================================================
PocketSage - VERBOSE DEV MODE
All button clicks, dialog operations, and errors will be logged below
================================================================================

[10:15:23] INFO     [pocketsage.desktop.app:32] PocketSage desktop application starting
[10:15:23] DEBUG    [pocketsage.desktop.navigation:30] Registering route: /dashboard
[10:15:23] DEBUG    [pocketsage.desktop.navigation:30] Registering route: /ledger
[10:15:23] DEBUG    [pocketsage.desktop.navigation:30] Registering route: /admin
[10:15:24] INFO     [pocketsage.desktop.navigation:36] Route change requested: /dashboard
[10:15:24] DEBUG    [pocketsage.desktop.navigation:49] Building view for route: /dashboard
[10:15:24] INFO     [pocketsage.desktop.navigation:56] Successfully loaded view for route: /dashboard
```

When you click a button, you'll see:
```
[10:16:45] INFO     [pocketsage.desktop.views.admin:120] Seed button clicked
[10:16:45] INFO     [pocketsage.desktop.views.admin:123] Starting heavy seed
[10:16:46] INFO     [pocketsage.desktop.views.admin:125] Heavy seed completed: 3650 transactions
```

## Debugging Admin Mode Gray Screen

With verbose logging enabled, when you switch to admin mode, look for:

1. **Admin mode toggle**:
   ```
   Route change requested: /admin (admin_mode=True)
   ```

2. **View building**:
   ```
   Building admin view (admin_mode=True)
   Fetching database statistics
   ```

3. **Errors** (what's likely causing the gray screen):
   ```
   ERROR: Failed to build view for route /admin: [error message]
   ```

The error message will tell you exactly what's wrong!

## Logging Levels

The verbose mode uses these log levels:

- **DEBUG**: Detailed trace (dialog operations, field values)
- **INFO**: Important events (button clicks, route changes, operations complete)
- **WARNING**: Unexpected but handled (admin blocked, file not selected)  
- **ERROR**: Failures (view build errors, save failures)

## Files Modified

The logging was added to:
- `src/pocketsage/logging_config.py` - Console formatter with DEBUG level
- `src/pocketsage/config.py` - DEV_MODE default = True
- `src/pocketsage/desktop/views/admin.py` - All admin button handlers
- `src/pocketsage/desktop/views/ledger.py` - Transaction dialog operations
- `src/pocketsage/desktop/navigation.py` - Route changes and view building

## Disabling Verbose Mode

To run normally without console spam:

1. Set environment variable:
   ```batch
   set POCKETSAGE_DEV_MODE=false
   python run_desktop.py
   ```

2. Or just use:
   ```batch
   python run_desktop.py
   ```

## Next Steps After Finding the Problem

Once you see the error in the console:

1. Copy the error message
2. Search for that error in the codebase
3. Check the file and line number from the log
4. The stack trace will show the exact problem

For admin gray screen specifically, look for errors during:
- `Building admin view`
- `Fetching database statistics`
- Any missing database tables or columns
