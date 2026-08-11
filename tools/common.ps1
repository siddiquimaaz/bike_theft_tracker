<#
    Shared helpers for setup.ps1 and run.ps1.

    Dot-sourced by both, so a fix here applies to installing and to launching.
    Everything in this file is written for Windows PowerShell 5.1, which is what
    the .bat wrappers invoke: no `&&`, no ternary, no `??`.
#>

# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
$script:Warnings = @()

function Write-Head($text) {
    Write-Host ''
    Write-Host ('  ' + ('-' * 62)) -ForegroundColor DarkGray
    Write-Host "   $text" -ForegroundColor Cyan
    Write-Host ('  ' + ('-' * 62)) -ForegroundColor DarkGray
}
function Write-Ok   ($text) { Write-Host "   [ OK ]  $text" -ForegroundColor Green }
function Write-Info ($text) { Write-Host "   [ .. ]  $text" -ForegroundColor Gray }
function Write-Fail ($text) { Write-Host "   [FAIL]  $text" -ForegroundColor Red }
function Write-Warn ($text) {
    Write-Host "   [WARN]  $text" -ForegroundColor Yellow
    $script:Warnings += $text
}
function Fail($text) { throw $text }

function Write-Banner($lines, $colour) {
    Write-Host ''
    Write-Host '  ==============================================================' -ForegroundColor $colour
    foreach ($l in $lines) { Write-Host "     $l" -ForegroundColor $colour }
    Write-Host '  ==============================================================' -ForegroundColor $colour
}

# --------------------------------------------------------------------------
# native commands
#
# pip, npm, initdb and psql all write progress and warnings to stderr. Under
# $ErrorActionPreference = 'Stop', PowerShell 5.1 turns that into a terminating
# NativeCommandError and aborts an install that was going fine. Every external
# call goes through here: preference relaxed for the call, real exit code
# returned for the caller to judge.
# --------------------------------------------------------------------------
function Invoke-Native {
    param(
        [Parameter(Mandatory)] [string] $Exe,
        [string[]] $Arguments = @(),
        # Send the program's own output to the host (the default) or capture it.
        [switch] $Quiet
    )
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        if ($Quiet) {
            & $Exe @Arguments 2>&1 | Out-Null
        } else {
            # Out-Host, not the pipeline: pip and npm progress is the only
            # feedback during the slow steps, and keeping it out of the pipeline
            # leaves the exit code as this function's single return value.
            & $Exe @Arguments | Out-Host
        }
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
}

# --------------------------------------------------------------------------
# PATH
#
# winget writes PATH to the registry, not into this already-running process, so
# a Python or Node installed seconds ago is invisible without re-reading it.
# Some hardened Windows images also ship without System32 on PATH, which breaks
# pip, npm and winget in confusing "not recognized" ways.
# --------------------------------------------------------------------------
function Update-PathFromRegistry {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user    = [Environment]::GetEnvironmentVariable('Path', 'User')
    $merged  = ($machine, $user | Where-Object { $_ }) -join ';'
    if ($merged) { $env:Path = $merged }
    $system32 = Join-Path $env:SystemRoot 'System32'
    if ($env:Path -notlike "*$system32*") { $env:Path = "$system32;$env:Path" }
}

function Test-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Invoke-Winget($id, $label) {
    if (-not (Test-Command 'winget')) { return $false }
    Write-Info "Installing $label via winget ($id) - this can take a few minutes..."
    Invoke-Native 'winget' @(
        'install', '-e', '--id', $id, '--silent',
        '--accept-package-agreements', '--accept-source-agreements'
    ) | Out-Null
    Update-PathFromRegistry
    return $true
}

# --------------------------------------------------------------------------
# downloads
# --------------------------------------------------------------------------
function Get-OfflineOrRemote {
    <#
        Return a path to `name`, preferring copies already on this machine over
        the network. Looks, in order:

          1. <repo>\vendor\<name>   - put there deliberately, e.g. carried in on
                                      a USB stick for a machine with no internet
          2. <temp cache>\<name>    - downloaded by an earlier run on this machine
          3. the network            - $Url, then $FallbackUrl

        The vendor folder is what makes a fully offline install possible: drop
        the two archives in beside the repo and setup.ps1 never reaches for the
        network. Nothing is copied out of vendor\, it is read in place, so a
        read-only USB stick works.
    #>
    param(
        [Parameter(Mandatory)] [string] $Name,
        [Parameter(Mandatory)] [string] $Url,
        [string] $FallbackUrl = '',
        [Parameter(Mandatory)] [string] $VendorDir,
        [Parameter(Mandatory)] [string] $CacheDir,
        [Parameter(Mandatory)] [string] $Label
    )

    $vendored = Join-Path $VendorDir $Name
    if (Test-Path $vendored) {
        Write-Ok "Using the copy shipped in vendor\ ($Name) - no download needed"
        return $vendored
    }

    $cached = Join-Path $CacheDir $Name
    if (Test-Path $cached) {
        Write-Info "Reusing the archive already downloaded to the temp folder ($Name)."
        return $cached
    }

    try {
        Get-RemoteFile $Url $cached $Label
    } catch {
        if (-not $FallbackUrl) { throw }
        Write-Info "The published release moved - trying the archived build..."
        # A partial file from the failed attempt would be mistaken for a good
        # one on the next run.
        Remove-Item -Force $cached -ErrorAction SilentlyContinue
        Get-RemoteFile $FallbackUrl $cached "$Label (archived build)"
    }
    return $cached
}

