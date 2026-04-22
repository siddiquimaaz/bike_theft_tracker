# Bike Theft Tracker — Fresh Machine Setup Guide
### (Any Machine — Linux, macOS, or Windows)

> Follow this guide to get the project running from scratch on a new machine.
> You do **not** need any prior setup — this guide covers everything from zero.

---

## Demo Reset Guide

For recurring "reset and run" steps on an already configured machine, see `RESET_RUNBOOK.md`.

---

## What You Will Install

| Component | Version | Why |
|-----------|---------|-----|
| Python | 3.11 | The runtime. Do NOT use 3.12+ (some ML packages lack wheels) |
| PostgreSQL | 15 | The database |
| PostGIS | 3.x | Geographic extension — needed for theft location queries |
| GDAL | any recent | C library that Django uses for coordinate math |
| Git | any | To clone the repository |

---

## Step 0 — Install Prerequisites

Choose your operating system:

---

### Linux (Ubuntu 22.04 / Debian)

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
    python3.11 python3.11-venv python3-pip \
    postgresql-15 postgresql-15-postgis-3 \
    gdal-bin libgdal-dev \
    git curl
```

Start PostgreSQL:

```bash
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

---

### macOS (Homebrew)

Install Homebrew first if you don't have it:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then:
```bash
brew install python@3.11 postgresql@15 postgis gdal git
brew services start postgresql@15
```

Add PostgreSQL to your PATH (add this to `~/.zshrc` or `~/.bash_profile`):
```bash
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
```

---

### Windows 11

Install each item in order:

**1. Python 3.11**
- Download from: https://www.python.org/downloads/release/python-3119/
- Pick "Windows installer (64-bit)"
- During install: **check "Add Python to PATH"**
- Verify: open PowerShell → `python --version` → should show `Python 3.11.x`

**2. PostgreSQL 15 + PostGIS**
- Download from: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
- Select version 15 for Windows x86-64
- Run the installer — keep all defaults
- When the **Stack Builder** opens after install:
  - Select your PostgreSQL 15 installation
  - Expand **Spatial Extensions** → check **PostGIS 3.x for PostgreSQL 15**
  - Click Next and let it install
- Note the password you set for the `postgres` user — you'll need it shortly

**3. GDAL (for Django GeoDjango)**

Open PowerShell **as Administrator** and run:
```powershell
winget install --id GISInternals.GDAL -e --accept-package-agreements --accept-source-agreements
```

If `winget` is not available, download from https://trac.osgeo.org/osgeo4w/ (choose the OSGeo4W network installer → Express install → GDAL).

**4. Git**
- Download from: https://git-scm.com/download/win
- Run installer with all defaults

---

## Step 1 — Get the Code

```bash
# Clone from GitHub (replace with actual repo URL)
git clone https://github.com/YOUR_USERNAME/bike-theft-tracker.git
cd bike-theft-tracker
```

