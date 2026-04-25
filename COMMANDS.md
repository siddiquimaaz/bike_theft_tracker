# Bike Theft Tracker — Complete Command Reference

> **Quick orientation:** Django backend on port **8000** · React frontend on port **3000** · PostgreSQL on port **5433**
> All `python manage.py` commands run from `btt-backend/` with the venv active.
> All `npm` commands run from `btt-frontend/`.

---

## Demo Reset Guide

For the complete reset checklist (stop everything, flush DB, migrate, restart), see `RESET_RUNBOOK.md`.

---

## Table of Contents

1. [Daily Startup](#1-daily-startup)
2. [Virtual Environment — Create, Activate, Deactivate](#2-virtual-environment--create-activate-deactivate)
3. [Kill All Ports & Processes](#3-kill-all-ports--processes)
4. [Initial Setup (First Time)](#4-initial-setup-first-time)
5. [Demo Accounts & Credentials](#5-demo-accounts--credentials)
6. [Role-Based Frontend Routes](#6-role-based-frontend-routes)
7. [API Endpoints — Full Reference](#7-api-endpoints--full-reference)
8. [Backend Management Commands](#8-backend-management-commands)
9. [Database Commands](#9-database-commands)
10. [ML & Analytics Commands](#10-ml--analytics-commands)
11. [Testing Commands](#11-testing-commands)
12. [Frontend Commands](#12-frontend-commands)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Daily Startup

### One-command start (recommended)
```bat
:: From D:\scripts\bike_theft_tracker — double-click or run in CMD:
start.bat
```
This kills existing processes on ports 8000/3000, stops PostgreSQL, restarts everything cleanly, then opens both servers.

### One-command full reset + start (for demos)
```bat
reset_and_start.bat
```
This fully flushes DB data, reapplies migrations, optionally creates superuser/demo data, and starts backend+frontend.

### Manual start (if start.bat has issues)

**Terminal 1 — PostgreSQL:**
```powershell
& "C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe" -D "C:\Users\Maaz\localdev\postgresql-15\data" -o "-p 5433" start
```

**Terminal 2 — Django backend:**
```cmd
cd D:\scripts\bike_theft_tracker
call venv\Scripts\activate.bat
cd btt-backend
python manage.py runserver
```

**Terminal 3 — React frontend:**
```cmd
cd D:\scripts\bike_theft_tracker\btt-frontend
npm run dev
```

### Verify everything is up
| Service | URL | Expected |
|---------|-----|----------|
| Django API | http://localhost:8000/api/auth/login/ | 405 Method Not Allowed (GET) |
| Django Admin | http://localhost:8000/admin/ | Admin login page |
| React App | http://localhost:3000 | Login page |

---

## 2. Virtual Environment — Create, Activate, Deactivate

> The virtual environment (`venv/`) lives at the **project root**: `D:\scripts\bike_theft_tracker\venv\`
> It is shared by the entire project — you do **not** need separate venvs for different apps.

---

### Create the virtual environment

```cmd
:: CMD / PowerShell — run once from project root
cd D:\scripts\bike_theft_tracker
python -m venv venv
```

Creates the `venv/` folder. Only needed once. If `venv/` already exists, skip this step.

---

### Activate the virtual environment

Pick the right command for your shell:

#### CMD (Command Prompt) ✅ recommended on Windows
```cmd
cd D:\scripts\bike_theft_tracker
call venv\Scripts\activate.bat
```
Prompt changes to: `(venv) D:\scripts\bike_theft_tracker>`

#### PowerShell
```powershell
cd D:\scripts\bike_theft_tracker
& .\venv\Scripts\Activate.ps1
```
If you get a security error run this first (one-time):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Git Bash / MSYS2
```bash
cd /d/scripts/bike_theft_tracker
source venv/Scripts/activate
```

---

### Check if venv is active

```cmd
:: CMD / PowerShell — should show path inside your venv folder
where python

:: Should print something like:
::   D:\scripts\bike_theft_tracker\venv\Scripts\python.exe

:: Also check the Python version
python --version

:: List installed packages
pip list

:: Confirm Django is installed (sanity check)
python -c "import django; print(django.__version__)"
```

---

### Deactivate the virtual environment

```cmd
:: Works in CMD, PowerShell, and Bash — all the same command
deactivate
```

Prompt goes back to normal. No path change needed.

---

### Install / update packages

```cmd
:: Install all project dependencies (after activating venv)
pip install -r requirements.txt

:: Install a single new package
pip install <package-name>

:: Install a specific version
pip install "django==4.2.11"

:: Upgrade a package
pip install --upgrade <package-name>

:: Upgrade pip itself
python -m pip install --upgrade pip

:: Uninstall a package
pip uninstall <package-name>
```

---

### Save / export current packages

```cmd
:: Overwrite requirements.txt with currently installed packages
pip freeze > requirements.txt

:: Preview what would be written (without saving)
pip freeze
```

---

### Delete and fully recreate the virtual environment

```cmd
:: 1. Deactivate first (if active)
deactivate

:: 2. Delete the venv folder
rmdir /s /q D:\scripts\bike_theft_tracker\venv

:: 3. Recreate
cd D:\scripts\bike_theft_tracker
python -m venv venv

:: 4. Activate
call venv\Scripts\activate.bat

:: 5. Reinstall everything
pip install -r requirements.txt
```

---

### Common venv errors

| Error | Cause | Fix |
|-------|-------|-----|
| `'python' is not recognized` | Python not on system PATH | Use full path: `C:\Python314\python.exe -m venv venv` |
| `cannot be loaded because running scripts is disabled` | PowerShell execution policy | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `call` not recognized | Running CMD command in PowerShell | Use `& .\venv\Scripts\Activate.ps1` instead |
| `pip: command not found` | venv not active | Run the activate command first |
| `ModuleNotFoundError` in Django | Wrong Python / venv not active | Verify `where python` points to venv path |

---

## 3. Kill All Ports & Processes

> Use these when `start.bat` fails, a server is stuck, or you get "port already in use" errors.
> All commands run in **CMD** (not PowerShell) unless noted.

---

### Find what is running on a port

```cmd
:: Show all listeners — find your port in the list
netstat -ano | findstr LISTENING

:: Find specifically what's on port 8000
netstat -aon | findstr ":8000 "

:: Find specifically what's on port 3000
netstat -aon | findstr ":3000 "

:: Find specifically what's on port 5433 (PostgreSQL)
netstat -aon | findstr ":5433 "

:: The last column is the PID — use it with tasklist to identify the process
tasklist | findstr <PID>
```

---

### Kill a specific port (CMD)

```cmd
:: Kill whatever process is on port 8000 (Django)
for /f "tokens=5" %a in ('netstat -aon ^| findstr ":8000 "') do taskkill /PID %a /F

:: Kill whatever process is on port 3000 (React/Vite)
for /f "tokens=5" %a in ('netstat -aon ^| findstr ":3000 "') do taskkill /PID %a /F

:: Kill whatever process is on port 5433 (PostgreSQL)
for /f "tokens=5" %a in ('netstat -aon ^| findstr ":5433 "') do taskkill /PID %a /F

:: Kill whatever process is on port 5432 (default PostgreSQL)
for /f "tokens=5" %a in ('netstat -aon ^| findstr ":5432 "') do taskkill /PID %a /F
```

> **Note:** In a `.bat` file use `%%a`. In CMD prompt directly, use `%a`.

---

### Kill all project ports at once (CMD)

Copy-paste this block to kill everything in one go:

```cmd
for /f "tokens=5" %a in ('netstat -aon ^| findstr ":8000 "') do taskkill /PID %a /F 2>nul
for /f "tokens=5" %a in ('netstat -aon ^| findstr ":3000 "') do taskkill /PID %a /F 2>nul
for /f "tokens=5" %a in ('netstat -aon ^| findstr ":5433 "') do taskkill /PID %a /F 2>nul
```

---

### Kill a specific port (PowerShell)

```powershell
# Kill whatever is on port 8000
$port = 8000
$pid = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue).OwningProcess
if ($pid) { Stop-Process -Id $pid -Force; Write-Host "Killed PID $pid on port $port" }

# Kill port 3000
$port = 3000
$pid = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue).OwningProcess
if ($pid) { Stop-Process -Id $pid -Force; Write-Host "Killed PID $pid on port $port" }

# Kill port 5433
$port = 5433
$pid = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue).OwningProcess
if ($pid) { Stop-Process -Id $pid -Force; Write-Host "Killed PID $pid on port $port" }
```

---

### Kill by process name

```cmd
:: Kill all Python processes (Django server, management commands)
taskkill /IM python.exe /F

:: Kill all Node.js processes (Vite dev server)
taskkill /IM node.exe /F

:: Kill all npm processes
taskkill /IM npm.cmd /F

:: Kill PostgreSQL (pg_ctl managed — use stop command instead)
taskkill /IM postgres.exe /F
taskkill /IM pg_ctl.exe /F

:: Kill everything at once (nuclear)
taskkill /IM python.exe /F 2>nul
taskkill /IM node.exe /F 2>nul
taskkill /IM postgres.exe /F 2>nul
```

---

### Kill by PID directly

```cmd
:: Kill a process by its exact PID
taskkill /PID 12345 /F

:: Kill multiple PIDs at once
taskkill /PID 12345 /PID 67890 /F
```

---

### Stop PostgreSQL cleanly (preferred over taskkill)

```cmd
:: Clean shutdown — always prefer this over taskkill for PostgreSQL
"C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe" -D "C:\Users\Maaz\localdev\postgresql-15\data" stop
```

```powershell
# PowerShell version
& "C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe" -D "C:\Users\Maaz\localdev\postgresql-15\data" stop
```

---

### Full nuclear reset — kill everything and restart

```cmd
:: One command — does everything below automatically
kill_all.bat
```

`kill_all.bat` runs these steps in order:
1. Deactivates the virtual environment (current shell + clears env vars)
2. Stops PostgreSQL cleanly via `pg_ctl stop`
3. Kills port 8000 (Django)
4. Kills port 3000 (React/Vite)
5. Kills port 5433 (PostgreSQL)
6. Kills any remaining `python.exe`, `node.exe`, `postgres.exe` by name

Then bring everything back:
```cmd
start.bat
```

> **Note on venv deactivation:** `kill_all.bat` deactivates the venv in the **shell it runs in** and clears `VIRTUAL_ENV`, `VIRTUAL_ENV_PROMPT`, `PYTHONHOME`. Any **other open terminals** that have the venv active need to run `deactivate` manually or be closed.

---

## 4. Initial Setup (First Time)

### Step 1 — Install frontend dependencies
```bat
install_frontend.bat
```
Runs `npm install` + `npx playwright install chromium`.

### Step 2 — Create Python virtual environment
```cmd
cd D:\scripts\bike_theft_tracker
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Step 3 — Create `.env` file
```cmd
cd btt-backend
copy .env.example .env
```
Then edit `.env` with your database password and other values.

### Step 4 — Run database migrations
```cmd
cd D:\scripts\bike_theft_tracker
call venv\Scripts\activate.bat
cd btt-backend
python manage.py migrate
```

### Step 5 — Seed demo users
```cmd
python manage.py create_demo_users
```

### Step 6 — (Optional) Seed demo theft data
```cmd
python manage.py seed_demo_data
```
Loads 120+ realistic Pakistani bike theft records with GPS coordinates.

---

## 5. Demo Accounts & Credentials

| Role | Email | Password | Access |
|------|-------|----------|--------|
| **Admin** | `admin@demo.btt` | `DemoAdmin@2024` | Full system access + Django admin |
| **Authority** | `authority.karachi@demo.btt` | `Authority@2024` | Case reports, sightings, fuzzy search, hotspots |
| **Owner** | `owner000@demo.btt` | `Owner@2024` | Register bikes, file reports |
| **Community** | `community@demo.btt` | `Community@2024` | Submit sightings |

### Re-seed demo users (fixes broken passwords)
```cmd
cd D:\scripts\bike_theft_tracker
call venv\Scripts\activate.bat
cd btt-backend
python manage.py create_demo_users --reset
```
Use `--reset` whenever you suspect passwords are wrong or users are corrupted.

### Create a Django superuser manually
```cmd
python manage.py createsuperuser
```

---

## 6. Role-Based Frontend Routes

Open http://localhost:3000 and log in — you are redirected automatically based on role.

### Owner (`owner000@demo.btt`)
| Page | URL |
|------|-----|
| Dashboard | http://localhost:3000/owner/dashboard |
| My Bikes | http://localhost:3000/owner/bikes |
| Theft Reports | http://localhost:3000/owner/reports |
| Notifications | http://localhost:3000/owner/notifications |

### Authority (`authority.karachi@demo.btt`)
| Page | URL |
|------|-----|
| Dashboard | http://localhost:3000/authority/dashboard |
| Case Reports | http://localhost:3000/authority/reports |
| Sightings | http://localhost:3000/authority/sightings |
| Fuzzy Search | http://localhost:3000/authority/fuzzy |
| Hotspot Map | http://localhost:3000/authority/hotspots |
| Notifications | http://localhost:3000/authority/notifications |

### Admin (`admin@demo.btt`)
| Page | URL |
|------|-----|
| Dashboard | http://localhost:3000/admin/dashboard |
| User Management | http://localhost:3000/admin/users |
| Analytics | http://localhost:3000/admin/analytics |
| Audit Logs | http://localhost:3000/admin/audit |
| Notifications | http://localhost:3000/admin/notifications |
| Django Admin Panel | http://localhost:8000/admin/ |

### Community (`community@demo.btt`)
| Page | URL |
|------|-----|
| Dashboard | http://localhost:3000/community/dashboard |
| Submit Sighting | http://localhost:3000/community/sightings |
| Notifications | http://localhost:3000/community/notifications |

---

## 7. API Endpoints — Full Reference

Base URL: `http://localhost:8000`
All authenticated endpoints require: `Authorization: Bearer <access_token>`

---

### Authentication — `/api/auth/`
> No token required unless noted.

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| POST | `/api/auth/register/` | Public | Create owner or community account |
| POST | `/api/auth/login/` | Public | Returns `access`, `refresh`, and `user` object |
| POST | `/api/auth/token/refresh/` | Public | Refresh access token |
| GET | `/api/auth/verify-email/<uuid>/` | Public | Activate account via email link |
| POST | `/api/auth/forgot-password/` | Public | Send password reset email |
| POST | `/api/auth/reset-password/<uuid>/` | Public | Set new password |
| POST | `/api/auth/check-email/` | Public | Availability check (throttled 30/min) |
| POST | `/api/auth/check-cnic/` | Public | Availability check (throttled 30/min) |
| POST | `/api/auth/logout/` | Auth | Blacklist refresh token |

**Login request body:**
```json
{ "email": "owner000@demo.btt", "password": "Owner@2024" }
```
**Login response:**
```json
{
  "access": "<jwt>",
  "refresh": "<jwt>",
  "user": { "id": 3, "email": "owner000@demo.btt", "role": "owner", "full_name": "Demo Owner", "city": "Karachi" }
}
```

**Register request body:**
```json
{
  "full_name": "Ali Khan",
  "email": "ali@example.com",
  "cnic": "4200012345678",
  "role": "owner",
  "city": "Karachi",
  "password": "Secure@123",
  "confirm_password": "Secure@123"
}
```

---

### Bikes — `/api/bikes/`
> Owner only (except public search).

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/api/bikes/` | Owner | List my registered bikes |
| POST | `/api/bikes/` | Owner | Register a new bike |
| GET | `/api/bikes/<id>/` | Owner | Get bike details |
| PUT | `/api/bikes/<id>/` | Owner | Update bike info |
| DELETE | `/api/bikes/<id>/` | Owner | Remove bike |

**Register bike request body:**
```json
{
  "make": "Honda",
  "model": "CD 70",
  "year": 2020,
  "color": "Black",
  "registration_number": "KHI-001",
  "engine_number": "ENG12345678",
  "chassis_number": "CHS12345678",
  "registration_city": "Karachi"
}
```

---

### Public Search — `/api/search/`
> No token required.

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/api/search/bike/?q=ENG123` | Public | Search by engine/chassis/plate |
| GET | `/api/search/city/Karachi/` | Public | Get theft count for a city |

---

### Theft Reports — `/api/reports/`
> Owner files reports; Authority manages them.

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/api/reports/` | Owner / Authority | List reports (filtered by role) |
| POST | `/api/reports/` | Owner | File a new theft report |
| GET | `/api/reports/<id>/` | Owner / Authority | Report details |
| PUT | `/api/reports/<id>/` | Owner | Update report |
| PATCH | `/api/reports/<id>/status/` | Authority | Update status |
| POST | `/api/reports/<id>/recovery/` | Authority | Add recovery record |
| GET | `/api/reports/<id>/recovery/` | Authority / Owner | View recovery record |
| PUT | `/api/reports/<id>/recovery/` | Authority | Amend recovery record |
| PUT | `/api/reports/<id>/recovery/confirm/` | Owner | Confirm pickup → closes case (`pending_verification`/`recovered` → `closed`) |

**File theft report request body:**
```json
{
  "bike": 1,
  "theft_date": "2024-01-15",
  "theft_city": "Karachi",
  "theft_location_detail": "Near Hassan Square, Orangi Town",
  "description": "Bike stolen from outside shop"
}
```

**Update report status (Authority):**
```json
{ "status": "under_investigation" }
```
Status flow (modern lifecycle):
`new_case` → `under_review` → `active_investigation` → `bike_located` → `pending_verification` → `recovered` → `closed`

Legacy values (`stolen`, `under_investigation`) remain accepted for backwards compatibility on older reports. See `VERIFIED_DEMO_FLOW.md` for the full state machine and which transitions are allowed at each step.

**Add recovery record (Authority):**
```json
{
  "recovery_date": "2024-02-01",
  "recovery_city": "Karachi",
  "bike_condition": "Good — minor scratches"
}
```

---

### Sightings — `/api/sightings/`
> Community/Authority submits; Authority verifies.

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/api/sightings/` | Authority | List all sightings |
| POST | `/api/sightings/` | Community / Auth | Submit a sighting |
| GET | `/api/sightings/<id>/` | Authority | Sighting details + fuzzy match results |
| POST | `/api/sightings/<id>/verify/` | Authority | Confirm match and link to a bike |
| PUT | `/api/sightings/<id>/owner-confirm/` | Owner | Owner handshake response: `yes` / `no` / `not_sure` |

**Submit sighting request body:**
```json
{
  "raw_engine_number": "ENG1234",
  "raw_chassis_number": "CHS5678",
  "sighting_date": "2024-01-20",
  "sighting_city": "Lahore",
  "location_description": "Near Anarkali Bazaar",
  "notes": "Bike was parked near a fruit stall"
}
```

**Verify sighting (Authority):**
```json
{ "bike_id": 7 }
```

---

### Notifications — `/api/notifications/`

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/api/notifications/` | Auth | List my notifications |
| POST | `/api/notifications/<id>/read/` | Auth | Mark one as read |
| POST | `/api/notifications/read-all/` | Auth | Mark all as read |

---

### ML & Analytics — `/api/ml/`
> Authority and Admin only.

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| POST | `/api/ml/fuzzy-match/` | Authority | Find bikes matching partial numbers |
| GET | `/api/ml/hotspots/` | Authority / Admin | Theft hotspot clusters |
| GET | `/api/ml/trends/` | Authority / Admin | Monthly theft trend analytics |
| GET | `/api/ml/recovery-zones/` | Authority / Admin | Recovery hotspot areas |
| POST | `/api/ml/trigger-reanalysis/` | Admin | Force recalculate all ML models |

**Fuzzy match request body:**
```json
{
  "engine_number": "ENG1234",
  "chassis_number": "CHS5678"
}
```
**Fuzzy match response:** List of matches with `fuzzy_match_score` (0–100). Score ≥ 85 = HIGH, ≥ 70 = MEDIUM, < 70 = LOW.

---

### Admin — `/api/admin/`
> Admin only.

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/api/admin/users/` | Admin | List all users |
| POST | `/api/admin/users/authority/` | Admin | Create an authority account |
| PATCH | `/api/admin/users/<id>/status/` | Admin | Activate/deactivate user |
| GET | `/api/admin/analytics/` | Admin | System-wide statistics |
| GET | `/api/admin/audit-logs/` | Admin | All audit log entries |

**Create authority account:**
```json
{
  "full_name": "Inspector Fatima",
  "email": "fatima@police.gov.pk",
  "cnic": "4210199900001",
  "city": "Lahore",
  "badge_number": "LHR-0042",
  "password": "Temp@1234",
  "confirm_password": "Temp@1234"
}
```

**Toggle user active status:**
```json
{ "is_active": false }
```

---

## 8. Backend Management Commands

All commands run from `btt-backend/` with venv active:
```cmd
cd D:\scripts\bike_theft_tracker
call venv\Scripts\activate.bat
cd btt-backend
```

### Django Core
```cmd
:: Start development server
python manage.py runserver

:: Start on a different port
python manage.py runserver 8080

:: Run database migrations
python manage.py migrate

:: Create new migration after model change
python manage.py makemigrations

:: Show migration status
python manage.py showmigrations

:: Open Django shell
python manage.py shell

:: Open database shell (psql)
python manage.py dbshell

:: Collect static files (production)
python manage.py collectstatic

:: Check for common errors
python manage.py check
```

### User Management
```cmd
:: Seed demo users (skip if already exist)
python manage.py create_demo_users

:: Delete and re-create all demo users (fixes broken passwords)
python manage.py create_demo_users --reset

:: Create a superuser interactively
python manage.py createsuperuser
```

---

## 9. Database Commands

### Connect to the database
```cmd
:: Using psql directly (PostgreSQL on port 5433)
"C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\psql.exe" -U bttadmin -d bikethefttracker -p 5433

:: Or via Django shell
python manage.py dbshell
```

### Useful psql queries
```sql
-- List all tables
\dt

-- Count records in each key table
SELECT COUNT(*) FROM users_customuser;
SELECT COUNT(*) FROM bikes_bike;
SELECT COUNT(*) FROM reports_theftreport;
SELECT COUNT(*) FROM sightings_sighting;

-- Show all users and their roles
SELECT email, role, is_active, is_verified FROM users_customuser;

-- Show recent theft reports
SELECT id, theft_city, status, created_at FROM reports_theftreport ORDER BY created_at DESC LIMIT 10;

-- Show fuzzy match scores
SELECT id, sighting_city, fuzzy_match_score, is_verified FROM sightings_sighting ORDER BY fuzzy_match_score DESC;

-- Exit psql
\q
```

### PostgreSQL service control
```powershell
$PGCTL = "C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe"
$PGDATA = "C:\Users\Maaz\localdev\postgresql-15\data"

# Start PostgreSQL
& $PGCTL -D $PGDATA -o "-p 5433" -l "$PGDATA\pg.log" start

# Stop PostgreSQL
& $PGCTL -D $PGDATA stop

# Check status
& $PGCTL -D $PGDATA status

# Restart
& $PGCTL -D $PGDATA restart
```

### Reset the entire database (nuclear option)
```cmd
:: Drop and recreate — WARNING: deletes all data
python manage.py migrate reports zero
python manage.py migrate sightings zero
python manage.py migrate bikes zero
python manage.py migrate notifications zero
python manage.py migrate ml zero
python manage.py migrate users zero
python manage.py migrate

:: Then re-seed
python manage.py create_demo_users
python manage.py seed_demo_data
```

---

## 10. ML & Analytics Commands

Run from `btt-backend/` with venv active.

### Hotspot Analysis (DBSCAN Clustering)
```cmd
:: Run for all cities
python manage.py run_hotspot_analysis

:: Run for a specific city
python manage.py run_hotspot_analysis --city Karachi
python manage.py run_hotspot_analysis --city Lahore
python manage.py run_hotspot_analysis --city Islamabad
python manage.py run_hotspot_analysis --city Rawalpindi
python manage.py run_hotspot_analysis --city Faisalabad
python manage.py run_hotspot_analysis --city Peshawar
python manage.py run_hotspot_analysis --city Quetta
python manage.py run_hotspot_analysis --city Multan

:: Run for ALL cities in sequence
python manage.py run_hotspot_analysis --all-cities
```

### Trend Analytics
```cmd
:: Compute monthly theft trend data
python manage.py run_trend_analytics
```

### Demo Data Seeding
```cmd
:: Seed 120+ demo theft records (default)
python manage.py seed_demo_data

:: Seed a custom number of records
python manage.py seed_demo_data --count 200

:: Clear all demo data and re-seed
python manage.py seed_demo_data --clear

:: Clear only (no re-seed)
python manage.py seed_demo_data --clear --count 0
```

### Trigger ML re-analysis via API
```cmd
:: POST to /api/ml/trigger-reanalysis/ — Admin only
curl -X POST http://localhost:8000/api/ml/trigger-reanalysis/ ^
  -H "Authorization: Bearer <admin_access_token>"
```

---

## 11. Testing Commands

### Backend Tests (Pytest)

Run from `btt-backend/` with venv active:
```cmd
cd D:\scripts\bike_theft_tracker
call venv\Scripts\activate.bat
cd btt-backend
```

```cmd
:: Run all tests (341 tests, requires 80% coverage to pass)
pytest

:: Run with short traceback (faster output)
pytest --tb=short -q

:: Run a specific app's tests
pytest tests/test_users.py
pytest tests/test_bikes.py
pytest tests/test_reports.py
pytest tests/test_sightings.py
pytest tests/test_ml.py
pytest tests/test_notifications.py

:: Run a single test by name
pytest tests/test_users.py::TestLogin::test_login_success

:: Run without coverage (faster)
pytest --no-cov

:: Run and open HTML coverage report
pytest
start htmlcov\index.html

:: Run in watch mode (re-run on file save)
ptw -- --tb=short -q
```

### Frontend E2E Tests (Playwright)

Run from `btt-frontend/`:
```cmd
cd D:\scripts\bike_theft_tracker\btt-frontend
```

> **Both servers must be running** before starting E2E tests.
> Demo users must be seeded: `python manage.py create_demo_users`

```cmd
:: Run all E2E tests (headless)
npx playwright test

:: Run all tests and open the HTML report when done
npx playwright test --reporter=html

:: Run a specific test suite
npx playwright test e2e/auth.spec.js
npx playwright test e2e/owner.spec.js
npx playwright test e2e/authority.spec.js
npx playwright test e2e/admin.spec.js
npx playwright test e2e/community.spec.js
npx playwright test e2e/api-connectivity.spec.js

:: Full six-event cross-role demo narrative (mirrors the backend
:: TestEndToEndDemoNarrative integration test). Long-running — opt in
:: before a presentation, not on every commit.
npx playwright test tests/e2e/demo_narrative.spec.js

:: Run in headed mode (see the browser)
npx playwright test --headed

:: Run in interactive UI mode (step through tests)
npx playwright test --ui

:: Re-run only failed tests
npx playwright test --last-failed

:: Show HTML report from last run
npx playwright show-report

:: Run via npm scripts
npm run test:e2e
npm run test:e2e:ui
npm run test:e2e:report
```

### Run everything at once
```bat
:: Runs backend pytest, then Playwright E2E
run_tests.bat
```

---

## 12. Frontend Commands

Run from `btt-frontend/`:
```cmd
cd D:\scripts\bike_theft_tracker\btt-frontend
```

```cmd
:: Start development server (http://localhost:3000)
npm run dev

:: Build for production
npm run build

:: Preview the production build locally
npm run preview

:: Install all dependencies
npm install

:: Install Playwright browsers
npx playwright install chromium

:: Install a new package
npm install <package-name>

:: Check for outdated packages
npm outdated

:: View the dependency tree
npm list --depth=0
```

---

## 13. Troubleshooting

### Login returns 401 for all demo users
Passwords were hashed incorrectly. Fix:
```cmd
cd D:\scripts\bike_theft_tracker
call venv\Scripts\activate.bat
cd btt-backend
python manage.py create_demo_users --reset
```

### Registration returns 400
Check that your request body includes `confirm_password` (not `confirm`):
```json
{ "confirm_password": "Secure@123" }
```

### `vite is not recognized` / `npm is not recognized`
Node.js is not on your PATH. Use the full path or add it:
```cmd
SET PATH=C:\Program Files\nodejs;%PATH%
npm run dev
```
Or just run `start.bat` which sets the PATH automatically.

### `call venv\Scripts\activate.bat` fails in PowerShell
`call` is CMD-only. Use this in PowerShell instead:
```powershell
& .\venv\Scripts\Activate.ps1
```

### Django: `GDAL_LIBRARY_PATH` / `GEOS_LIBRARY_PATH` errors
Edit `btt-backend/.env` and set the correct DLL paths:
```
GDAL_LIBRARY_PATH=C:\OSGeo4W\bin\gdal311.dll
GEOS_LIBRARY_PATH=C:\OSGeo4W\bin\geos_c.dll
```

### PostgreSQL connection refused on port 5433
```powershell
# Check if it's running
& "C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe" -D "C:\Users\Maaz\localdev\postgresql-15\data" status

# Start it
& "C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe" -D "C:\Users\Maaz\localdev\postgresql-15\data" -o "-p 5433" start
```

### Port 8000 or 3000 already in use
```cmd
:: Kill whatever is on port 8000
for /f "tokens=5" %a in ('netstat -aon ^| findstr ":8000 "') do taskkill /PID %a /F

:: Kill whatever is on port 3000
for /f "tokens=5" %a in ('netstat -aon ^| findstr ":3000 "') do taskkill /PID %a /F
```
Or just run `start.bat` which does this automatically.

### Pytest coverage is below 80%
```cmd
:: Check what's not covered
pytest --cov-report=term-missing
start htmlcov\index.html
```

### Migration errors after model changes
```cmd
python manage.py makemigrations
python manage.py migrate
```
If migrations conflict: `python manage.py migrate --run-syncdb`

### Django shell — quick data inspection
```cmd
python manage.py shell
```
```python
from apps.users.models import CustomUser
from apps.bikes.models import Bike
from apps.reports.models import TheftReport
from apps.sightings.models import Sighting

# Check all users
CustomUser.objects.values('email', 'role', 'is_active', 'is_verified')

# Check a user's password hash (should start with pbkdf2_sha256)
u = CustomUser.objects.get(email='owner000@demo.btt')
print(u.password[:30])

# Count by role
from django.db.models import Count
CustomUser.objects.values('role').annotate(count=Count('id'))

# Check reports by status
TheftReport.objects.values('status').annotate(count=Count('id'))
```

---

## Quick Reference Card

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STARTUP & SHUTDOWN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Start everything              start.bat
  Kill Django (port 8000)       for /f "tokens=5" %a in ('netstat -aon ^| findstr ":8000 "') do taskkill /PID %a /F
  Kill React  (port 3000)       for /f "tokens=5" %a in ('netstat -aon ^| findstr ":3000 "') do taskkill /PID %a /F
  Kill all Python               taskkill /IM python.exe /F
  Kill all Node                 taskkill /IM node.exe /F
  Stop PostgreSQL               pg_ctl -D <PGDATA> stop

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  VIRTUAL ENVIRONMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Create                        python -m venv venv
  Activate (CMD)                call venv\Scripts\activate.bat
  Activate (PowerShell)         & .\venv\Scripts\Activate.ps1
  Activate (Bash)               source venv/Scripts/activate
  Deactivate (any shell)        deactivate
  Install deps                  pip install -r requirements.txt
  Delete & recreate             rmdir /s /q venv && python -m venv venv

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DJANGO BACKEND
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Run server                    python manage.py runserver
  Migrate                       python manage.py migrate
  Make migrations               python manage.py makemigrations
  Django shell                  python manage.py shell
  DB shell (psql)               python manage.py dbshell
  Check config                  python manage.py check

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DEMO DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Re-seed users (fix 401)       python manage.py create_demo_users --reset
  Seed theft data               python manage.py seed_demo_data
  Hotspot analysis              python manage.py run_hotspot_analysis --all-cities
  Trend analytics               python manage.py run_trend_analytics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FRONTEND
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Start Vite dev server         npm run dev
  Install packages              npm install
  Production build              npm run build

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TESTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Run all tests                 run_tests.bat
  Backend only                  pytest --tb=short -q
  E2E only (headless)           npx playwright test
  E2E with browser visible      npx playwright test --headed
  E2E interactive UI            npx playwright test --ui

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DEMO LOGINS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Admin      admin@demo.btt                /  DemoAdmin@2024
  Authority  authority.karachi@demo.btt   /  Authority@2024
  Owner      owner000@demo.btt            /  Owner@2024
  Community  community@demo.btt           /  Community@2024
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
