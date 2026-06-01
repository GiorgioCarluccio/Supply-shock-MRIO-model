@echo off
REM ============================================================
REM  OpenEconomics — Climate Physical-Risk Dashboard launcher
REM  Double-click this file to start the static dashboard and
REM  open it in your browser at http://localhost:3000
REM ============================================================
cd /d "%~dp0"

if not exist "node_modules" (
  echo Installing frontend dependencies ^(first run only^)...
  call npm install
)

if not exist "public\data\scenario_index.json" (
  echo.
  echo NOTE: frontend data not found in public\data.
  echo Run the export scripts from the repo root first:
  echo   .venv\Scripts\python.exe scripts\export_province_geojson_for_frontend.py
  echo   .venv\Scripts\python.exe scripts\export_dashboard_data_for_frontend.py
  echo.
)

echo Starting the dashboard server in a new window...
start "OE Dashboard server" cmd /k "npm run dev"

echo Waiting for the server to start...
timeout /t 6 >nul

echo Opening http://localhost:3000 ...
start "" "http://localhost:3000"

echo.
echo The dashboard server is running in the other window.
echo Close that window to stop the dashboard.