function Get-RemoteFile($url, $destination, $label) {
    New-Item -ItemType Directory -Force -Path (Split-Path $destination) | Out-Null
    Write-Info "Downloading $label..."
    Write-Host "           $url" -ForegroundColor DarkGray

    # BITS gives a real progress bar and resumes partial transfers; it is absent
    # or disabled on some locked-down machines, hence the WebClient fallback.
    if (Test-Command 'Start-BitsTransfer') {
        try {
            Start-BitsTransfer -Source $url -Destination $destination -Description $label -ErrorAction Stop
            return
        } catch {
            Write-Info 'BITS unavailable, falling back to a direct download...'
        }
    }
    $client = New-Object System.Net.WebClient
    try {
        $client.Headers.Add('User-Agent', 'btt-setup')
        $client.DownloadFile($url, $destination)
    } finally {
        $client.Dispose()
    }
}

# --------------------------------------------------------------------------
# ports
# --------------------------------------------------------------------------
function Get-FreePort($start, $limit) {
    # Bind-test rather than parse netstat: binding is what the server is about
    # to do, so it answers the question that actually matters, and it does not
    # depend on netstat.exe being reachable on a stripped PATH.
    for ($port = $start; $port -lt ($start + $limit); $port++) {
        $listener = $null
        try {
            $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $port)
            $listener.Start()
            return $port
        } catch {
            continue
        } finally {
            if ($listener) { $listener.Stop() }
        }
    }
    return 0
}

function Test-PortOpen($port) {
    # "Is something already listening here?" - the inverse of Get-FreePort, used
    # to detect a PostgreSQL this script started on an earlier run.
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect('127.0.0.1', $port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(1200, $false)) { return $false }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

# --------------------------------------------------------------------------
# .env
#
# One file, btt-backend\.env, seeded from the checked-in .env.example and then
# patched in place. Patching rather than rewriting matters: the installer needs
# to record the database port and password it chose, without discarding an
# email or Twilio key someone pasted in earlier.
# --------------------------------------------------------------------------
function Set-EnvValue {
    param(
        [Parameter(Mandatory)] [string] $Path,
        [Parameter(Mandatory)] [string] $Key,
        [Parameter(Mandatory)] [AllowEmptyString()] [string] $Value
    )
    $lines = @()
    if (Test-Path $Path) { $lines = @(Get-Content $Path) }

    $pattern = "^\s*#?\s*$([regex]::Escape($Key))\s*="
    $replaced = $false
    $out = New-Object System.Collections.Generic.List[string]
    foreach ($line in $lines) {
        if ((-not $replaced) -and ($line -match $pattern)) {
            $out.Add("$Key=$Value")
            $replaced = $true
        } else {
            $out.Add($line)
        }
    }
    if (-not $replaced) { $out.Add("$Key=$Value") }
    Set-Content -Path $Path -Value $out -Encoding ASCII
}

function Get-EnvValue {
    param(
        [Parameter(Mandatory)] [string] $Path,
        [Parameter(Mandatory)] [string] $Key
    )
    if (-not (Test-Path $Path)) { return $null }
    foreach ($line in (Get-Content $Path)) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=\s*(.*)$") {
            return $Matches[1].Trim()
        }
    }
    return $null
}

# --------------------------------------------------------------------------
# portable PostgreSQL
#
# Everything lives under <repo>\.localdb: the server binaries, the PostGIS
# extension files and the data directory. Nothing is installed system-wide,
# nothing needs administrator rights, and removing that one folder removes the
# database completely - which is the point, since this project gets handed to
# someone else's machine and should leave no trace when it is done.
# --------------------------------------------------------------------------
function Get-PgPaths($RepoRoot) {
    $root = Join-Path $RepoRoot '.localdb'
    return [pscustomobject]@{
        Root    = $root
        PgSql   = Join-Path $root 'pgsql'
        Bin     = Join-Path $root 'pgsql\bin'
        Data    = Join-Path $root 'data'
        Log     = Join-Path $root 'postgres.log'
        PgCtl   = Join-Path $root 'pgsql\bin\pg_ctl.exe'
        Psql    = Join-Path $root 'pgsql\bin\psql.exe'
        InitDb  = Join-Path $root 'pgsql\bin\initdb.exe'
        PortFile= Join-Path $root 'port.txt'
        PwFile  = Join-Path $root 'superuser-password.txt'
    }
}

