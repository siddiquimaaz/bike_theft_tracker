<#
    Bike Theft Tracker - run the test suite.

    Run it through run_tests.bat (double-click) or directly:
        powershell -ExecutionPolicy Bypass -File tools\test.ps1

    Makes sure the portable database is up, then runs pytest from btt-backend.
    Every path is derived from this file's own location, so it works on any
    machine and from any working directory.

    Anything after the switches below is passed straight through to pytest:
        run_tests.bat -k fuzzy
        run_tests.bat tests\test_reports.py -vv
#>
# Deliberately NOT [CmdletBinding()]. As an advanced script, PowerShell would
# reject any unrecognised token that starts with a dash - so `run_tests.bat -k
# fuzzy` would fail with "a parameter cannot be found that matches -k" instead
# of handing -k to pytest. Plain scripts collect exactly those leftovers in the
# automatic $args, which is what the pass-through below uses.
param(
    # Skip the coverage report (faster while iterating on one test).
    [switch]$NoCov,

    # Also run the Playwright end-to-end suite afterwards.
    [switch]$E2E
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')

$RepoRoot    = Split-Path -Parent $PSScriptRoot
$BackendDir  = Join-Path $RepoRoot 'btt-backend'
$FrontendDir = Join-Path $RepoRoot 'btt-frontend'
$VenvPython  = Join-Path $RepoRoot 'venv\Scripts\python.exe'
$EnvFile     = Join-Path $BackendDir '.env'

Update-PathFromRegistry
Write-Banner @('Bike Theft Tracker - tests') 'Magenta'

if (-not (Test-Path $VenvPython)) {
    Write-Fail 'The virtualenv is missing - run install.bat first.'
    exit 1
}
Write-Ok 'virtualenv'

# --------------------------------------------------------------------------
# Database
#
# pytest-django creates its test database from template1, which is where
# setup.ps1 enabled PostGIS. Without a running server every test errors on
# connect, which reads as a broken suite rather than a stopped database.
# --------------------------------------------------------------------------
$pg = Get-PgPaths $RepoRoot
$dbPort = Get-EnvValue -Path $EnvFile -Key 'DB_PORT'
if (-not $dbPort) { $dbPort = '5433' }

if (-not (Test-PgInstalled $pg)) {
    Write-Warn "No portable database in .localdb - assuming your own PostgreSQL serves port $dbPort."
} elseif (Test-PgRunning $pg) {
    # Same drift correction as run.ps1 - believe the running server over .env,
    # otherwise every test errors on connect and reads as a broken suite.
    $actual = Get-PgRunningPort $pg
    if ($actual -gt 0 -and "$actual" -ne "$dbPort") {
        Write-Warn "PostgreSQL is on port $actual but .env said $dbPort - correcting .env."
        Set-EnvValue -Path $EnvFile -Key 'DB_PORT' -Value "$actual"
        $dbPort = "$actual"
    }
    Write-Ok "PostgreSQL already running (port $dbPort)"
} else {
    Write-Info "Starting PostgreSQL on port $dbPort ..."
    if (Start-PortablePg $pg ([int]$dbPort)) {
        Write-Ok "PostgreSQL started (port $dbPort)"
    } else {
        Write-Fail "PostgreSQL did not start. Its log is at $($pg.Log)"
        exit 1
    }
}

# --------------------------------------------------------------------------
# pytest
# --------------------------------------------------------------------------
Write-Head 'pytest'

$pytestArgv = @('-m', 'pytest')
if ($NoCov) { $pytestArgv += '--no-cov' }
# Everything the param block did not claim, in the order it was typed.
$passThrough = @($args | Where-Object { $null -ne $_ } | ForEach-Object { "$_" })
if ($passThrough.Count -gt 0) {
    $pytestArgv += $passThrough
    Write-Info "Passing through to pytest: $($passThrough -join ' ')"
}

Push-Location $BackendDir
try {
    $code = Invoke-Native $VenvPython $pytestArgv
} finally {
    Pop-Location
}

if ($code -eq 0) {
    Write-Ok 'Backend tests passed'
} else {
    Write-Fail "pytest exited with code $code"
}

# --------------------------------------------------------------------------
# Playwright, on request
# --------------------------------------------------------------------------
if ($E2E) {
    Write-Head 'Playwright end-to-end'
    if (-not (Test-Path (Join-Path $FrontendDir 'node_modules'))) {
        Write-Warn 'Frontend packages are missing - run install.bat. Skipping the e2e suite.'
    } else {
        $npm = Resolve-Npm -RepoRoot $RepoRoot
        if (-not $npm) {
            Write-Warn 'npm not found - skipping the e2e suite.'
        } else {
            Push-Location $FrontendDir
            try {
                $e2eCode = Invoke-Native $npm @('run', 'test:e2e')
            } finally {
                Pop-Location
            }
            if ($e2eCode -eq 0) { Write-Ok 'End-to-end tests passed' }
            else { Write-Fail "Playwright exited with code $e2eCode"; $code = $e2eCode }
        }
    }
}

Write-Host ''
exit $code
