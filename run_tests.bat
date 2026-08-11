@echo off
REM ===========================================================================
REM  Bike Theft Tracker - run the test suite. Double-click this file.
REM
REM  Starts the portable PostgreSQL if it is not up, then runs pytest.
REM  The real work is in tools\test.ps1, which derives every path from the repo
REM  location - so unlike the version this replaced, there are no absolute
REM  C:\Users\... paths and it works on any machine.
REM
REM  Optional switches, if you run it from a terminal:
REM     run_tests.bat -NoCov         skip the coverage report
REM     run_tests.bat -E2E           also run the Playwright suite
REM     run_tests.bat -k fuzzy       anything else goes straight to pytest
REM ===========================================================================
setlocal
cd /d "%~dp0"

set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\test.ps1" %*
set "RESULT=%ERRORLEVEL%"
echo.
pause
exit /b %RESULT%
