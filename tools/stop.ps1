<#
    Bike Theft Tracker - stop everything this project started.

    Run it through kill_all.bat (double-click) or directly:
        powershell -ExecutionPolicy Bypass -File tools\stop.ps1

    Stops, in order: the frontend dev server, the Django dev server, and the
    portable PostgreSQL under .localdb.

    Every path is derived from this file's own location, so it works on any
    machine and from any working directory.

    Deliberately narrow about what it kills. The old version of this script ran
    `taskkill /IM node.exe` and `/IM postgres.exe`, which stopped every Node
    process and every PostgreSQL on the machine - including a system database
    that had nothing to do with this project. This one closes the ports it
    knows this project uses, and shuts the portable cluster down through pg_ctl.
#>
[CmdletBinding()]
param(
    # Leave the database running (handy between test runs - starting it again
    # is the slowest part of a restart).
    [switch]$KeepDb
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')

$RepoRoot = Split-Path -Parent $PSScriptRoot
$EnvFile  = Join-Path $RepoRoot 'btt-backend\.env'

Update-PathFromRegistry
Write-Banner @('Bike Theft Tracker - stopping') 'Magenta'

# --------------------------------------------------------------------------
# Dev servers, by port
#
# By port rather than by image name: this project's Django and vite are the
# only things on these ports, whereas python.exe and node.exe are shared with
# whatever else the machine is running.
# --------------------------------------------------------------------------
function Stop-Port($port, $label) {
    $pids = @()
    try {
        # Get-NetTCPConnection is the clean way and is present on Windows 8+;
        # netstat parsing is the fallback for stripped or older images.
        $pids = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop |
                  Select-Object -ExpandProperty OwningProcess -Unique)
    } catch {
        $netstat = Join-Path $env:SystemRoot 'System32\netstat.exe'
        if (Test-Path $netstat) {
            $pids = @(& $netstat -aon |
                      Select-String ":$port\s" |
                      ForEach-Object { ($_ -split '\s+')[-1] } |
                      Where-Object { $_ -match '^\d+$' } |
                      Select-Object -Unique)
        }
    }

    $pids = @($pids | Where-Object { $_ -and ([int]$_) -gt 4 })
    if ($pids.Count -eq 0) {
        Write-Info "$label (port $port) - nothing listening"
        return
    }
    foreach ($procId in $pids) {
        try {
            Stop-Process -Id ([int]$procId) -Force -ErrorAction Stop
            Write-Ok "$label (port $port) - stopped PID $procId"
        } catch {
            Write-Warn "$label (port $port) - could not stop PID ${procId}: $($_.Exception.Message)"
        }
    }
}

# The ranges run.ps1 picks from, so a server that moved to a busy-port fallback
# is still found.
foreach ($port in 3001..3005) { Stop-Port $port 'frontend' }
foreach ($port in 8001..8005) { Stop-Port $port 'backend' }

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
if ($KeepDb) {
    Write-Info 'Leaving PostgreSQL running (-KeepDb).'
} else {
    $pg = Get-PgPaths $RepoRoot
    if (-not (Test-PgInstalled $pg)) {
        Write-Info 'No portable database in .localdb - nothing to stop.'
    } elseif (-not (Test-PgRunning $pg)) {
        Write-Info 'PostgreSQL is not running.'
    } else {
        $port = Get-EnvValue -Path $EnvFile -Key 'DB_PORT'
        Write-Info "Stopping PostgreSQL (port $port)..."
        Stop-PortablePg $pg
        if (Test-PgRunning $pg) {
            Write-Warn "PostgreSQL did not stop cleanly. Its log is at $($pg.Log)"
        } else {
            Write-Ok 'PostgreSQL stopped'
        }
    }
}

Write-Banner @('Everything stopped') 'Green'
Write-Host ''
Write-Host '   Start it again with:  run.bat' -ForegroundColor Cyan
Write-Host ''
exit 0
