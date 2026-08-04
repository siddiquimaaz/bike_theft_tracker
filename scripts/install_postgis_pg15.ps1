# Install PostGIS 3.5 bundle for existing PostgreSQL 15 (Windows, x64).
# Requires: Administrator (UAC) when running the installer; PostgreSQL 15 under
#   C:\Program Files\PostgreSQL\15
#
# After install, enables CREATE EXTENSION postgis on bikethefttracker and template1
# (run the psql block only if you use the default DB name from .env.example).

$ErrorActionPreference = "Stop"

$BundleUrl = "https://ftp.postgresql.org/pub/postgis/pg15/v3.5.0/win64/postgis-bundle-pg15x64-setup-3.5.0-1.exe"
$BundleExe = Join-Path $env:TEMP "postgis-bundle-pg15x64-setup-3.5.0-1.exe"
$PgShare = "C:\Program Files\PostgreSQL\15\share\extension\postgis.control"
$Psql = "C:\Program Files\PostgreSQL\15\bin\psql.exe"

if (Test-Path $PgShare) {
    Write-Host "PostGIS already present: $PgShare" -ForegroundColor Green
}
else {
    Write-Host "Downloading PostGIS bundle ..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $BundleUrl -OutFile $BundleExe -UseBasicParsing
    Write-Host "Starting silent installer (UAC prompt) ..." -ForegroundColor Cyan
    Start-Process -FilePath $BundleExe -ArgumentList "/S" -Wait -Verb RunAs
    if (-not (Test-Path $PgShare)) {
        Write-Host "Install finished but postgis.control not found. Check PostgreSQL 15 path." -ForegroundColor Red
        exit 1
    }
    Write-Host "PostGIS files installed." -ForegroundColor Green
}

if (-not (Test-Path $Psql)) {
    Write-Host "psql not found at $Psql — skip CREATE EXTENSION (install PostgreSQL client tools)." -ForegroundColor Yellow
    exit 0
}

Write-Host "Enabling extension on template1 (postgres superuser) ..." -ForegroundColor Cyan
& $Psql -U postgres -h localhost -p 5432 -d template1 -c "CREATE EXTENSION IF NOT EXISTS postgis;"
$dbExists = & $Psql -U postgres -h localhost -p 5432 -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='bikethefttracker';"
if ($dbExists.Trim() -eq "1") {
    Write-Host "Enabling extension on bikethefttracker ..." -ForegroundColor Cyan
    & $Psql -U postgres -h localhost -p 5432 -d bikethefttracker -c "CREATE EXTENSION IF NOT EXISTS postgis;"
}

Write-Host "Done. Run: cd btt-backend && python manage.py migrate && python manage.py create_demo_users" -ForegroundColor Green
