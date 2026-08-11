@echo off
REM ===========================================================================
REM  Bike Theft Tracker - kept so existing notes that say "install_frontend.bat"
REM  still work. install.bat installs everything now, frontend included.
REM ===========================================================================
setlocal
cd /d "%~dp0"
echo.
echo   install_frontend.bat now forwards to install.bat, which installs the
echo   backend, the database and the frontend together.
echo.
call "%~dp0install.bat" %*
exit /b %ERRORLEVEL%
