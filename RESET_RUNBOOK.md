# Bike Theft Tracker Reset Runbook

Use this checklist before a demo/presentation when you want a fully fresh system.

This runbook covers:
- stopping all running services
- clearing local caches/artifacts
- resetting PostgreSQL data
- reapplying Django migrations
- optional superuser/demo data setup
- starting backend + frontend again

---

## Quick one-click option

From project root, run:

```bat
reset_and_start.bat
```

This script automates the full flow in this runbook and also asks:
- whether to create a superuser
- whether to seed demo users/data

---

## 0) Paths used in this project

- Project root: `D:\scripts\bike_theft_tracker`
- Backend: `D:\scripts\bike_theft_tracker\btt-backend`
- Frontend: `D:\scripts\bike_theft_tracker\btt-frontend`
- Venv Python: `D:\scripts\bike_theft_tracker\venv\Scripts\python.exe`
- PostgreSQL binaries: `C:\Users\Maaz\localdev\postgresql-15\pgsql\bin`
- PostgreSQL data dir: `C:\Users\Maaz\localdev\postgresql-15\data`

---

## 1) Stop everything cleanly

### 1.1 Stop backend/frontend dev servers

PowerShell:

```powershell
# Kill Django + Vite if running
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }

Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
```

### 1.2 Stop PostgreSQL

```powershell
& "C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe" `
  -D "C:\Users\Maaz\localdev\postgresql-15\data" stop
```

---

## 2) Optional: clear local caches/artifacts

From project root:

```powershell
if (Test-Path "btt-backend\.pytest_cache") { Remove-Item "btt-backend\.pytest_cache" -Recurse -Force }
if (Test-Path "btt-backend\htmlcov") { Remove-Item "btt-backend\htmlcov" -Recurse -Force }
if (Test-Path "btt-backend\.coverage") { Remove-Item "btt-backend\.coverage" -Force }
if (Test-Path "btt-frontend\test-results") { Remove-Item "btt-frontend\test-results" -Recurse -Force }
```

---

## 3) Start PostgreSQL again

```powershell
& "C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe" `
  -D "C:\Users\Maaz\localdev\postgresql-15\data" `
  -o "-p 5433" `
  -l "C:\Users\Maaz\localdev\postgresql-15\data\pg.log" start
```

---

## 4) Reset Django DB to empty state

From `btt-backend`:

```powershell
& "D:\scripts\bike_theft_tracker\venv\Scripts\python.exe" manage.py reset_db --noinput --force
& "D:\scripts\bike_theft_tracker\venv\Scripts\python.exe" manage.py migrate
& "D:\scripts\bike_theft_tracker\venv\Scripts\python.exe" manage.py check
```

What this gives you:
- all data removed
- schema preserved by migrations
- app ready to register new users from scratch

---

## 5) Optional setup before demo

### 5.1 Create Django superuser (for `/admin/`)

```powershell
& "D:\scripts\bike_theft_tracker\venv\Scripts\python.exe" manage.py createsuperuser
```

### 5.2 Seed demo users/data (only if you need preloaded content)

```powershell
& "D:\scripts\bike_theft_tracker\venv\Scripts\python.exe" manage.py create_demo_users --reset
& "D:\scripts\bike_theft_tracker\venv\Scripts\python.exe" manage.py seed_demo_data --clear
```

If you need a true clean demo where you register users live, skip this section.

---

## 6) Local-dev email verification mode (no paid SMTP/domain needed)

In `btt-backend/.env` set:

```ini
LOCAL_DEV_MODE=True
DISABLE_SMTP=True
```

In this mode:
- registration response includes `verification_token` and `verification_url`
- emails use console backend (no external SMTP required)

---

## 7) Start the app

### 7.1 Start backend

```powershell
cd D:\scripts\bike_theft_tracker\btt-backend
& "D:\scripts\bike_theft_tracker\venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000
```

### 7.2 Start frontend (new terminal)

```powershell
cd D:\scripts\bike_theft_tracker\btt-frontend
npm run dev
```

---

## 8) Quick verification checks

- Frontend: `http://localhost:3000/`
- Backend auth endpoint: `http://localhost:8000/api/auth/login/`
- Django admin (if superuser created): `http://localhost:8000/admin/`

Backend unauthenticated check:

```powershell
try { (Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/notifications/).StatusCode } catch { $_.Exception.Response.StatusCode.value__ }
```

Expected: `401` (means API is alive and auth protection is active).

---

## 9) One-command test pass (optional)

```powershell
cd D:\scripts\bike_theft_tracker\btt-backend
& "D:\scripts\bike_theft_tracker\venv\Scripts\python.exe" -m pytest
```

Expected currently: full suite passes with coverage gate.
