@echo off
SET NODEJS_PATH=C:\Program Files\nodejs
SET PATH=%NODEJS_PATH%;%PATH%

echo Starting PostgreSQL...
C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe -D C:\Users\Maaz\localdev\postgresql-15\data -o "-p 5433" -l C:\Users\Maaz\localdev\postgresql-15\data\pg.log start

echo Activating venv and starting Django on port 8000...
start "Django Backend" cmd /k "call venv\Scripts\activate.bat && cd btt-backend && python manage.py runserver"

echo Starting React frontend on port 3000...
start "React Frontend" cmd /k "SET PATH=%NODEJS_PATH%;%PATH% && cd btt-frontend && npm run dev"

echo.
echo Both servers are starting:
echo   Backend  -^>  http://localhost:8000/api/
echo   Frontend -^>  http://localhost:3000/
echo.
echo Open http://localhost:3000 in your browser.
