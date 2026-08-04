# Bike Theft Tracker — one-shot dev dependencies (Windows-first).
# Creates repo-root venv, installs backend requirements, installs frontend npm deps.

$ErrorActionPreference = "Stop"

function Find-Python312Plus {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($minor in 12..15) {
            $tag = "3.$minor"
            & py "-$tag" -c "import sys; assert sys.version_info >= (3, 12)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return (& py "-$tag" -c "import sys; print(sys.executable)").Trim()
            }
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -c "import sys; assert sys.version_info >= (3, 12); print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return (& python -c "import sys; print(sys.executable)").Trim()
        }
    }
    return $null
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $RepoRoot "venv\Scripts\python.exe"
$ReqFile = Join-Path $RepoRoot "btt-backend\requirements.txt"
$FrontendDir = Join-Path $RepoRoot "btt-frontend"

Write-Host "Repo root: $RepoRoot" -ForegroundColor Cyan

$py = Find-Python312Plus
if (-not $py) {
    Write-Host "Python 3.12+ not found. Install from https://www.python.org/downloads/ (check Add to PATH) or ensure the py launcher can run Python 3.12+." -ForegroundColor Red
    exit 1
}
Write-Host "Using Python: $py" -ForegroundColor Green

if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "Node.js / npm not found. Install LTS from https://nodejs.org/" -ForegroundColor Red
    exit 1
}
Write-Host "Using Node: $(node --version), npm: $(npm --version)" -ForegroundColor Green

if (-not (Test-Path $ReqFile)) {
    Write-Host "Missing requirements file: $ReqFile" -ForegroundColor Red
    exit 1
}

if (Test-Path $VenvPython) {
    # An existing venv on an older interpreter is worse than none: pip will not
    # error on requirements it cannot satisfy, it silently resolves backwards
    # and leaves you on a stale stack that looks installed. Check before reusing.
    & $VenvPython -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $venvVer = (& $VenvPython -c "import sys; print('.'.join(map(str, sys.version_info[:3])))").Trim()
        Write-Host "Existing venv runs Python $venvVer, but this project requires 3.12+." -ForegroundColor Yellow
        Write-Host "Rebuilding it with $py ..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force (Join-Path $RepoRoot "venv")
    }
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment at $RepoRoot\venv ..." -ForegroundColor Cyan
    & $py -m venv (Join-Path $RepoRoot "venv")
}

Write-Host "Upgrading pip and installing backend requirements ..." -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r $ReqFile

if (-not (Test-Path $FrontendDir)) {
    Write-Host "Missing frontend directory: $FrontendDir" -ForegroundColor Red
    exit 1
}

Push-Location $FrontendDir
try {
    if (Test-Path (Join-Path $FrontendDir "package-lock.json")) {
        Write-Host "Running npm ci (package-lock.json present) ..." -ForegroundColor Cyan
        npm ci
    }
    else {
        Write-Host "Running npm install (no package-lock.json) ..." -ForegroundColor Cyan
        npm install
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Done. Next: run scripts\setup_env.bat (or .ps1), install PostgreSQL + PostGIS (Stack Builder on Windows), edit btt-backend\.env, then: cd btt-frontend && npm run test:e2e  (or migrate manually from btt-backend)." -ForegroundColor Green
