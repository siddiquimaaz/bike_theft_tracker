@echo off
SET ROOT=%~dp0
SET PGCTL=C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe
SET PGDATA=C:\Users\Maaz\localdev\postgresql-15\data

echo ============================================================
echo   Bike Theft Tracker — Kill All Ports, Processes ^& Venvs
echo ============================================================
echo.
echo   Ports targeted:  8000 (Django)  3000 (React)
echo                    5433 (Project PG)  5432 (System PG)
echo   NOT touched:     135, 445, 8733, 49664-49670 (Windows system)
echo ============================================================
echo.

:: ── STEP 1: Deactivate virtual environment (this shell) ───────────────────────
echo [1/7] Deactivating virtual environment...

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
echo [2/7] Stopping project PostgreSQL on port 5433 (clean shutdown)...
"%PGCTL%" -D "%PGDATA%" stop >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo        Project PostgreSQL (port 5433) stopped cleanly.
) else (
    echo        Project PostgreSQL was not running (or already stopped).
)

:: ── STEP 3: Kill port 8000 (Django) ───────────────────────────────────────────
echo.
echo [3/7] Killing port 8000 (Django backend)...
set KILLED=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    if not errorlevel 1 (
        echo        Killed PID %%a on port 8000.
        set KILLED=1
    )
)
if "%KILLED%"=="0" echo        Nothing was running on port 8000.

:: ── STEP 4: Kill port 3000 (React / Vite) ─────────────────────────────────────
echo.
echo [4/7] Killing port 3000 (React frontend)...
set KILLED=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000 " 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    if not errorlevel 1 (
        echo        Killed PID %%a on port 3000.
        set KILLED=1
    )
)
if "%KILLED%"=="0" echo        Nothing was running on port 3000.

:: ── STEP 5: Kill port 5433 (project PostgreSQL — in case pg_ctl stop missed it)
echo.
echo [5/7] Killing port 5433 (project PostgreSQL — safety net)...
set KILLED=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5433 " 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    if not errorlevel 1 (
        echo        Killed PID %%a on port 5433.
        set KILLED=1
    )
)
if "%KILLED%"=="0" echo        Nothing was running on port 5433.

:: ── STEP 6: Kill port 5432 (system/other PostgreSQL instance) ─────────────────
echo.
echo [6/7] Checking port 5432 (system PostgreSQL)...
set KILLED=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5432 " 2^>nul') do (
    echo        Found PID %%a on port 5432 (separate PG install).
    taskkill /PID %%a /F >nul 2>&1
    if not errorlevel 1 (
        echo        Killed PID %%a on port 5432.
        set KILLED=1
    )
)
if "%KILLED%"=="0" echo        Nothing was running on port 5432.

:: ── STEP 7: Kill remaining Python, Node and Postgres processes ─────────────────
echo.
echo [7/7] Killing leftover python.exe, node.exe, postgres.exe...

taskkill /IM python.exe /F >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo        python.exe terminated.
) else (
    echo        No python.exe processes found.
)

taskkill /IM pythonw.exe /F >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo        pythonw.exe terminated.
)

taskkill /IM node.exe /F >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo        node.exe terminated.
) else (
    echo        No node.exe processes found.
)

taskkill /IM postgres.exe /F >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo        postgres.exe terminated.
) else (
    echo        No postgres.exe processes found.
)

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo ============================================================
echo   Done. Everything is stopped and cleared:
echo     [x] Virtual environment deactivated
echo     [x] PostgreSQL (port 5433) stopped
echo     [x] PostgreSQL (port 5432) stopped
echo     [x] Port 8000 (Django) cleared
echo     [x] Port 3000 (React)  cleared
echo     [x] python.exe / node.exe killed
echo.
echo   System ports (135, 445, 8733, 49664+) were NOT touched.
echo.
echo   Run start.bat to bring everything back up fresh.
echo ============================================================
echo.
pause
