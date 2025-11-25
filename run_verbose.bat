@echo off
REM Run PocketSage in verbose development mode with console logging
echo ============================================================
echo PocketSage - VERBOSE DEV MODE
echo ============================================================
echo.
echo This window will show all logging output including:
echo - Button clicks and UI events
echo - Dialog open/close operations  
echo - Database operations
echo - Admin mode activation
echo - Error messages and stack traces
echo.
echo ============================================================
echo.

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

REM Run the verbose version
python run_desktop_verbose.py

pause