function Test-PgInstalled($pg) {
    return (Test-Path $pg.PgCtl) -and (Test-Path $pg.Psql)
}

function Test-PgRunning($pg) {
    if (-not (Test-Path $pg.Data)) { return $false }
    $code = Invoke-Native $pg.PgCtl @('status', '-D', $pg.Data) -Quiet
    return ($code -eq 0)
}

function Get-PgRunningPort($pg) {
    <#
        The port a running server actually bound, read from the 4th line of
        postmaster.pid.

        This is the authoritative answer and the only one worth trusting. The
        port recorded in port.txt is written after a successful start, so a run
        interrupted in between leaves it stale or absent; and probing for a free
        port answers a different question entirely - an already-running server
        is by definition NOT on a free one. Guessing instead of asking is how
        you end up running psql against a port with nothing behind it.

        Returns 0 when there is no running server to ask.
    #>
    $pidFile = Join-Path $pg.Data 'postmaster.pid'
    if (-not (Test-Path $pidFile)) { return 0 }
    $lines = @(Get-Content $pidFile -ErrorAction SilentlyContinue)
    if ($lines.Count -lt 4) { return 0 }
    $port = 0
    if ([int]::TryParse($lines[3].Trim(), [ref]$port)) { return $port }
    return 0
}

function Start-PortablePg($pg, $port) {
    # -w waits until the server is actually accepting connections rather than
    # returning as soon as the process spawns; without it the next psql call
    # races the server's startup and fails on a cold machine.
    $code = Invoke-Native $pg.PgCtl @(
        'start', '-D', $pg.Data, '-l', $pg.Log, '-w', '-t', '60',
        '-o', "-p $port"
    ) -Quiet
    return ($code -eq 0)
}

function Stop-PortablePg($pg) {
    if (-not (Test-Path $pg.Data)) { return }
    # 'fast' rolls back open transactions and shuts down immediately; the
    # default 'smart' mode waits for clients to disconnect on their own, which
    # hangs whenever a dev server still holds a connection.
    Invoke-Native $pg.PgCtl @('stop', '-D', $pg.Data, '-m', 'fast', '-w', '-t', '30') -Quiet | Out-Null
}

function Invoke-Psql {
    <#
        Run one SQL statement as the bootstrap superuser.

        The password goes through PGPASSWORD rather than a prompt, because this
        whole script runs unattended; it is set per call and cleared after, so
        it never leaks into the two dev-server windows run.ps1 spawns.
    #>
    param(
        [Parameter(Mandatory)] $Pg,
        [Parameter(Mandatory)] [int] $Port,
        [Parameter(Mandatory)] [string] $Database,
        [Parameter(Mandatory)] [string] $Sql,
        [string] $Superuser = 'postgres',
        [string] $Password  = ''
    )
    $previousPw = $env:PGPASSWORD
    if ($Password) { $env:PGPASSWORD = $Password }
    try {
        $code = Invoke-Native $Pg.Psql @(
            '-U', $Superuser, '-h', '127.0.0.1', '-p', "$Port",
            '-d', $Database, '-v', 'ON_ERROR_STOP=1', '-q', '-c', $Sql
        ) -Quiet
        return $code
    } finally {
        $env:PGPASSWORD = $previousPw
    }
}

function Get-PsqlScalar {
    <# Same as Invoke-Psql but returns the single value the query produced. #>
    param(
        [Parameter(Mandatory)] $Pg,
        [Parameter(Mandatory)] [int] $Port,
        [Parameter(Mandatory)] [string] $Database,
        [Parameter(Mandatory)] [string] $Sql,
        [string] $Superuser = 'postgres',
        [string] $Password  = ''
    )
    $previousPw = $env:PGPASSWORD
    if ($Password) { $env:PGPASSWORD = $Password }
    $previousEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & $Pg.Psql '-U' $Superuser '-h' '127.0.0.1' '-p' "$Port" `
                          '-d' $Database '-tAc' $Sql 2>$null
        if ($null -eq $out) { return '' }
        return ("$out").Trim()
    } catch {
        return ''
    } finally {
        $env:PGPASSWORD = $previousPw
        $ErrorActionPreference = $previousEap
    }
}
