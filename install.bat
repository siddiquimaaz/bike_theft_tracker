@echo off
REM ===========================================================================
REM  Bike Theft Tracker - install everything. Double-click this file.
REM
REM  All the real work is in tools\setup.ps1; this wrapper exists so the whole
REM  thing is one double-click and so the console stays open long enough to
REM  read the result.
REM
REM  Installs Python and Node via winget if they are missing, builds the
REM  virtualenv, downloads a portable PostgreSQL 15 + PostGIS into .localdb\,
REM  creates the database, writes btt-backend\.env, migrates, seeds the demo
REM  data and installs the frontend packages. No administrator rights needed.
REM
REM  Optional switches, if you run it from a terminal:
REM     install.bat -RebuildVenv   rebuild the Python virtualenv from scratch
REM     install.bat -ResetDb       delete and recreate the database cluster
REM     install.bat -NoSeed        skip the demo users and demo data
REM     install.bat -Force         re-download PostgreSQL and PostGIS
REM ===========================================================================
setlocal
cd /d "%~dp0"

REM PowerShell by absolute path: a bare `powershell` fails on machines whose
REM PATH is missing System32, which is exactly the kind of machine this script
REM exists to cope with.
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"

REM Windows tags files that arrived from the internet (a downloaded repo zip),
REM and PowerShell then refuses to run them or nags on every one. Clearing that
REM tag on our own scripts turns a confusing security prompt into nothing.
"%PS%" -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem '%~dp0tools\*.ps1' | Unblock-File" >nul 2>nul

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\setup.ps1" %*
set "RESULT=%ERRORLEVEL%"

echo.
if not "%RESULT%"=="0" (
    echo   Install did not finish cleanly - see the messages above.
    echo   Fixing the item and running this file again is safe: anything that
    echo   already installed is detected and skipped.
)
pause
exit /b %RESULT%
