@echo off
REM ===========================================================================
REM  Bike Theft Tracker - wipe the database and start fresh.
REM
REM  Stops everything, rebuilds the database cluster from scratch, re-applies
REM  migrations, re-seeds the demo users and demo data, then starts the app.
REM  Use this before a demo when the data has been messed about with.
REM
REM  The old version of this file hardcoded C:\Users\Maaz\localdev\... for
REM  PostgreSQL. This one drives the portable database in .localdb and works
REM  on any machine.
REM
REM  This DELETES all local data. It does not touch anything outside .localdb.
REM ===========================================================================
setlocal
cd /d "%~dp0"

set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"

echo.
echo   This deletes the local database and re-seeds the demo data.
echo   Press Ctrl+C to cancel, or
pause

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\stop.ps1"
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\setup.ps1" -ResetDb
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo   Reset did not finish cleanly - see the messages above.
    pause
    exit /b %ERRORLEVEL%
)

call "%~dp0run.bat" %*
exit /b %ERRORLEVEL%
