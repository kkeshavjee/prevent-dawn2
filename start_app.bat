@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==========================================
echo      Antigravity Startup Helper
echo ==========================================
echo.

:: 1. Check for Node.js
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed or not in your PATH.
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

:: 2. Check for Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

:: 3. Setup Backend Virtual Environment
echo [1/3] Setting up Backend...
if not exist "backend\venv" (
    echo Creating virtual environment...
    python -m venv backend\venv
)

:: Install/Update requirements
echo Installing/Updating backend dependencies...
call backend\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

:: 4. Setup Frontend
echo.
echo [2/3] Setting up Frontend...
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

:: 5. Launch Application
echo.
echo [3/3] Starting Application...

:: Backend
echo Starting Backend in a new window...
start "Antigravity Backend" cmd /k "backend\venv\Scripts\activate && python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"

:: Wait a moment for backend to initialize
timeout /t 2 /nobreak >nul

:: Frontend
echo Starting Frontend in a new window...
start "Antigravity Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ==========================================
echo Application is starting!
echo.
echo Backend logs: Check the 'Antigravity Backend' window
echo Frontend logs: Check the 'Antigravity Frontend' window
echo.
echo Backend URL:  http://127.0.0.1:8000
echo Frontend URL: http://127.0.0.1:5173
echo ==========================================
echo.
pause
