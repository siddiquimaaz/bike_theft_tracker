# Copy btt-backend/.env.example -> .env only when .env is missing (never overwrites).

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Backend = Join-Path $RepoRoot "btt-backend"
$Example = Join-Path $Backend ".env.example"
$Target = Join-Path $Backend ".env"

if (-not (Test-Path $Example)) {
    Write-Host "Missing template: $Example" -ForegroundColor Red
    exit 1
}

if (Test-Path $Target) {
    Write-Host "btt-backend\.env already exists — left unchanged." -ForegroundColor Yellow
}
else {
    Copy-Item -Path $Example -Destination $Target
    Write-Host "Created btt-backend\.env from .env.example" -ForegroundColor Green
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit btt-backend\.env — set SECRET_KEY, DB_*, and optional email/Twilio."
Write-Host "  2. Install PostgreSQL 15 + PostGIS and create the database/user (see docs/README_NEWMACHINE.md)."
Write-Host "  3. On Windows, install GDAL if GeoDjango cannot find DLLs (same doc)."
Write-Host "  4. Activate repo venv:  .\venv\Scripts\Activate.ps1"
Write-Host "  5. cd btt-backend && python manage.py migrate && python manage.py runserver"
