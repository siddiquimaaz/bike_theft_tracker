@echo off
SET ROOT=%~dp0
SET NODEJS=C:\Program Files\nodejs
SET PGCTL=C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe
SET PGDATA=C:\Users\Maaz\localdev\postgresql-15\data

echo ============================================================
echo   Bike Theft Tracker — Clean Start
echo ============================================================
echo.

:: ── STEP 1: Kill anything already using ports 8000 and 3000 ──────────────────
echo [1/6] Killing any process on port 8000 (Django)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo [2/6] Killing any process on port 3000 (React)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000 " 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: ── STEP 2: Stop PostgreSQL if already running ────────────────────────────────
echo [3/6] Stopping PostgreSQL (if running)...
"%PGCTL%" -D "%PGDATA%" stop >nul 2>&1
ping 127.0.0.1 -n 3 >nul

:: ── STEP 3: Deactivate any active venv (kill leftover python processes) ───────
echo [4/6] Clearing any active virtual environment...
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1
ping 127.0.0.1 -n 2 >nul

:: ── STEP 4: Start PostgreSQL fresh ───────────────────────────────────────────
echo [5/6] Starting PostgreSQL on port 5433...
"%PGCTL%" -D "%PGDATA%" -o "-p 5433" -l "%PGDATA%\pg.log" start
timeout /t 3 /nobreak >nul

:: ── STEP 5: Activate venv + start Django ─────────────────────────────────────
echo [6/6] Activating venv and starting Django + React...
start "BTT Backend" cmd /k "cd /d "%ROOT%" && call venv\Scripts\activate.bat && cd btt-backend && python manage.py runserver"

:: ── STEP 6: Start React frontend ─────────────────────────────────────────────
start "BTT Frontend" cmd /k "SET PATH=%NODEJS%;%PATH% && cd /d "%ROOT%btt-frontend" && npm run dev"

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo ============================================================
echo   All services started cleanly.
echo   Open: http://localhost:3000
echo ============================================================
echo.
echo   Demo logins:
echo     Admin      --  admin@demo.btt               /  DemoAdmin@2024
echo     Authority  --  authority.karachi@demo.btt   /  Authority@2024
echo     Owner      --  owner000@demo.btt            /  Owner@2024
echo     Community  --  community@demo.btt           /  Community@2024
echo.
pause
