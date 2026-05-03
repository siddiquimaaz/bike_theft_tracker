@echo off
setlocal EnableExtensions EnableDelayedExpansion

set ROOT=%~dp0
set PYTHON_EXE=%ROOT%venv\Scripts\python.exe
set PGCTL=C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe
set PGDATA=C:\Users\Maaz\localdev\postgresql-15\data
set NODEJS_PATH=C:\Program Files\nodejs
set PATH=%NODEJS_PATH%;%PATH%

echo ============================================================
echo   Bike Theft Tracker -- Test Runner
echo ============================================================
echo.

:: ── Sanity checks ─────────────────────────────────────────────────────────────
if not exist "%PYTHON_EXE%" (
  echo [ERROR] Python venv not found: %PYTHON_EXE%
  echo Create it first: python -m venv venv ^&^& venv\Scripts\pip install -r btt-backend\requirements.txt
  pause & exit /b 1
)
if not exist "%PGCTL%" (
  echo [ERROR] pg_ctl not found: %PGCTL%
  echo Update PGCTL path in this script.
  pause & exit /b 1
)

:: ── Start PostgreSQL if not already running ────────────────────────────────────
echo [1/3] Ensuring PostgreSQL is running on port 5433...
"%PGCTL%" status -D "%PGDATA%" >nul 2>&1
if errorlevel 1 (
  echo        Starting PostgreSQL...
  "%PGCTL%" -D "%PGDATA%" -o "-p 5433" -l "%PGDATA%\pg.log" start
  if errorlevel 1 (
    echo [ERROR] Failed to start PostgreSQL.
    pause & exit /b 1
  )
  ping 127.0.0.1 -n 3 >nul
) else (
  echo        PostgreSQL already running.
)

:: ── Django backend tests (pytest) ─────────────────────────────────────────────
echo.
echo [2/3] Running Django backend tests (381 tests, 90%%+ coverage required)...
echo        This takes ~10-11 minutes.
echo ─────────────────────────────────────────────────────────────────────────────
pushd "%ROOT%btt-backend"
"%PYTHON_EXE%" -m pytest tests/ --tb=short
set BACKEND_EXIT=%ERRORLEVEL%
popd

if %BACKEND_EXIT% EQU 0 (
  echo.
  echo [PASS] All backend tests passed.
) else (
  echo.
  echo [FAIL] Backend tests failed (exit code %BACKEND_EXIT%).
)

:: ── Optional E2E tests (Playwright) ───────────────────────────────────────────
echo.
echo [3/3] Frontend E2E tests (Playwright) -- optional.
echo        Both servers must be running first (start.bat or reset_and_start.bat).
echo.
set /p RUN_E2E="Run Playwright E2E tests now? (y/N): "
if /I "!RUN_E2E!"=="y" (
  pushd "%ROOT%btt-frontend"
  npx playwright test
  set E2E_EXIT=!ERRORLEVEL!
  popd
  if !E2E_EXIT! EQU 0 (
    echo [PASS] E2E tests passed.
    echo        Open btt-frontend\playwright-report\index.html for the HTML report.
  ) else (
    echo [FAIL] E2E tests failed. Check btt-frontend\playwright-report\index.html.
  )
) else (
  echo        Skipped E2E tests.
)

echo.
echo ============================================================
echo   Done.
echo   HTML coverage report: btt-backend\htmlcov\index.html
echo ============================================================
echo.
pause
