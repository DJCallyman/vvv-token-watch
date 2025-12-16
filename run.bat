@echo off
REM VVV Token Watch - Windows launcher script
REM 
REM This script launches the VVV Token Watch application on Windows.
REM It checks for Python installation and virtual environment setup.

echo VVV Token Watch - Starting...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
    echo.
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if requirements are installed
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo Dependencies installed successfully
    echo.
)

REM Check if .env file exists
if not exist ".env" (
    echo WARNING: .env file not found
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy .env.example .env
        echo.
        echo Please edit .env file and add your API keys before running again
        pause
        exit /b 1
    ) else (
        echo ERROR: .env.example not found
        echo Please create a .env file with your configuration
        pause
        exit /b 1
    )
)

REM Run the application
echo Launching VVV Token Watch...
echo.
python run.py

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo Application exited with an error
    pause
)
