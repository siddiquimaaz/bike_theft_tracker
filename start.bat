@echo off
REM ===========================================================================
REM  Bike Theft Tracker - kept so existing notes and docs that say "start.bat"
REM  still work. run.bat is the real launcher now.
REM
REM  The old version of this file hardcoded C:\Users\Maaz\localdev\... for
REM  PostgreSQL, so it only ever ran on one machine. run.bat starts the
REM  portable database in .localdb instead and works anywhere.
REM ===========================================================================
setlocal
cd /d "%~dp0"
echo.
echo   start.bat now forwards to run.bat - see the note inside this file.
echo.
call "%~dp0run.bat" %*
exit /b %ERRORLEVEL%
