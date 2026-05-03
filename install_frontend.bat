@echo off
SET NODEJS_PATH=C:\Program Files\nodejs
SET PATH=%NODEJS_PATH%;%PATH%

echo ── Installing frontend dependencies ──────────────────────────────
cd btt-frontend
npm install
if %ERRORLEVEL% NEQ 0 ( echo npm install failed. & exit /b 1 )

echo.
echo ── Installing Playwright browsers ────────────────────────────────
npx playwright install chromium
if %ERRORLEVEL% NEQ 0 ( echo Playwright install failed. & exit /b 1 )

echo.
echo ── All done! ────────────────────────────────────────────────────
echo   Run:  start.bat               to start both servers
echo   Run:  run_tests.bat          to run E2E tests
echo.
