@echo off
title Alertrix - Data Preprocessing
echo.
echo ========================================
echo   ALERTRIX - Data Preprocessing Engine
echo ========================================
echo.

:: Activate virtual environment and run preprocessing
cd /d %~dp0backend
call .\venv\Scripts\activate

cd /d %~dp0
echo Running data_prep.py...
echo.

python data_prep.py

echo.
echo ========================================
echo Preprocessing complete!
echo ========================================
pause
