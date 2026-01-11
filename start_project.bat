@echo off
title Alertrix - Project Launcher
echo.
echo ========================================
echo    ALERTRIX - Anomaly Detection System
echo ========================================
echo.
echo Starting Backend and Frontend servers...
echo.

:: Start Backend Server in new terminal
echo [1/2] Launching Backend Server (FastAPI)...
start "Alertrix Backend" cmd /k "cd /d %~dp0backend && .\venv\Scripts\activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

:: Wait a moment for backend to initialize
timeout /t 3 /nobreak > nul

:: Start Frontend Server in new terminal
echo [2/2] Launching Frontend Server (Vite)...
start "Alertrix Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo Both servers are starting...
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Press any key to exit this launcher...
pause > nul
