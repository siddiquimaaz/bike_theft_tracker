# Bike Theft Tracker — Local Machine Setup Guide
### (This Machine — Windows 11, Portable Stack Already Installed)

> This guide is for **Maaz's development machine** where PostgreSQL, the virtual environment,
> and all dependencies are already installed. No new installs are needed.

---

## Demo Reset Guide

Before presenting the app, follow `RESET_RUNBOOK.md` for a complete clean reset workflow.

---

## What's Already Set Up

| Component | Location | Details |
|-----------|----------|---------|
| PostgreSQL 15 | `C:\Users\Maaz\localdev\postgresql-15\` | Portable, runs on port **5433** |
| PostGIS 3.6 | Installed inside PostgreSQL above | Extension active in `bikethefttracker` + `template1` |
| Python venv | `D:\scripts\bike_theft_tracker\venv\` | Python 3.11.9, all packages installed |
| GDAL DLL | `venv\Lib\site-packages\rasterio.libs\` | Loaded via `.env` |
| GEOS DLL | `venv\Lib\site-packages\shapely.libs\` | Loaded via `.env` |
| Database | `bikethefttracker` | User: `bttadmin` / Password: `localdevpass123` |
| Superuser | `siddiquimaaz88@gmail.com` | Created during initial setup |

---

## Starting the App — Quick Way

Double-click **`start.bat`** in the project root.

It will:
1. Start PostgreSQL on port 5433
2. Activate the virtual environment
3. Launch the Django dev server at http://localhost:8000

---

## Starting the App — Manual Way

Open a terminal inside `D:\scripts\bike_theft_tracker\` and run each step:

### Step 1 — Start PostgreSQL

```bat
C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe ^
  -D C:\Users\Maaz\localdev\postgresql-15\data ^
  -o "-p 5433" ^
  -l C:\Users\Maaz\localdev\postgresql-15\data\pg.log ^
  start
```

Expected output:
```
waiting for server to start.... done
server started
```

### Step 2 — Activate the Virtual Environment

```bat
venv\Scripts\activate.bat
```

Your prompt changes to: `(venv) D:\scripts\bike_theft_tracker>`

### Step 3 — Start the Django Server

```bat
python manage.py runserver
```

Expected output:
```
Django version 4.2.11, using settings 'config.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

**The API is now live at: http://localhost:8000/api/**

> **Note:** Opening `http://127.0.0.1:8000/` in the browser shows a **404 — this is normal**.
> The app has no frontend or root page. Every valid URL starts with `/api/` or `/admin/`.
> Use the endpoints listed in the section below, or open `http://localhost:8000/admin/` for the Django admin panel.

---

## Stopping the App

1. Stop the Django server: press `Ctrl + C` in the server terminal

2. Stop PostgreSQL:
```bat
C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe ^
  -D C:\Users\Maaz\localdev\postgresql-15\data ^
  stop
```

---

## Check That Everything Works

Open your browser or Postman and visit:

```
http://localhost:8000/api/auth/login/
```

You should get a 405 Method Not Allowed (GET) or a 200 with a form (meaning the server is responding).

### Quick curl test:

```bat
curl -X POST http://localhost:8000/api/auth/login/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"siddiquimaaz88@gmail.com\",\"password\":\"YOUR_PASSWORD\"}"
```

A successful response looks like:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## Running the Test Suite

Make sure PostgreSQL is running, then:

```bat
venv\Scripts\activate.bat
python -m pytest tests/
```

**Expected result:** 381 tests passing, 90%+ coverage.

### Other test options:

```bat
:: Run a specific test file
python -m pytest tests/test_auth.py -v

:: Skip the 90% coverage threshold (faster for quick checks)
python -m pytest tests/ --no-cov -q

:: Generate an HTML coverage report (opens at htmlcov\index.html)
python -m pytest tests/ --cov-report=html
```

---

## Loading Demo Data (Optional)

To populate the database with realistic sample data for testing the ML features:

```bat
python manage.py seed_demo_data
python manage.py run_hotspot_analysis --all-cities
python manage.py run_trend_analytics
```

This creates **120 theft records** across multiple cities plus these demo accounts:

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@demo.btt | DemoAdmin@2024 |
| Authority (Karachi) | authority.karachi@demo.btt | Authority@2024 |
| Authority (Lahore) | authority.lahore@demo.btt | Authority@2024 |
| Owner | owner000@demo.btt | Owner@2024 |

---

## Creating a New Admin Account

If you need another superuser:

```bat
python manage.py createsuperuser
```

You'll be prompted for email, full name, and password.

---

## Checking the Database Directly

Connect to PostgreSQL using psql:

```bat
C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\psql.exe ^
  -U bttadmin -h localhost -p 5433 -d bikethefttracker
```

Useful SQL commands inside psql:

```sql
-- List all tables
\dt

-- Count users
SELECT role, COUNT(*) FROM users GROUP BY role;

-- Count theft reports
SELECT status, COUNT(*) FROM theft_reports GROUP BY status;

-- Exit psql
\q
```

---

## Django Admin Panel

Visit http://localhost:8000/admin/ and log in with the superuser account.

From here you can:
- Browse all database records
- Manually create/edit users, bikes, reports
- View audit logs
- Check ML cache entries

---

## API at a Glance

