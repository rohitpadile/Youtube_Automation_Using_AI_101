@echo off
title Mr. Nobody Studio Dashboard Launcher
echo ============================================================
echo   🚀 STARTING MR. NOBODY STUDIO DASHBOARD
echo ============================================================
echo.
cd /d "%~dp0"
python app.py
echo.
echo ============================================================
echo   Studio Dashboard & Server Closed Cleanly.
echo ============================================================
timeout /t 3 >nul
