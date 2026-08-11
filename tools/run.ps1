<#
    Bike Theft Tracker - one-click launcher.

    Run it through run.bat (double-click) or directly:
        powershell -ExecutionPolicy Bypass -File tools\run.ps1

    Starts the portable database, then opens one console window per app so each
    keeps its own logs and can be stopped on its own:

        PostgreSQL  - .localdb, background, port recorded in .localdb\port.txt
        backend     - Django dev server    http://localhost:8001
        frontend    - vite dev server      http://localhost:3001

    Three things this handles that hand-typed commands do not:

    Ports. A supervisor's laptop often already has something on 8001 or 3001.
    Each is probed first and the next free one used, then both sides are told
    where the other landed - the frontend's dev port and its /api proxy target,
    which matters because vite.config.js sets strictPort and would otherwise
    refuse to start rather than moving on its own.

    The database. PostgreSQL is a portable copy under .localdb with no Windows
    service behind it, so nothing starts it at boot. This does, and leaves it
    running for the two dev servers.

    Missing install. If venv or node_modules is absent this runs setup.ps1
    first, so double-clicking run.bat on a fresh clone still ends with a
    working app rather than an error.
#>
[CmdletBinding()]
param(
    # Start the windows but don't open a browser tab.
    [switch]$NoBrowser,

    # Leave PostgreSQL alone (use when you are running your own instance).
    [switch]$NoDb
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

. (Join-Path $PSScriptRoot 'common.ps1')

$RepoRoot    = Split-Path -Parent $PSScriptRoot
$BackendDir  = Join-Path $RepoRoot 'btt-backend'
$FrontendDir = Join-Path $RepoRoot 'btt-frontend'
$VenvPython  = Join-Path $RepoRoot 'venv\Scripts\python.exe'
$EnvFile     = Join-Path $BackendDir '.env'

Update-PathFromRegistry

$CmdExe = Join-Path $env:SystemRoot 'System32\cmd.exe'
if (-not (Test-Path $CmdExe)) { $CmdExe = 'cmd.exe' }

function Resolve-Npm {
    foreach ($name in @('npm.cmd', 'npm')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    foreach ($candidate in @(
        (Join-Path $env:ProgramFiles 'nodejs\npm.cmd'),
        (Join-Path ${env:ProgramFiles(x86)} 'nodejs\npm.cmd'),
        (Join-Path $env:APPDATA 'npm\npm.cmd')
    )) {
        if ($candidate -and (Test-Path $candidate)) { return $candidate }
    }
    return $null
}

Write-Banner @('Bike Theft Tracker - starting') 'Magenta'

# --------------------------------------------------------------------------
# Install on demand, so run.bat works on a fresh clone too
# --------------------------------------------------------------------------
$needsSetup = (-not (Test-Path $VenvPython)) -or
              (-not (Test-Path (Join-Path $FrontendDir 'node_modules'))) -or
              (-not (Test-Path $EnvFile))
if ($needsSetup) {
    Write-Warn 'This looks like a fresh clone - running the installer first.'
    Write-Host ''
    & (Join-Path $PSScriptRoot 'setup.ps1')
    if ($LASTEXITCODE -ne 0) {
        Write-Fail 'Setup did not finish cleanly. Fix the items above and run install.bat again.'
        exit 1
    }
    Write-Host ''
}

foreach ($item in @(
    @{ Path = $VenvPython;                             Label = 'backend virtualenv' },
    @{ Path = (Join-Path $FrontendDir 'node_modules'); Label = 'frontend packages' },
    @{ Path = $EnvFile;                                Label = 'btt-backend\.env' }
)) {
    if (-not (Test-Path $item.Path)) {
        Write-Fail "$($item.Label) is missing - run install.bat"
        exit 1
    }
    Write-Ok $item.Label
}

$Npm = Resolve-Npm
if (-not $Npm) {
    Write-Fail 'npm could not be found, even after re-reading PATH from the registry.'
    Write-Fail 'Install Node.js 18+ from https://nodejs.org, then run install.bat.'
    exit 1
}
Write-Ok "npm ($Npm)"

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
$pg = Get-PgPaths $RepoRoot
$dbPort = Get-EnvValue -Path $EnvFile -Key 'DB_PORT'
if (-not $dbPort) { $dbPort = '5433' }

if ($NoDb) {
    Write-Info "Leaving the database alone (-NoDb). .env points at port $dbPort."
} elseif (-not (Test-PgInstalled $pg)) {
    # No portable copy: the .env may well point at a PostgreSQL the user
    # installed themselves, so this is a note rather than a failure.
    Write-Warn "No portable database in .localdb - assuming your own PostgreSQL is serving port $dbPort."
} elseif (Test-PgRunning $pg) {
    # Believe the server, not the file. If .env and the running cluster have
    # drifted - an interrupted install, a port that was busy last time - Django
    # would otherwise dial a port with nothing behind it and fail at the first
    # query rather than here, where it can be corrected.
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
        Write-Fail 'Running install.bat again usually resolves this.'
        exit 1
    }
}

# --------------------------------------------------------------------------
# Ports
# --------------------------------------------------------------------------
$backendPort  = Get-FreePort 8001 100
$frontendPort = Get-FreePort 3001 100
if ($backendPort -eq 0)  { Write-Fail 'No free port in 8001-8100.'; exit 1 }
if ($frontendPort -eq 0) { Write-Fail 'No free port in 3001-3100.'; exit 1 }
Write-Ok "backend port $backendPort"
Write-Ok "frontend port $frontendPort"

$backendUrl  = "http://localhost:$backendPort"
$frontendUrl = "http://localhost:$frontendPort"

# The frontend calls /api on its own origin and vite proxies that to Django, so
# the proxy target has to follow the backend wherever it landed. FRONTEND_URL in
# .env is what the backend puts in verification and reset emails.
Set-EnvValue -Path $EnvFile -Key 'FRONTEND_URL' -Value $frontendUrl

# --------------------------------------------------------------------------
# Launch
#
# Each window is driven by a small generated .cmd rather than a long inline
# `cmd /k "..."` string: quoting a nested command line through PowerShell -> cmd
# -> the dev server is where these launchers usually break, and a file on disk
# sidesteps all of it. They live in TEMP so nothing lands in the repo.
# --------------------------------------------------------------------------
$launchDir = Join-Path $env:TEMP 'btt-run'
New-Item -ItemType Directory -Force -Path $launchDir | Out-Null

$backendCmd = Join-Path $launchDir 'backend.cmd'
@"
@echo off
title BTT backend
cd /d "$BackendDir"
set "PATH=%SystemRoot%\System32;%PATH%"
echo.
echo   Bike Theft Tracker backend - $backendUrl
echo   API root                   - $backendUrl/api/
echo   Keep this window open. Ctrl+C stops the backend.
echo.
REM --noreload: the file watcher restarts the server on any touched file, which
REM is exactly what you do not want mid-demo.
"$VenvPython" manage.py runserver $backendPort --noreload
echo.
echo   Backend stopped.
pause
"@ | Set-Content -Path $backendCmd -Encoding ASCII

$nodeDir = Split-Path $Npm -Parent
$frontendCmd = Join-Path $launchDir 'frontend.cmd'
@"
@echo off
title BTT frontend
cd /d "$FrontendDir"
REM npm by full path, and its folder on PATH for this window only: vite spawns
REM node itself, so the child processes need to find it even when the machine's
REM PATH has not caught up with a just-installed Node.
set "PATH=$nodeDir;%SystemRoot%\System32;%PATH%"
REM vite.config.js reads both of these. strictPort is on, so the dev port must
REM be one we already know is free rather than left to vite to pick.
set "VITE_DEV_PORT=$frontendPort"
set "VITE_API_PROXY_TARGET=$backendUrl"
echo.
echo   Bike Theft Tracker frontend - $frontendUrl
echo   Keep this window open. Ctrl+C stops the frontend.
echo.
call "$Npm" run dev
echo.
echo   Frontend stopped.
pause
"@ | Set-Content -Path $frontendCmd -Encoding ASCII

Write-Host ''
Write-Info 'Opening the backend window...'
Start-Process -FilePath $CmdExe -ArgumentList '/k',$backendCmd -WorkingDirectory $BackendDir | Out-Null

Write-Info 'Waiting for the backend to answer...'
$ready = $false
foreach ($attempt in 1..60) {
    Start-Sleep -Milliseconds 1000
    try {
        # Any HTTP answer means Django is serving; 401/403/404 are all fine here,
        # they still prove the server is up and routing.
        Invoke-WebRequest -Uri "$backendUrl/api/" -UseBasicParsing -TimeoutSec 3 | Out-Null
        $ready = $true; break
    } catch {
        if ($_.Exception.Response) { $ready = $true; break }
    }
}
if ($ready) {
    Write-Ok 'Backend is up'
} else {
    Write-Warn 'The backend has not answered yet - check its window for errors. Starting the frontend anyway.'
}

Write-Info 'Opening the frontend window...'
Start-Process -FilePath $CmdExe -ArgumentList '/k',$frontendCmd -WorkingDirectory $FrontendDir | Out-Null

Write-Banner @('Bike Theft Tracker is starting') 'Green'
Write-Host ''
Write-Host "     App        $frontendUrl" -ForegroundColor Cyan
Write-Host "     Backend    $backendUrl/api/" -ForegroundColor Cyan
Write-Host "     Admin      $backendUrl/admin/" -ForegroundColor Cyan
Write-Host ''
Write-Host '     Demo logins' -ForegroundColor Gray
Write-Host '       admin@demo.btt                DemoAdmin@2024' -ForegroundColor DarkGray
Write-Host '       authority.karachi@demo.btt    Authority@2024' -ForegroundColor DarkGray
Write-Host '       owner000@demo.btt             Owner@2024'     -ForegroundColor DarkGray
Write-Host '       community@demo.btt            Community@2024' -ForegroundColor DarkGray
Write-Host ''
if ($backendPort -ne 8001)  { Write-Host "     Note: port 8001 was busy, the backend moved to $backendPort." -ForegroundColor Yellow }
if ($frontendPort -ne 3001) { Write-Host "     Note: port 3001 was busy, the frontend moved to $frontendPort." -ForegroundColor Yellow }
Write-Host '     Keep both windows open while using the app.' -ForegroundColor Gray
Write-Host '     kill_all.bat stops everything, database included.' -ForegroundColor Gray
Write-Host ''

if (-not $NoBrowser) {
    # Vite compiles the first page on demand; opening too early shows an error
    # page, which reads as "it did not work".
    Write-Info 'Opening the browser once the first page has compiled...'
    $opened = $false
    foreach ($attempt in 1..60) {
        Start-Sleep -Seconds 1
        try {
            $response = Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) { $opened = $true; break }
        } catch { }
    }
    Start-Process $frontendUrl | Out-Null
    if (-not $opened) {
        Write-Warn 'The page was still compiling - if the tab is blank, refresh it in a few seconds.'
    }
}

exit 0
