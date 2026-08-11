@echo off
REM ===========================================================================
REM  Bike Theft Tracker - stop everything. Double-click this file.
REM
REM  Stops the frontend, the backend and the portable PostgreSQL in .localdb.
REM  The real work is in tools\stop.ps1, which derives every path from the repo
REM  location - so unlike the version this replaced, there are no absolute
REM  C:\Users\... paths and it works on any machine.
REM
REM  Optional switch, if you run it from a terminal:
REM     kill_all.bat -KeepDb    leave PostgreSQL running
REM ===========================================================================
setlocal
cd /d "%~dp0"

set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\stop.ps1" %*
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
