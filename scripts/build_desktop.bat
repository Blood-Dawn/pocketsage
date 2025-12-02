@echo off
REM Build PocketSage desktop application using flet pack

echo Building PocketSage desktop application...

REM Ensure we're in the project root
cd /d "%~dp0\.."

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -e ".[dev]"

REM Run tests
echo Running tests...
pytest || echo Warning: Some tests failed

REM Build desktop app
echo Building desktop application with flet pack...
flet pack run_desktop.py ^
    --name "PocketSage" ^
    --product-name "PocketSage" ^
    --product-version "0.1.0" ^
    --file-description "Offline Finance & Habit Tracker"

echo Build complete! Binary should be in dist\ directory
echo Windows: dist\PocketSage\PocketSage.exe
