@echo off
SET NODEJS_PATH=C:\Program Files\nodejs
SET PATH=%NODEJS_PATH%;%PATH%

echo ╔══════════════════════════════════════════════════════════════╗
echo ║          Bike Theft Tracker — E2E Test Runner               ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo IMPORTANT: Both servers must be running before tests start:
echo   Backend  -^>  http://localhost:8000   (Django)
echo   Frontend -^>  http://localhost:3000   (Vite)
echo.
echo If you haven't seeded demo users yet, run first:
echo   cd btt-backend ^&^& python manage.py create_demo_users
echo.
pause

echo Running Django backend tests (pytest)...
echo ─────────────────────────────────────────────────────────────────
call venv\Scripts\activate.bat
cd btt-backend
pytest --tb=short -q
cd ..

echo.
echo Running frontend E2E tests (Playwright)...
echo ─────────────────────────────────────────────────────────────────
cd btt-frontend
npx playwright test
cd ..

echo.
echo Done. Open btt-frontend\playwright-report\index.html for the HTML report.
