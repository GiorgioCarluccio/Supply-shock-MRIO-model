@echo off
REM ============================================================
REM  OpenEconomics - Climate Physical-Risk Dashboard launcher
REM  Double-click this file to start the static dashboard and
REM  open it in your browser at http://localhost:3000
REM ============================================================
setlocal
set "APP_URL=http://localhost:3000/"
cd /d "%~dp0"

if not exist "node_modules" (
  echo Installing frontend dependencies ^(first run only^)...
  call npm install
  if errorlevel 1 (
    echo npm install failed.
    pause
    exit /b 1
  )
)

if not exist "public\data\scenario_index.json" (
  echo.
  echo NOTE: frontend data not found in public\data.
  echo Run the export scripts from the repo root first:
  echo   .venv\Scripts\python.exe scripts\export_province_geojson_for_frontend.py
  echo   .venv\Scripts\python.exe scripts\export_dashboard_data_for_frontend.py
  echo.
)

call :probe
if errorlevel 1 (
  call :clean_cache
  if errorlevel 1 exit /b 1
  echo Starting the dashboard server in a new window...
  start "OE Dashboard server" /D "%~dp0" cmd /k npm run dev
) else (
  echo Dashboard server is already running.
)

echo Waiting for the dashboard to respond...
for /l %%I in (1,1,45) do (
  call :probe
  if not errorlevel 1 goto open_dashboard
  timeout /t 2 /nobreak >nul
)

echo.
echo The dashboard did not respond at %APP_URL%.
echo Check the server window for errors, then run this launcher again.
pause
exit /b 1

:open_dashboard
echo Opening %APP_URL% ...
start "" "%APP_URL%"

echo.
echo The dashboard is available at %APP_URL%.
echo If this launcher opened a server window, close that window to stop it.
exit /b 0

:probe
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%APP_URL%' -TimeoutSec 2; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } } catch {}; exit 1"
exit /b %ERRORLEVEL%

:clean_cache
if exist ".next" (
  echo Cleaning Next.js dev cache...
  attrib -R -S -H ".next" /S /D >nul 2>nul
  rmdir /S /Q ".next"
  if exist ".next" (
    echo Could not remove .next. Close any dashboard/server windows and try again.
    pause
    exit /b 1
  )
)
exit /b 0
