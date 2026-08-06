@echo off
SET ROOT=%~dp0
SET NODEJS=C:\Program Files\nodejs
SET PGCTL=C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe
SET PGDATA=C:\Users\Maaz\localdev\postgresql-15\data

:: BTT uses 8001/3001. Ports 8000 and 3000 belong to MuseAI on this machine —
:: never kill or bind them here.
SET BACKEND_PORT=8001
SET FRONTEND_PORT=3001

echo ============================================================
echo   Bike Theft Tracker — Clean Start
echo   Backend %BACKEND_PORT%  Frontend %FRONTEND_PORT%  PostgreSQL 5433
echo   (MuseAI on 8000/3000 is left untouched)
echo ============================================================
echo.

:: ── STEP 1: Free BTT's own ports only ────────────────────────────────────────
echo [1/6] Killing any process on port %BACKEND_PORT% (Django)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%BACKEND_PORT% " 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo [2/6] Killing any process on port %FRONTEND_PORT% (React)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%FRONTEND_PORT% " 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: ── STEP 2: Stop PostgreSQL if already running ────────────────────────────────
echo [3/6] Stopping PostgreSQL (if running)...
"%PGCTL%" -D "%PGDATA%" stop >nul 2>&1
ping 127.0.0.1 -n 3 >nul

:: ── STEP 3: Free the project PostgreSQL port ─────────────────────────────────
:: NOTE: this used to run `taskkill /IM python.exe` and `/IM node.exe`, which
:: killed every Python and Node process on the machine — including MuseAI.
:: Only BTT's own ports are cleared now.
echo [4/6] Clearing port 5433 (project PostgreSQL safety net)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5433 " 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
ping 127.0.0.1 -n 2 >nul

:: ── STEP 4: Start PostgreSQL fresh ───────────────────────────────────────────
echo [5/6] Starting PostgreSQL on port 5433...
"%PGCTL%" -D "%PGDATA%" -o "-p 5433" -l "%PGDATA%\pg.log" start
timeout /t 3 /nobreak >nul

:: ── STEP 5: Activate venv + start Django ─────────────────────────────────────
echo [6/6] Activating venv and starting Django + React...
start "BTT Backend" cmd /k "cd /d "%ROOT%" && call venv\Scripts\activate.bat && cd btt-backend && python manage.py runserver localhost:%BACKEND_PORT%"

:: ── STEP 6: Start React frontend ─────────────────────────────────────────────
start "BTT Frontend" cmd /k "SET PATH=%NODEJS%;%PATH% && cd /d "%ROOT%btt-frontend" && npm run dev -- --port %FRONTEND_PORT% --strictPort"

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo ============================================================
echo   All services started cleanly.
echo   Open: http://localhost:%FRONTEND_PORT%
echo   API : http://localhost:%BACKEND_PORT%/api/
echo ============================================================
echo.
echo   Demo logins:
echo     Admin      --  admin@demo.btt               /  DemoAdmin@2024
echo     Authority  --  authority.karachi@demo.btt   /  Authority@2024
echo     Owner      --  owner000@demo.btt            /  Owner@2024
echo     Community  --  community@demo.btt           /  Community@2024
echo.
pause
