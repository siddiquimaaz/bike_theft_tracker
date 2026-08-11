<#
    Bike Theft Tracker - one-click setup.

    Run it through install.bat (double-click) or directly:
        powershell -ExecutionPolicy Bypass -File tools\setup.ps1

    What it does, in order, on a machine that has just cloned the repo:
        1. Python 3.12+         - installs via winget if absent
        2. Node.js 18+          - installs via winget if absent
        3. venv                 - virtualenv + pip install -r requirements.lock.txt
        4. .localdb\pgsql       - portable PostgreSQL 15, downloaded, no admin
        5. PostGIS              - unpacked over the same folder
        6. .localdb\data        - initdb, server started on a free port
        7. role + database      - bttadmin / bikethefttracker, PostGIS enabled
        8. btt-backend\.env     - seeded from .env.example, DB values filled in
        9. migrate + seed       - schema, demo users, demo data
       10. btt-frontend         - npm ci
       11. verify               - Django checks and a real query against the DB

    Everything is idempotent: anything already present is detected and skipped,
    so re-running after a failure only redoes the part that failed.

    Nothing needs administrator rights. PostgreSQL is a portable copy under
    .localdb\ inside this repo - no system service, no PATH edits, and deleting
    that one folder removes the database completely.
#>
[CmdletBinding()]
param(
    # Delete and rebuild the virtualenv even if it looks healthy.
    [switch]$RebuildVenv,

    # Delete and rebuild the database cluster. Destroys all local data.
    [switch]$ResetDb,

    # Skip the demo users and demo data seeding step.
    [switch]$NoSeed,

    # Re-download PostgreSQL and PostGIS even if already unpacked.
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
# PS 5.1 renders a progress bar per byte range on Invoke-WebRequest, turning a
# 60-second download into a 10-minute one. The download helper prints its own.
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

. (Join-Path $PSScriptRoot 'common.ps1')

$RepoRoot    = Split-Path -Parent $PSScriptRoot
$BackendDir  = Join-Path $RepoRoot 'btt-backend'
$FrontendDir = Join-Path $RepoRoot 'btt-frontend'
$VenvDir     = Join-Path $RepoRoot 'venv'
$VenvPython  = Join-Path $VenvDir 'Scripts\python.exe'
$EnvFile     = Join-Path $BackendDir '.env'
$EnvExample  = Join-Path $BackendDir '.env.example'
$CacheDir    = Join-Path $env:TEMP 'btt-setup'
# Checked before the network. Drop the PostgreSQL and PostGIS archives here to
# install on a machine with no internet - see vendor\README.md.
$VendorDir   = Join-Path $RepoRoot 'vendor'

# Pinned, and verified reachable at the time of writing. Both are plain zips
# with no installer and no admin requirement.
$PgUrl     = 'https://get.enterprisedb.com/postgresql/postgresql-15.12-1-windows-x64-binaries.zip'
$PostgisUrl = 'https://download.osgeo.org/postgis/windows/pg15/postgis-bundle-pg15-3.6.2x64.zip'
# The current-release folder only ever holds the newest build; when it rolls
# over, the previous one stays reachable under archive/.
$PostgisFallbackUrl = 'https://download.osgeo.org/postgis/windows/pg15/archive/postgis-bundle-pg15-3.5.3x64.zip'

$DbName = 'bikethefttracker'
$DbUser = 'bttadmin'

Update-PathFromRegistry
New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null

Write-Banner @('Bike Theft Tracker - installing everything needed to run locally') 'Magenta'

# --------------------------------------------------------------------------
# 1. Python
# --------------------------------------------------------------------------
Write-Head '1/11  Python 3.12+'

function Resolve-Python {
    # Django 6.0 requires 3.12+. The py launcher is asked by name first because
    # it sidesteps the Windows Store `python` stub, which exists only to open
    # the Store page and reports no usable version.
    $candidates = @()
    if (Test-Command 'py') {
        foreach ($v in @('-3.13', '-3.12', '-3.14', '-3')) { $candidates += ,@('py', @($v)) }
    }
    if (Test-Command 'python') { $candidates += ,@('python', @()) }
    foreach ($v in @('313', '312', '314')) {
        $candidates += ,@((Join-Path $env:LOCALAPPDATA "Programs\Python\Python$v\python.exe"), @())
    }

    foreach ($c in $candidates) {
        $exe = $c[0]; $pre = $c[1]
        if ($exe -like '*\*' -and -not (Test-Path $exe)) { continue }
        try {
            $out = & $exe @pre -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        } catch { continue }
        if (-not $out) { continue }
        $parts = "$out".Trim().Split('.')
        if ($parts.Count -lt 2) { continue }
        $major = [int]$parts[0]; $minor = [int]$parts[1]
        if ($major -eq 3 -and $minor -ge 12) {
            return [pscustomobject]@{ Exe = $exe; Pre = $pre; Version = "$major.$minor" }
        }
    }
    return $null
}

$python = Resolve-Python
if (-not $python) {
    Write-Info 'No Python 3.12 or newer found.'
    if (-not (Invoke-Winget 'Python.Python.3.13' 'Python 3.13')) {
        Fail @"
Python 3.12 or newer is required (Django 6.0 does not support older versions)
and winget is not available to install it.
  1. Download it from https://www.python.org/downloads/
  2. During setup, tick "Add python.exe to PATH"
  3. Re-run install.bat
"@
    }
    $python = Resolve-Python
    if (-not $python) {
        Fail 'Python was installed but still cannot be found. Close this window, open a new one, and re-run install.bat.'
    }
}
Write-Ok "Python $($python.Version)  ($($python.Exe) $($python.Pre))"

# --------------------------------------------------------------------------
# 2. Node.js
# --------------------------------------------------------------------------
Write-Head '2/11  Node.js 18+'

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

$npm = Resolve-Npm
if (-not $npm) {
    Write-Info 'Node.js not found.'
    if (-not (Invoke-Winget 'OpenJS.NodeJS.LTS' 'Node.js LTS')) {
        Fail @"
Node.js 18 or newer is required and winget is not available to install it.
  1. Download the LTS installer from https://nodejs.org
  2. Run it with the default options
  3. Re-run install.bat
"@
    }
    $npm = Resolve-Npm
    if (-not $npm) {
        Fail 'Node.js was installed but npm still cannot be found. Close this window, open a new one, and re-run install.bat.'
    }
}
$nodeVersion = '(unknown)'
try { $nodeVersion = (& node --version) } catch { }
Write-Ok "Node $nodeVersion"

# --------------------------------------------------------------------------
# 3. virtualenv + Python packages
# --------------------------------------------------------------------------
Write-Head '3/11  Virtualenv and Python packages'

if ($RebuildVenv -and (Test-Path $VenvDir)) {
    Write-Info 'Removing the existing virtualenv (-RebuildVenv)...'
    Remove-Item -Recurse -Force $VenvDir
}

# A venv built on an older interpreter is worse than none: pip does not fail on
# requirements it cannot satisfy, it silently resolves backwards and leaves a
# stale stack that looks installed. Check the version before reusing it.
if (Test-Path $VenvPython) {
    $venvVersion = ''
    try {
        $venvVersion = (& $VenvPython -c "import sys; print('%d.%d' % sys.version_info[:2])").Trim()
    } catch { }
    $tooOld = $true
    if ($venvVersion -match '^3\.(\d+)$') { $tooOld = ([int]$Matches[1] -lt 12) }
    if ($tooOld) {
        Write-Info "The existing venv runs Python $venvVersion, but this project needs 3.12+ - rebuilding it."
        Remove-Item -Recurse -Force $VenvDir
    }
}

if (-not (Test-Path $VenvPython)) {
    # A half-created venv (interrupted install, wrong Python) is a classic
    # source of "the package is installed but will not import" - clear the
    # whole folder rather than trying to repair it.
    if (Test-Path $VenvDir) {
        Write-Info 'The existing virtualenv looks incomplete, rebuilding it...'
        Remove-Item -Recurse -Force $VenvDir
    }
    Write-Info 'Creating venv\ ...'
    Invoke-Native $python.Exe (@($python.Pre) + @('-m', 'venv', $VenvDir)) | Out-Null
    if (-not (Test-Path $VenvPython)) { Fail 'Could not create the virtualenv.' }
    Write-Ok 'Virtualenv created'
} else {
    Write-Ok 'Virtualenv already present'
}

Invoke-Native $VenvPython @('-m', 'pip', 'install', '--upgrade', 'pip', '--quiet') | Out-Null

$lockFile = Join-Path $BackendDir 'requirements.lock.txt'
$reqFile  = Join-Path $BackendDir 'requirements.txt'
$pipCode  = 1
if (Test-Path $lockFile) {
    Write-Info 'Installing the pinned versions from requirements.lock.txt (several minutes on a first run)...'
    $pipCode = Invoke-Native $VenvPython @('-m', 'pip', 'install', '-r', $lockFile)
    if ($pipCode -ne 0) {
        Write-Warn 'The pinned versions did not install on this machine - retrying with the unpinned requirements.txt.'
    }
}
if ($pipCode -ne 0) {
    Write-Info 'Installing from requirements.txt...'
    $pipCode = Invoke-Native $VenvPython @('-m', 'pip', 'install', '-r', $reqFile)
}
if ($pipCode -ne 0) { Fail 'pip install failed - the errors above say why.' }

# Import what the app starts with, so a resolver that "succeeded" while
# producing an unusable combination is caught here rather than in a crashed
# server window later. rasterio and shapely matter most: GeoDjango ctypes-loads
# the GDAL and GEOS DLLs out of those wheels, and a version mismatch shows up
# as WinError 127 at the first map query.
$importCheck = Invoke-Native $VenvPython @(
    '-c', 'import django, rest_framework, psycopg, rasterio, shapely, sklearn, pandas, rapidfuzz'
)
if ($importCheck -ne 0) {
    Fail 'The installed packages do not import cleanly together. Re-run: install.bat -RebuildVenv'
}
Write-Ok 'Python packages installed'

# --------------------------------------------------------------------------
# 4-5. portable PostgreSQL + PostGIS
# --------------------------------------------------------------------------
Write-Head '4/11  PostgreSQL 15 (portable, no admin)'

$pg = Get-PgPaths $RepoRoot

if ($Force -and (Test-Path $pg.PgSql)) {
    Write-Info 'Removing the unpacked server (-Force)...'
    if (Test-PgRunning $pg) { Stop-PortablePg $pg }
    Remove-Item -Recurse -Force $pg.PgSql
}

if (Test-PgInstalled $pg) {
    Write-Ok 'PostgreSQL already unpacked (.localdb\pgsql)'
} else {
    $zip = Get-OfflineOrRemote -Name 'postgresql-15-binaries.zip' -Url $PgUrl `
        -VendorDir $VendorDir -CacheDir $CacheDir `
        -Label 'PostgreSQL 15 binaries (~290 MB, the slow step)'
    Write-Info 'Extracting PostgreSQL...'
    New-Item -ItemType Directory -Force -Path $pg.Root | Out-Null
    # The archive contains a single top-level pgsql\ folder, which lands as
    # .localdb\pgsql - exactly where Get-PgPaths expects it.
    Expand-Archive -Path $zip -DestinationPath $pg.Root -Force
    if (-not (Test-PgInstalled $pg)) { Fail 'PostgreSQL unpacked but pg_ctl.exe / psql.exe are missing.' }
    Write-Ok 'PostgreSQL 15 unpacked into .localdb\pgsql'
}

Write-Head '5/11  PostGIS'

$postgisControl = Join-Path $pg.PgSql 'share\extension\postgis.control'
if ((Test-Path $postgisControl) -and (-not $Force)) {
    Write-Ok 'PostGIS already unpacked'
} else {
    $zip = Get-OfflineOrRemote -Name 'postgis-bundle.zip' -Url $PostgisUrl `
        -FallbackUrl $PostgisFallbackUrl -VendorDir $VendorDir -CacheDir $CacheDir `
        -Label 'PostGIS bundle (~120 MB)'

    $extracted = Join-Path $CacheDir 'postgis-extracted'
    if (Test-Path $extracted) { Remove-Item -Recurse -Force $extracted }
    Write-Info 'Extracting PostGIS...'
    Expand-Archive -Path $zip -DestinationPath $extracted -Force

    # The bundle wraps everything in one versioned folder whose bin/, lib/ and
    # share/ mirror the server's own layout, so the install is a straight
    # overlay onto pgsql\ rather than a per-file copy list.
    $bundleRoot = Get-ChildItem -Path $extracted -Directory |
                  Where-Object { Test-Path (Join-Path $_.FullName 'bin') } |
                  Select-Object -First 1
    if (-not $bundleRoot) { $bundleRoot = Get-Item $extracted }
    Copy-Item -Path (Join-Path $bundleRoot.FullName '*') -Destination $pg.PgSql -Recurse -Force

    if (-not (Test-Path $postgisControl)) {
        Fail 'The PostGIS bundle unpacked but postgis.control is not where it should be.'
    }
    Remove-Item -Recurse -Force $extracted -ErrorAction SilentlyContinue
    Write-Ok 'PostGIS unpacked over .localdb\pgsql'
}

# --------------------------------------------------------------------------
# 6. cluster
# --------------------------------------------------------------------------
Write-Head '6/11  Database cluster'

if ($ResetDb -and (Test-Path $pg.Data)) {
    Write-Info 'Stopping the server and deleting the cluster (-ResetDb)...'
    if (Test-PgRunning $pg) { Stop-PortablePg $pg }
    Remove-Item -Recurse -Force $pg.Data
    Remove-Item -Force $pg.PortFile, $pg.PwFile -ErrorAction SilentlyContinue
}

# A random superuser password, generated once and kept beside the cluster. It
# is never typed by a human: initdb reads it from a file, and every later psql
# call takes it from PGPASSWORD. Trust stays on scram-sha-256 rather than the
# usual portable-Postgres shortcut of `trust` on loopback, so a shared machine
# does not hand the cluster to anything else running on it.
if (Test-Path $pg.PwFile) {
    $superPw = (Get-Content $pg.PwFile -Raw).Trim()
} else {
    $bytes = New-Object 'System.Byte[]' 24
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $superPw = [Convert]::ToBase64String($bytes) -replace '[^A-Za-z0-9]', ''
}

if (Test-Path (Join-Path $pg.Data 'PG_VERSION')) {
    Write-Ok 'Cluster already initialised (.localdb\data)'
} else {
    if (Test-Path $pg.Data) { Remove-Item -Recurse -Force $pg.Data }
    New-Item -ItemType Directory -Force -Path $pg.Data | Out-Null

    $pwFileTmp = Join-Path $CacheDir 'pgpw.txt'
    Set-Content -Path $pwFileTmp -Value $superPw -Encoding ASCII -NoNewline
    Write-Info 'Initialising the cluster (initdb)...'
    $code = Invoke-Native $pg.InitDb @(
        '-D', $pg.Data, '-U', 'postgres', '--pwfile', $pwFileTmp,
        '-E', 'UTF8', '--locale=C', '-A', 'scram-sha-256'
    ) -Quiet
    Remove-Item -Force $pwFileTmp -ErrorAction SilentlyContinue
    if ($code -ne 0 -or -not (Test-Path (Join-Path $pg.Data 'PG_VERSION'))) {
        Fail 'initdb failed - see the messages above.'
    }
    New-Item -ItemType Directory -Force -Path $pg.Root | Out-Null
    Set-Content -Path $pg.PwFile -Value $superPw -Encoding ASCII
    Write-Ok 'Cluster initialised'
}

# Port, in order of authority:
#   1. an already-running server - ask it, via postmaster.pid
#   2. the port a previous run recorded, if nothing else has taken it
#   3. the first free port from 5433 up (5432 is routinely taken by a system
#      PostgreSQL or by Hyper-V)
$pgPort = 0
if (Test-PgRunning $pg) {
    $pgPort = Get-PgRunningPort $pg
    if ($pgPort -gt 0) {
        Write-Ok "Server already running on port $pgPort"
    } else {
        # Running but unreadable pid file - restart it onto a known port rather
        # than carrying on against a port we would only be guessing at.
        Write-Info 'A server is running but its port could not be read - restarting it...'
        Stop-PortablePg $pg
    }
}

if ($pgPort -eq 0) {
    if (Test-Path $pg.PortFile) {
        $recorded = 0
        if ([int]::TryParse((Get-Content $pg.PortFile -Raw).Trim(), [ref]$recorded)) {
            # Only reuse it if it is actually free - another program may have
            # taken it since it was recorded.
            if ($recorded -gt 0 -and -not (Test-PortOpen $recorded)) { $pgPort = $recorded }
        }
    }
    if ($pgPort -eq 0) { $pgPort = Get-FreePort 5433 60 }
    if ($pgPort -eq 0) { Fail 'No free TCP port in 5433-5492 for PostgreSQL.' }

    Write-Info "Starting PostgreSQL on port $pgPort ..."
    if (-not (Start-PortablePg $pg $pgPort)) {
        Fail "PostgreSQL did not start. The server log is at $($pg.Log)"
    }
    Write-Ok "Server started on port $pgPort"
}
Set-Content -Path $pg.PortFile -Value "$pgPort" -Encoding ASCII

# --------------------------------------------------------------------------
# 7. role, database, PostGIS extension
# --------------------------------------------------------------------------
Write-Head '7/11  Application role and database'

# The app's own password. Same reasoning as the superuser one: generated, kept
# on disk beside the cluster, written into .env, never typed.
$appPw = Get-EnvValue -Path $EnvFile -Key 'DB_PASSWORD'
if ((-not $appPw) -or ($appPw -eq 'your_db_password_here')) {
    $bytes = New-Object 'System.Byte[]' 18
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $appPw = [Convert]::ToBase64String($bytes) -replace '[^A-Za-z0-9]', ''
}

$roleExists = Get-PsqlScalar -Pg $pg -Port $pgPort -Database 'postgres' -Password $superPw `
    -Sql "SELECT 1 FROM pg_roles WHERE rolname='$DbUser';"
if ($roleExists -eq '1') {
    # Reassert the password so .env and the server cannot drift apart, which is
    # otherwise a very confusing authentication failure on a re-run.
    Invoke-Psql -Pg $pg -Port $pgPort -Database 'postgres' -Password $superPw `
        -Sql "ALTER ROLE $DbUser WITH LOGIN PASSWORD '$appPw' CREATEDB;" | Out-Null
    Write-Ok "Role $DbUser already exists (password reasserted)"
} else {
    # CREATEDB because the test suite builds and drops its own test database.
    $code = Invoke-Psql -Pg $pg -Port $pgPort -Database 'postgres' -Password $superPw `
        -Sql "CREATE ROLE $DbUser WITH LOGIN PASSWORD '$appPw' CREATEDB;"
    if ($code -ne 0) { Fail "Could not create the $DbUser role." }
    Write-Ok "Role $DbUser created"
}

$dbExists = Get-PsqlScalar -Pg $pg -Port $pgPort -Database 'postgres' -Password $superPw `
    -Sql "SELECT 1 FROM pg_database WHERE datname='$DbName';"
if ($dbExists -eq '1') {
    Write-Ok "Database $DbName already exists"
} else {
    $code = Invoke-Psql -Pg $pg -Port $pgPort -Database 'postgres' -Password $superPw `
        -Sql "CREATE DATABASE $DbName OWNER $DbUser;"
    if ($code -ne 0) { Fail "Could not create the $DbName database." }
    Write-Ok "Database $DbName created"
}

# PostGIS goes into template1 as well as the app database: pytest-django builds
# its test database from template1, so without this every geo test fails on a
# missing extension even though the app database is fine.
foreach ($target in @('template1', $DbName)) {
    $code = Invoke-Psql -Pg $pg -Port $pgPort -Database $target -Password $superPw `
        -Sql 'CREATE EXTENSION IF NOT EXISTS postgis;'
    if ($code -ne 0) { Fail "Could not enable PostGIS on $target." }
}
$postgisVersion = Get-PsqlScalar -Pg $pg -Port $pgPort -Database $DbName -Password $superPw `
    -Sql 'SELECT postgis_lib_version();'
Write-Ok "PostGIS $postgisVersion enabled on $DbName and template1"

# --------------------------------------------------------------------------
# 8. .env
# --------------------------------------------------------------------------
Write-Head '8/11  Configuration'

if (-not (Test-Path $EnvFile)) {
    if (-not (Test-Path $EnvExample)) { Fail 'btt-backend\.env.example is missing.' }
    Copy-Item $EnvExample $EnvFile
    Write-Ok 'Created btt-backend\.env from .env.example'
} else {
    Write-Ok 'btt-backend\.env already present - updating the database values only'
}

# Only the values this installer actually determined. Email and Twilio keys are
# left exactly as found, so a re-run never clobbers something pasted in by hand.
Set-EnvValue -Path $EnvFile -Key 'DB_NAME'     -Value $DbName
Set-EnvValue -Path $EnvFile -Key 'DB_USER'     -Value $DbUser
Set-EnvValue -Path $EnvFile -Key 'DB_PASSWORD' -Value $appPw
Set-EnvValue -Path $EnvFile -Key 'DB_HOST'     -Value '127.0.0.1'
Set-EnvValue -Path $EnvFile -Key 'DB_PORT'     -Value "$pgPort"
Set-EnvValue -Path $EnvFile -Key 'MEDIA_ROOT'  -Value (Join-Path $RepoRoot 'media')

$secret = Get-EnvValue -Path $EnvFile -Key 'SECRET_KEY'
if ((-not $secret) -or ($secret -like 'change-me*')) {
    $bytes = New-Object 'System.Byte[]' 48
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    Set-EnvValue -Path $EnvFile -Key 'SECRET_KEY' -Value (([Convert]::ToBase64String($bytes)) -replace '[^A-Za-z0-9]', '')
    Write-Ok 'Generated a SECRET_KEY'
}

# A demo machine has no SMTP credentials and no Twilio account. Left at the
# defaults, registration would block on a verification email that never
# arrives; these three make the whole flow work offline.
Set-EnvValue -Path $EnvFile -Key 'LOCAL_DEV_MODE'  -Value 'True'
Set-EnvValue -Path $EnvFile -Key 'DISABLE_SMTP'    -Value 'True'
Set-EnvValue -Path $EnvFile -Key 'DEBUG'           -Value 'True'
New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot 'media') | Out-Null
Write-Ok "Database settings written (port $pgPort)"

# --------------------------------------------------------------------------
# 9. migrations and seed data
# --------------------------------------------------------------------------
Write-Head '9/11  Database schema and demo data'

Push-Location $BackendDir
try {
    $code = Invoke-Native $VenvPython @('manage.py', 'migrate', '--noinput')
    if ($code -ne 0) { Fail 'manage.py migrate failed - see the errors above.' }
    Write-Ok 'Migrations applied'

    if ($NoSeed) {
        Write-Info 'Skipped demo users and demo data (-NoSeed).'
    } else {
        # Both commands are written to be idempotent, so a re-run tops up
        # what is missing rather than duplicating rows.
        if ((Invoke-Native $VenvPython @('manage.py', 'create_demo_users')) -ne 0) {
            Write-Warn 'create_demo_users did not finish cleanly - the app still runs, but the demo logins may be missing.'
        } else {
            Write-Ok 'Demo users created'
        }
        if ((Invoke-Native $VenvPython @('manage.py', 'seed_demo_data')) -ne 0) {
            Write-Warn 'seed_demo_data did not finish cleanly - the app still runs, but dashboards will be empty.'
        } else {
            Write-Ok 'Demo data seeded'
        }
    }
} finally {
    Pop-Location
}

# --------------------------------------------------------------------------
# 10. frontend packages
# --------------------------------------------------------------------------
Write-Head '10/11  Frontend packages'

Push-Location $FrontendDir
try {
    # `npm ci` installs exactly what package-lock.json records, down to the
    # transitive dependencies. It refuses to run if the lock file and
    # package.json have drifted apart, in which case npm install reconciles them.
    $npmCode = 1
    if (Test-Path (Join-Path $FrontendDir 'package-lock.json')) {
        Write-Info 'Installing the exact versions in package-lock.json...'
        $npmCode = Invoke-Native $npm @('ci', '--no-fund', '--no-audit')
        if ($npmCode -ne 0) {
            Write-Warn 'npm ci failed (the lock file and package.json may have drifted) - falling back to npm install.'
        }
    }
    if ($npmCode -ne 0) {
        Write-Info 'Running npm install...'
        $npmCode = Invoke-Native $npm @('install', '--no-fund', '--no-audit')
    }
    if ($npmCode -ne 0) { Fail 'npm install failed - the errors above say why.' }
} finally {
    Pop-Location
}
Write-Ok 'Frontend packages installed'

# --------------------------------------------------------------------------
# 11. verify
# --------------------------------------------------------------------------
Write-Head '11/11  Verifying the install'

$verifyOk = $true
Push-Location $BackendDir
try {
    if ((Invoke-Native $VenvPython @('manage.py', 'check')) -ne 0) {
        Write-Warn 'manage.py check reported problems.'
        $verifyOk = $false
    } else {
        Write-Ok 'Django system checks pass'
    }

    # A real spatial query end to end: Django settings -> psycopg -> the
    # cluster -> PostGIS, plus the GDAL/GEOS DLLs GeoDjango ctypes-loads out of
    # the rasterio wheel. If this answers, the parts that usually break on a
    # fresh Windows machine are all working together.
    # sys.path gets the backend directory explicitly. Python puts the *script's*
    # own directory on sys.path, not the working directory, and this script
    # lives in TEMP - so without this line `config` is not importable no matter
    # which folder the probe is launched from.
    $probe = @"
import os, sys
sys.path.insert(0, r"$BackendDir")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.contrib.gis.geos import Point
from django.db import connection
with connection.cursor() as c:
    c.execute("SELECT postgis_lib_version();")
    v = c.fetchone()[0]
p = Point(67.0011, 24.8607, srid=4326)
print("probe ok - postgis", v, "- geos", p.wkt[:18])
"@
    $probeFile = Join-Path $CacheDir 'probe.py'
    Set-Content -Path $probeFile -Value $probe -Encoding ASCII
    if ((Invoke-Native $VenvPython @($probeFile)) -ne 0) {
        Write-Warn 'The database/PostGIS/GEOS probe failed - see the error above.'
        $verifyOk = $false
    } else {
        Write-Ok 'Database, PostGIS and GEOS all respond'
    }
} finally {
    Pop-Location
}

# --------------------------------------------------------------------------
if ($verifyOk) {
    Write-Banner @('Install complete') 'Green'
} else {
    Write-Banner @('Install finished, but a check above failed') 'Yellow'
}

if ($script:Warnings.Count -gt 0) {
    Write-Host ''
    Write-Host '   Worth knowing:' -ForegroundColor Yellow
    foreach ($w in $script:Warnings) { Write-Host "     - $w" -ForegroundColor Yellow }
}

Write-Host ''
Write-Host '   Database   PostgreSQL 15 + PostGIS, portable, in .localdb\' -ForegroundColor Gray
Write-Host "              $DbName on 127.0.0.1:$pgPort as $DbUser" -ForegroundColor Gray
Write-Host '              Delete .localdb\ to remove it completely.' -ForegroundColor Gray
Write-Host ''
Write-Host '   Next step: double-click  run.bat' -ForegroundColor Cyan
Write-Host ''

if (-not $verifyOk) { exit 1 }
exit 0
