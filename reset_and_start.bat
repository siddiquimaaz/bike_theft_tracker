@echo off
setlocal EnableExtensions EnableDelayedExpansion

set ROOT=%~dp0
set PYTHON_EXE=%ROOT%venv\Scripts\python.exe
set PGCTL=C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe
set PGDATA=C:\Users\Maaz\localdev\postgresql-15\data
set FRONTEND_DIR=%ROOT%btt-frontend
set BACKEND_DIR=%ROOT%btt-backend

echo ============================================================
echo   Bike Theft Tracker - Full Reset and Start
echo ============================================================
echo.

if not exist "%PYTHON_EXE%" (
  echo [ERROR] Python venv not found: %PYTHON_EXE%
  echo Create it first: python -m venv venv
  exit /b 1
)

if not exist "%PGCTL%" (
  echo [ERROR] pg_ctl not found: %PGCTL%
  echo Update PGCTL path in this script.
  exit /b 1
)

echo [1/9] Stopping Django/Frontend listeners on ports 8000 and 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " 2^>nul') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000 " 2^>nul') do taskkill /PID %%a /F >nul 2>&1

echo [2/9] Stopping PostgreSQL (if running)...
"%PGCTL%" -D "%PGDATA%" stop >nul 2>&1
ping 127.0.0.1 -n 2 >nul

echo [3/9] Clearing local test/cache artifacts...
if exist "%BACKEND_DIR%\.pytest_cache" rmdir /s /q "%BACKEND_DIR%\.pytest_cache"
if exist "%BACKEND_DIR%\htmlcov" rmdir /s /q "%BACKEND_DIR%\htmlcov"
if exist "%BACKEND_DIR%\.coverage" del /f /q "%BACKEND_DIR%\.coverage" >nul 2>&1
if exist "%FRONTEND_DIR%\test-results" rmdir /s /q "%FRONTEND_DIR%\test-results"

echo [4/9] Starting PostgreSQL on port 5433...
"%PGCTL%" -D "%PGDATA%" -o "-p 5433" -l "%PGDATA%\pg.log" start
if errorlevel 1 (
  echo [ERROR] Failed to start PostgreSQL.
  exit /b 1
)
ping 127.0.0.1 -n 3 >nul

echo [5/9] Flushing DB data and applying migrations...
pushd "%BACKEND_DIR%"
"%PYTHON_EXE%" manage.py reset_db --noinput --force
if errorlevel 1 (
  echo [ERROR] reset_db failed.
  popd
  exit /b 1
)
echo        Generating any missing migrations...
"%PYTHON_EXE%" manage.py makemigrations
"%PYTHON_EXE%" manage.py migrate
if errorlevel 1 (
  echo [ERROR] migrate failed.
  popd
  exit /b 1
)
"%PYTHON_EXE%" manage.py check
if errorlevel 1 (
  echo [ERROR] django check failed.
  popd
  exit /b 1
)
popd

set CREATE_SUPERUSER=n
set SEED_DEMO=n

set /p CREATE_SUPERUSER="[6/9] Create superuser now? (y/N): "
if /I "%CREATE_SUPERUSER%"=="y" (
  pushd "%BACKEND_DIR%"
  "%PYTHON_EXE%" manage.py createsuperuser
  popd
)

set /p SEED_DEMO="[7/9] Seed demo users/data now? (y/N): "
if /I "%SEED_DEMO%"=="y" (
  pushd "%BACKEND_DIR%"
  "%PYTHON_EXE%" manage.py create_demo_users --reset
  "%PYTHON_EXE%" manage.py seed_demo_data --clear
  popd
)

echo [8/9] Starting backend server...
start "BTT Backend" cmd /k "cd /d "%BACKEND_DIR%" && "%PYTHON_EXE%" manage.py runserver 0.0.0.0:8000"

echo [9/9] Starting frontend server...
start "BTT Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev"

echo.
echo ============================================================
echo   Done. Fresh environment is up.
echo   Frontend: http://localhost:3000/
echo   Backend : http://localhost:8000/api/
echo ============================================================
echo.
pause