All endpoints are prefixed with `http://localhost:8000/api/`

### Authentication — no token needed

| Method | URL | What it does |
|--------|-----|-------------|
| POST | `/auth/register/` | Register a new Owner or Community user |
| POST | `/auth/login/` | Get access + refresh JWT tokens |
| POST | `/auth/token/refresh/` | Refresh an expired access token |
| POST | `/auth/verify-email/{token}/` | Confirm email (link sent at registration) |
| POST | `/auth/forgot-password/` | Request a password reset email |
| POST | `/auth/reset-password/{token}/` | Set a new password |
| POST | `/auth/logout/` | Invalidate your refresh token |

### Owner Endpoints — requires `Authorization: Bearer <token>`

| Method | URL | What it does |
|--------|-----|-------------|
| POST | `/bikes/` | Register a bike |
| GET | `/bikes/` | List my bikes |
| GET | `/bikes/{id}/` | Bike detail |
| PUT | `/bikes/{id}/` | Update color / plate / photo |
| DELETE | `/bikes/{id}/` | Soft-delete a bike |
| POST | `/reports/` | File a theft report |
| GET | `/reports/` | My theft reports |
| GET | `/reports/{id}/` | Report detail |
| GET | `/notifications/` | My notifications |
| PUT | `/notifications/{id}/read/` | Mark notification as read |
| PUT | `/notifications/read-all/` | Mark all as read |

### Authority Endpoints — police officers only

| Method | URL | What it does |
|--------|-----|-------------|
| GET | `/reports/` | All reports in my city |
| PUT | `/reports/{id}/status/` | Advance case status |
| POST | `/reports/{id}/recovery/` | Log a bike recovery |
| PUT | `/reports/{id}/recovery/` | Amend recovery record |
| GET | `/sightings/` | All unverified sightings |
| PUT | `/sightings/{id}/verify/` | Verify a sighting, notify owner |
| GET | `/ml/fuzzy-match/?engine={n}` | Fuzzy-match engine number |
| GET | `/ml/fuzzy-match/?chassis={n}` | Fuzzy-match chassis number |
| GET | `/ml/hotspots/` | Theft hotspot clusters |

### Admin Endpoints — admin only

| Method | URL | What it does |
|--------|-----|-------------|
| GET | `/admin/users/` | All users |
| POST | `/admin/users/authority/` | Create authority account |
| PUT | `/admin/users/{id}/status/` | Activate / deactivate user |
| GET | `/admin/analytics/` | Live KPI dashboard |
| GET | `/admin/audit-logs/` | Case status audit trail |
| GET | `/ml/trends/` | Monthly theft/recovery trends |
| GET | `/ml/recovery-zones/?lat=&lng=` | Recovery zone heatmap data |
| POST | `/ml/trigger-reanalysis/` | Force ML recompute now |

---

## Troubleshooting — This Machine

### "Port 5433 — connection refused"

PostgreSQL is not running. Start it:

```bat
C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe ^
  -D C:\Users\Maaz\localdev\postgresql-15\data -o "-p 5433" start
```

### "OSError: GDAL not found" or "[WinError 127]"

The `.env` file is not loading correctly. Check that `.env` exists in the project root and contains:

```ini
GDAL_LIBRARY_PATH=D:\scripts\bike_theft_tracker\venv\Lib\site-packages\rasterio.libs\gdal-06c8a783fc258d4e4739c3a67902a55f.dll
GEOS_LIBRARY_PATH=D:\scripts\bike_theft_tracker\venv\Lib\site-packages\shapely.libs\geos_c-072b7a9224d16d3e4ab2395bb855b2d3.dll
```

### "ModuleNotFoundError: No module named 'django'"

Wrong virtual environment is active. Run:

```bat
venv\Scripts\activate.bat
```

Make sure the prompt shows `(venv)` before the path.

### "coverage: 13% — all tests pass but coverage is low"

PostgreSQL was not running when tests started (fixtures error out silently in some modes). Start PostgreSQL first, then re-run.

### Tests pass but Django server fails to start

Check for syntax errors introduced in recent edits:

```bat
python manage.py check
```

---

## Project File Structure

```
D:\scripts\bike_theft_tracker\
├── apps\
│   ├── users\         User model, auth views, JWT, RBAC permissions
│   ├── bikes\         Bike registration and management
│   ├── reports\       Theft reports, status machine, recovery records
│   ├── sightings\     Community sightings and authority verification
│   ├── notifications\ Email, SMS, in-app notifications
│   └── ml\            Fuzzy match, DBSCAN clustering, trend analytics
├── config\
│   ├── settings.py    All Django settings (reads from .env)
│   └── urls.py        Root URL routing
├── tests\             381 tests — 90%+ coverage
├── deploy\            Nginx, Gunicorn, cron configs (for production)
├── venv\              Python 3.11 virtual environment (DO NOT commit)
├── .env               Your local secrets (DO NOT commit)
├── .env.example       Template with placeholder values (safe to commit)
├── requirements.txt   Python dependencies
├── manage.py          Django CLI
├── start.bat          One-click startup script for this machine
├── pytest.ini         Test configuration
├── README.md          Tech stack + full API reference
├── README_LOCAL.md    This file
└── GUIDE.md           Complete 3-scenario run/deploy guide
```
