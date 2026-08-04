# Run full frontend + backend test suite (PowerShell script)
# Usage: From repository root run in an elevated/developer PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\scripts\run_full_tests.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$logs = Join-Path $root 'test-logs'
New-Item -ItemType Directory -Path $logs -Force | Out-Null

function Check-Command($name){
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)){
        Write-Warning "$name not found in PATH. Install it before running the script."
    }
}

Write-Host "Checking prerequisites..."
Check-Command node
Check-Command npm
Check-Command npx
Check-Command python
Check-Command git

# FRONTEND
Push-Location (Join-Path $root 'btt-frontend')
Write-Host "\n--- FRONTEND: update, install, build, e2e tests ---\n"
try{
    Write-Host 'Updating package.json with npm-check-updates (ncu)...'
    npx npm-check-updates -u --target latest
} catch { Write-Warning "npx ncu failed: $_" }

Write-Host 'Running npm install (no-audit/no-fund to speed up)'
npm install --no-audit --no-fund 2>&1 | Tee-Object -FilePath (Join-Path $logs 'frontend-npm-install.log')

Write-Host 'Installing Playwright browsers...'
try{ npx playwright install --with-deps 2>&1 | Tee-Object -FilePath (Join-Path $logs 'playwright-install.log') } catch { Write-Warning "Playwright install failed: $_" }

Write-Host 'Building frontend...'
npm run build 2>&1 | Tee-Object -FilePath (Join-Path $logs 'frontend-build.log')

Write-Host 'Running Playwright E2E...'
# run headless by default
npm run test:e2e 2>&1 | Tee-Object -FilePath (Join-Path $logs 'frontend-e2e.log')
Pop-Location

# BACKEND
Push-Location (Join-Path $root 'btt-backend')
Write-Host "\n--- BACKEND: venv, install, migrate, tests ---\n"

$venvPath = Join-Path $PWD '.venv'
if (-Not (Test-Path $venvPath)){
    Write-Host 'Creating virtual environment .venv'
    python -m venv .venv
}

Write-Host 'Activating venv'
$activate = Join-Path $venvPath 'Scripts\Activate.ps1'
if (Test-Path $activate){
    & $activate
} else {
    Write-Warning "Activation script not found at $activate"
}

Write-Host 'Upgrading pip/setuptools/wheel'
python -m pip install -U pip setuptools wheel 2>&1 | Tee-Object -FilePath (Join-Path $logs 'backend-pip-upgrade.log')

Write-Host 'Installing requirements'
python -m pip install -r requirements.txt 2>&1 | Tee-Object -FilePath (Join-Path $logs 'backend-pip-install.log')

Write-Host 'Applying migrations'
python manage.py migrate 2>&1 | Tee-Object -FilePath (Join-Path $logs 'backend-migrate.log')

Write-Host 'Running pytest'
pytest -q 2>&1 | Tee-Object -FilePath (Join-Path $logs 'backend-pytest.log')
Pop-Location

Write-Host "\nAll done. Logs saved in: $logs\nPlease upload the logs (frontend-build.log, frontend-e2e.log, backend-pytest.log, etc.) so I can diagnose failures and produce fixes."
