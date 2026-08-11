@echo off
REM ===========================================================================
REM  Bike Theft Tracker - start the app. Double-click this file.
REM
REM  Starts the portable database, opens one window for the backend and one for
REM  the frontend, then opens the app in your browser. If dependencies are not
REM  installed yet it runs the installer first, so this file alone is enough on
REM  a fresh clone.
REM
REM  Optional switches, if you run it from a terminal:
REM     run.bat -NoBrowser   don't open a browser tab
REM     run.bat -NoDb        don't touch PostgreSQL (use your own instance)
REM ===========================================================================
setlocal
cd /d "%~dp0"

set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"

REM Same internet-tag clearing as install.bat - see the note there.
"%PS%" -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem '%~dp0tools\*.ps1' | Unblock-File" >nul 2>nul

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\run.ps1" %*
set "RESULT=%ERRORLEVEL%"

if not "%RESULT%"=="0" (
    echo.
    echo   Bike Theft Tracker could not start - see the messages above.
    pause
)
exit /b %RESULT%