If you received a zip file instead:
- Extract it anywhere (e.g. `C:\Projects\bike-theft-tracker\` or `~/projects/bike-theft-tracker/`)
- Open a terminal inside that folder

---

## Step 2 — Set Up the Database

### Linux / macOS

```bash
sudo -u postgres psql << 'EOF'
CREATE DATABASE bikethefttracker;
CREATE USER bttadmin WITH PASSWORD 'localdevpass123';
GRANT ALL PRIVILEGES ON DATABASE bikethefttracker TO bttadmin;
ALTER USER bttadmin CREATEDB;

\c bikethefttracker
CREATE EXTENSION IF NOT EXISTS postgis;

\c template1
CREATE EXTENSION IF NOT EXISTS postgis;
\q
EOF
```

### Windows

Open the **psql** tool (search "psql" in Start menu, or open it from `C:\Program Files\PostgreSQL\15\bin\psql.exe`).

When asked for password, enter the `postgres` password you set during install.

Run these commands one by one:

```sql
CREATE DATABASE bikethefttracker;
CREATE USER bttadmin WITH PASSWORD 'localdevpass123';
GRANT ALL PRIVILEGES ON DATABASE bikethefttracker TO bttadmin;
ALTER USER bttadmin CREATEDB;

\c bikethefttracker
CREATE EXTENSION IF NOT EXISTS postgis;

\c template1
CREATE EXTENSION IF NOT EXISTS postgis;

\q
```

> **Why `template1`?** When pytest creates a test database, it copies from `template1`.
> Installing PostGIS there means test databases automatically get the extension — no extra setup needed.

---

## Step 3 — Create Python Virtual Environment

Open a terminal in the project folder, then:

### Linux / macOS
```bash
python3.11 -m venv venv
source venv/bin/activate
```

### Windows (PowerShell)
```powershell
py -3.11 -m venv venv
venv\Scripts\Activate.ps1
```

### Windows (Command Prompt)
```bat
py -3.11 -m venv venv
venv\Scripts\activate.bat
```

Your prompt will change to show `(venv)` — this confirms the environment is active.

---

## Step 4 — Install Python Dependencies

With the venv active:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs Django, DRF, JWT, rapidfuzz, scikit-learn, pandas, psycopg, PostGIS bindings, and all other packages.

It will take 2–3 minutes — normal.

---

## Step 5 — Configure Environment Variables

Copy the example file:

```bash
# Linux / macOS
cp .env.example .env

# Windows
copy .env.example .env
```

Open `.env` in any text editor (VS Code, Notepad, etc.) and fill in the values:

```ini
# ─── REQUIRED — change these ───────────────────────────────────────────────────

# Generate a secret key — run this command and paste the output:
# python -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY=paste-your-generated-key-here

DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database — use the password you set in Step 2
DB_NAME=bikethefttracker
DB_USER=bttadmin
DB_PASSWORD=localdevpass123
DB_HOST=localhost
DB_PORT=5432

# Media files — absolute path to a folder where uploaded photos will be saved
# Linux/macOS example:  /home/yourname/bike-theft-tracker/media
# Windows example:      C:\Projects\bike-theft-tracker\media
MEDIA_ROOT=/absolute/path/to/bike-theft-tracker/media

# ─── OPTIONAL — leave as placeholders if not testing email/SMS ─────────────────

FRONTEND_URL=http://localhost:3000

# Email — only needed if testing registration verification emails
# Use a Gmail App Password: https://myaccount.google.com/apppasswords
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_gmail@gmail.com
EMAIL_HOST_PASSWORD=xxxx_xxxx_xxxx_xxxx
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Bike Theft Tracker <noreply@bikethefttracker.pk>

# SMS — only needed if testing recovery/sighting SMS alerts
TWILIO_ACCOUNT_SID=placeholder
TWILIO_AUTH_TOKEN=placeholder
TWILIO_FROM_NUMBER=+1234567890

JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
ALLOWED_UPLOAD_EXTENSIONS=jpg,jpeg,png
MAX_UPLOAD_SIZE_MB=2
```

> **Windows only:** If Django fails to start with `OSError: GDAL not found`, add these lines to `.env`:
> ```ini
> GDAL_LIBRARY_PATH=C:\Program Files\GDAL\gdal.dll
> GEOS_LIBRARY_PATH=C:\Program Files\GDAL\geos_c.dll
> ```
> Adjust the path to match where GDAL was installed on your machine.

---

## Step 6 — Create the Media Folder

Create the folder you put in `MEDIA_ROOT`:

```bash
# Linux / macOS
mkdir -p /absolute/path/to/bike-theft-tracker/media

# Windows
mkdir C:\Projects\bike-theft-tracker\media
```

---

## Step 7 — Run Database Migrations

```bash
python manage.py migrate
```

Expected output (last few lines):
```
Running migrations:
  Applying users.0001_initial... OK
  Applying bikes.0001_initial... OK
  Applying reports.0001_initial... OK
  Applying sightings.0001_initial... OK
  Applying notifications.0001_initial... OK
  Applying ml.0001_initial... OK
```

If you see errors, go to the **Troubleshooting** section below.

---

## Step 8 — Create an Admin Account

```bash
python manage.py createsuperuser
```

You will be prompted:

```
Email: admin@example.com
Full name: Admin User
Password: (type a strong password — not shown)
Password (again): (repeat)
Superuser created successfully.
```

---

## Step 9 — Start the Server

```bash
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
> Use the endpoints listed in the API Reference section, or open `http://localhost:8000/admin/` for the Django admin panel.

---

## Step 10 — Verify It Works

Open a browser and visit:

```
http://localhost:8000/api/auth/login/
```

You should see a DRF HTML form (or a JSON response) — this confirms the server is running correctly.

### Test login via curl:

```bash
# Linux / macOS
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}'

# Windows (Command Prompt)
curl -X POST http://localhost:8000/api/auth/login/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"admin@example.com\",\"password\":\"yourpassword\"}"
```

Successful response:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## Step 11 — Run the Test Suite (Optional but Recommended)

```bash
python -m pytest tests/
```

**Expected result:** All 241 tests passing, ≥ 80% coverage.

```
================= 241 passed in 98.58s (0:01:38) ===================
Required test coverage of 80% reached. Total coverage: 80.08%
```

---

## Step 12 — Load Demo Data (Optional)

To get realistic data for exploring the ML and analytics features:

```bash
python manage.py seed_demo_data
python manage.py run_hotspot_analysis --all-cities
python manage.py run_trend_analytics
```

Demo accounts created:

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@demo.btt | DemoAdmin@2024 |
| Authority — Karachi | authority.karachi@demo.btt | Authority@2024 |
| Authority — Lahore | authority.lahore@demo.btt | Authority@2024 |
| Owner | owner000@demo.btt | Owner@2024 |

---

## How to Use the API

### Using Postman

1. Download Postman from https://www.postman.com/downloads/
2. Create a new request
3. Set base URL to `http://localhost:8000`
4. For protected endpoints: go to the **Authorization** tab → select **Bearer Token** → paste your access token

### Using the Django Admin Panel

Visit http://localhost:8000/admin/ and log in with the superuser you created in Step 8.

---

## Complete API Reference

### Authentication — No Token Required

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register as Owner or Community Reporter |
| POST | `/api/auth/login/` | Get JWT access + refresh tokens |
| POST | `/api/auth/token/refresh/` | Refresh an expired access token |
| POST | `/api/auth/verify-email/{token}/` | Confirm email address (link is valid 24 hours) |
| POST | `/api/auth/forgot-password/` | Request a password reset email |
| POST | `/api/auth/reset-password/{token}/` | Set a new password (link valid 1 hour, one-use) |
| POST | `/api/auth/logout/` | Blacklist current refresh token |

### Bikes — Owner Only

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/bikes/` | Register a new bike |
| GET | `/api/bikes/` | List all my bikes |
| GET | `/api/bikes/{id}/` | Full bike detail |
| PUT | `/api/bikes/{id}/` | Update color, plate number, or photo |
| DELETE | `/api/bikes/{id}/` | Soft-delete (preserves theft evidence) |

### Reports — Role-Scoped

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| POST | `/api/reports/` | Owner | File a theft report |
| GET | `/api/reports/` | Owner / Authority / Admin | Owner sees own; Authority sees city; Admin sees all |
| GET | `/api/reports/{id}/` | Any authenticated | Full report detail |
| PUT | `/api/reports/{id}/status/` | Authority / Admin | Advance case status |
| DELETE | `/api/reports/{id}/` | Admin only | Soft-delete (evidence preserved) |
| POST | `/api/reports/{id}/recovery/` | Authority | Log a bike recovery |
| GET | `/api/reports/{id}/recovery/` | Any authenticated | View recovery details |
| PUT | `/api/reports/{id}/recovery/` | Authority | Amend recovery record |

**Case Status Flow:**
```
stolen  ──►  under_investigation  ──►  recovered  ──►  closed
  │                                                       ▲
  └───────────────────────────────────────────────────────┘
                    (direct close allowed)
```

### Sightings — Community Reporting

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| POST | `/api/sightings/` | Any authenticated | Submit a bike sighting |
| GET | `/api/sightings/` | Authority / Admin | All unverified sightings, sorted by match score |
| GET | `/api/sightings/{id}/` | Any authenticated | Sighting detail with fuzzy match candidate |
| PUT | `/api/sightings/{id}/verify/` | Authority / Admin | Verify sighting, link to bike, notify owner |

### ML / Analytics — Intelligence Features

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/api/ml/fuzzy-match/?engine={n}` | Authority | Match engine number against stolen bikes |
| GET | `/api/ml/fuzzy-match/?chassis={n}` | Authority | Match chassis number against stolen bikes |
| GET | `/api/ml/hotspots/?city={c}` | Authority / Admin | DBSCAN theft cluster data for map |
| GET | `/api/ml/trends/` | Admin | Monthly theft + recovery rates per city |
| GET | `/api/ml/recovery-zones/?lat=&lng=&radius_km=` | Admin | PostGIS recovery scatter near a point |
| POST | `/api/ml/trigger-reanalysis/` | Admin | Force immediate ML recompute |

### Notifications

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/api/notifications/` | Any authenticated | All my notifications + unread count |
| PUT | `/api/notifications/{id}/read/` | Any authenticated | Mark one as read |
| PUT | `/api/notifications/read-all/` | Any authenticated | Mark all as read |

### Admin Panel

| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| GET | `/api/admin/users/` | Admin | All users — filterable by role/city/status |
| POST | `/api/admin/users/authority/` | Admin | Create a police authority account |
| PUT | `/api/admin/users/{id}/status/` | Admin | Activate, deactivate, or change role |
| GET | `/api/admin/analytics/` | Admin | Live KPI dashboard |
| GET | `/api/admin/audit-logs/` | Admin | Immutable case status audit trail |

---

## User Roles Explained

| Role | How to Create | What They Can Do |
|------|--------------|-----------------|
| **Owner** | Self-register via `/api/auth/register/` with `"role":"owner"` | Register bikes, file theft reports, track status |
| **Community** | Self-register with `"role":"community"` | Submit sighting reports (no CNIC needed) |
| **Authority** | Admin creates via `/api/admin/users/authority/` | Manage reports in their city, verify sightings, log recoveries, run fuzzy match |
| **Admin** | Created via `python manage.py createsuperuser` | Full access to everything |

---

## Re-running After a Restart

Every time you restart the machine:

### Linux / macOS

PostgreSQL likely starts automatically. Just activate venv and run:

```bash
cd /path/to/bike-theft-tracker
source venv/bin/activate
python manage.py runserver
```

### Windows

PostgreSQL starts automatically as a Windows Service (installed by the EDB installer).
Just activate venv and run:

```bat
cd C:\path\to\bike-theft-tracker
venv\Scripts\activate.bat
python manage.py runserver
```

---

## Troubleshooting

### "Connection refused" — can't connect to database

**Linux/macOS:**
```bash
sudo systemctl status postgresql     # check if running
sudo systemctl start postgresql      # start if stopped
```

**Windows:**
- Press `Win + R` → type `services.msc` → find `postgresql-x64-15` → right-click → Start

---

### "django.db.utils.ProgrammingError: relation does not exist"

Migrations haven't been applied. Run:

```bash
python manage.py migrate
```

---

### "PostGIS extension not found" or "operator does not exist: geography"

PostGIS is not installed in the database. Run in psql:

```sql
\c bikethefttracker
CREATE EXTENSION IF NOT EXISTS postgis;

\c template1
CREATE EXTENSION IF NOT EXISTS postgis;
```

---

### "OSError: [WinError 127] — GDAL not found" (Windows only)

Add to `.env`:
```ini
GDAL_LIBRARY_PATH=C:\Program Files\GDAL\gdal.dll
GEOS_LIBRARY_PATH=C:\Program Files\GDAL\geos_c.dll
```

If GDAL was installed elsewhere, find the `.dll` file:
```powershell
Get-ChildItem -Path C:\ -Recurse -Filter "gdal*.dll" -ErrorAction SilentlyContinue
```

---

### "bttadmin permission denied to create database"

The database user is missing the CREATEDB permission (needed by pytest). Fix it:

```bash
# Linux/macOS
sudo -u postgres psql -c "ALTER USER bttadmin CREATEDB;"

# Windows (in psql as postgres user)
ALTER USER bttadmin CREATEDB;
```

---

### Port 5432 is already in use (Windows only)

Windows Hyper-V or WSL sometimes reserves port 5432. Change PostgreSQL port:

1. In psql: `ALTER SYSTEM SET port = 5433;` then restart PostgreSQL service
2. In `.env`: change `DB_PORT=5432` to `DB_PORT=5433`

---

### "ModuleNotFoundError: No module named 'django'"

The virtual environment is not active. Run:

```bash
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate.bat
```

---

### Tests fail with "database is being accessed by other users"

Another process is holding a connection to the test database. Close all psql connections and retry, or restart PostgreSQL.

---

## Everyday Commands Reference

```bash
# Start dev server
python manage.py runserver

# Run all tests
python -m pytest tests/

# Run tests (quick, no coverage)
python -m pytest tests/ --no-cov -q

# Apply new migrations
python manage.py migrate

# Create a migration after model change
python manage.py makemigrations

# Open Django shell
python manage.py shell

# Check for configuration errors
python manage.py check

# Seed demo data
python manage.py seed_demo_data

# Run ML analysis
python manage.py run_hotspot_analysis --all-cities
python manage.py run_trend_analytics
```
