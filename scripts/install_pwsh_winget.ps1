# Installer script for PowerShell 7 via winget (requires admin)
# Run in an elevated PowerShell window:
#   set-executionpolicy bypass -Scope Process -Force; .\scripts\install_pwsh_winget.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host 'Checking for winget...'
if (-not (Get-Command winget -ErrorAction SilentlyContinue)){
    Write-Error 'winget not found. Please install App Installer from the Microsoft Store or use the MSI script instead.'
    exit 1
}

Write-Host 'Installing PowerShell (latest) via winget...'
# Use exact ID to avoid ambiguity and ensure latest stable channel
winget install --id Microsoft.PowerShell -e --silent --accept-package-agreements --accept-source-agreements

Write-Host 'Installation command issued. Verifying pwsh availability...'
Start-Sleep -Seconds 2
if (Get-Command pwsh -ErrorAction SilentlyContinue){
    Write-Host 'pwsh installed. Version:' (pwsh --version)
} else {
    Write-Warning 'pwsh not found in PATH yet. You may need to restart your terminal/IDE.'
}

Write-Host 'Done. After restarting your terminal, run: pwsh --version'