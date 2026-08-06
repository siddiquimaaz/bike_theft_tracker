@echo off
SET ROOT=%~dp0
SET PGCTL=C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe
SET PGDATA=C:\Users\Maaz\localdev\postgresql-15\data

:: BTT uses 8001/3001. Ports 8000 and 3000 belong to MuseAI on this machine.
SET BACKEND_PORT=8001
SET FRONTEND_PORT=3001

echo ============================================================
echo   Bike Theft Tracker — Kill BTT Ports, Processes ^& Venvs
echo ============================================================
echo.
echo   Ports targeted:  %BACKEND_PORT% (Django)  %FRONTEND_PORT% (React)
echo                    5433 (Project PG)
echo   NOT touched:     8000/3000 (MuseAI), 5432 (system PG),
echo                    135, 445, 8733, 49664-49670 (Windows system)
echo ============================================================
echo.

:: ── STEP 1: Deactivate virtual environment (this shell) ───────────────────────
echo [1/5] Deactivating virtual environment...

if defined VIRTUAL_ENV (
    echo        Active venv detected: %VIRTUAL_ENV%
    if exist "%ROOT%venv\Scripts\deactivate.bat" (
        call "%ROOT%venv\Scripts\deactivate.bat"
        echo        Deactivated: %ROOT%venv
    )
) else (
    if exist "%ROOT%venv\Scripts\deactivate.bat" (
        call "%ROOT%venv\Scripts\deactivate.bat" >nul 2>&1
    )
    echo        No active venv in this shell.
)

:: Clear all venv-related environment variables
set VIRTUAL_ENV=
set VIRTUAL_ENV_PROMPT=
set PYTHONHOME=
echo        Venv environment variables cleared.
echo        NOTE: Other open terminals need 'deactivate' or close them manually.

:: ── STEP 2: Stop project PostgreSQL cleanly (port 5433) ───────────────────────
echo.
echo [2/5] Stopping project PostgreSQL on port 5433 (clean shutdown)...
"%PGCTL%" -D "%PGDATA%" stop >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo        Project PostgreSQL (port 5433) stopped cleanly.
) else (
    echo        Project PostgreSQL was not running (or already stopped).
)

:: ── STEP 3: Kill BTT backend port ─────────────────────────────────────────────
echo.
echo [3/5] Killing port %BACKEND_PORT% (Django backend)...
set KILLED=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%BACKEND_PORT% " 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    if not errorlevel 1 (
        echo        Killed PID %%a on port %BACKEND_PORT%.
        set KILLED=1
    )
)
if "%KILLED%"=="0" echo        Nothing was running on port %BACKEND_PORT%.

:: ── STEP 4: Kill BTT frontend port ────────────────────────────────────────────
echo.
echo [4/5] Killing port %FRONTEND_PORT% (React frontend)...
set KILLED=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%FRONTEND_PORT% " 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    if not errorlevel 1 (
        echo        Killed PID %%a on port %FRONTEND_PORT%.
        set KILLED=1
    )
)
if "%KILLED%"=="0" echo        Nothing was running on port %FRONTEND_PORT%.

:: ── STEP 5: Kill port 5433 (project PostgreSQL — pg_ctl stop safety net) ──────
:: NOTE: this script used to end with `taskkill /IM python.exe`, `/IM node.exe`
:: and `/IM postgres.exe`, which killed every such process on the machine —
:: including MuseAI and the system PostgreSQL on 5432. Only BTT's own ports are
:: cleared now; nothing is killed by image name.
echo.
echo [5/5] Killing port 5433 (project PostgreSQL — safety net)...
set KILLED=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5433 " 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    if not errorlevel 1 (
        echo        Killed PID %%a on port 5433.
        set KILLED=1
    )
)
if "%KILLED%"=="0" echo        Nothing was running on port 5433.

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo ============================================================
echo   Done. BTT is stopped and cleared:
echo     [x] Virtual environment deactivated
echo     [x] PostgreSQL (port 5433) stopped
echo     [x] Port %BACKEND_PORT% (Django) cleared
echo     [x] Port %FRONTEND_PORT% (React)  cleared
echo.
echo   Left running on purpose: MuseAI (8000/3000), system PG (5432),
echo   and Windows system ports (135, 445, 8733, 49664+).
echo.
echo   Run start.bat to bring everything back up fresh.
echo ============================================================
echo.
pause
