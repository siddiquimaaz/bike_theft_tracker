@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_all.ps1"
if errorlevel 1 (
    echo.
    echo Install failed — see messages above.
    pause
    exit /b 1
)
exit /b 0
