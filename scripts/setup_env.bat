@echo off
setlocal
set "BACKEND=%~dp0..\btt-backend"
set "EXAMPLE=%BACKEND%\.env.example"
set "ENVFILE=%BACKEND%\.env"

if not exist "%EXAMPLE%" (
    echo ERROR: Missing "%EXAMPLE%"
    pause
    exit /b 1
)

if exist "%ENVFILE%" (
    echo btt-backend\.env already exists — left unchanged.
) else (
    copy /Y "%EXAMPLE%" "%ENVFILE%" >nul
    echo Created btt-backend\.env from .env.example
)

echo.
echo Next steps:
echo   1. Edit btt-backend\.env — set SECRET_KEY, DB_*, and optional email/Twilio.
echo   2. Install PostgreSQL 15 + PostGIS and create the database/user (see docs\README_NEWMACHINE.md).
echo   3. On Windows, install GDAL if GeoDjango cannot find DLLs (same doc).
echo   4. Activate repo venv:  venv\Scripts\activate.bat
echo   5. cd btt-backend ^&^& python manage.py migrate ^&^& python manage.py runserver
echo.
