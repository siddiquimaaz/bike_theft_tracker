# Bike Theft Tracker — Complete Run & Deploy Guide

> **Group 58 | Batch 2022F | BS Computer Science | SSUET, Karachi**

---

## Demo Reset Guide

Use `RESET_RUNBOOK.md` when you need to flush everything and start from a clean state before a presentation.

---

## What This App Does

Bike Theft Tracker is a REST API backend that lets four types of users manage bike theft cases end-to-end:

| Role | What they can do |
|------|-----------------|
| **Owner** | Register bikes, file theft reports, track case status, view recovery details |
| **Community** | Submit sightings of suspicious bikes (with partial engine/chassis numbers) |
| **Authority** (Police) | Manage reports in their city, verify sightings, log recoveries, run fuzzy-match searches |
| **Admin** | Full access — manage all users, view analytics dashboard, trigger ML reanalysis |

### Key Features

| Feature | How it works |
|---------|-------------|
| **JWT Authentication** | Access tokens (15 min) + refresh tokens (7 days). Login blocked until email verified. |
| **Bike Registration** | Owner registers bike with engine number, chassis number, photo. Numbers are immutable. |
| **Theft Reports** | Owner files a report → status machine: `stolen → under_investigation → recovered → closed` |
| **Fuzzy Matching** | Authority searches by partial/damaged engine or chassis number — uses RapidFuzz WRatio scoring (HIGH/MEDIUM/LOW confidence labels) |
| **Sightings** | Anyone authenticated submits a sighting. Fuzzy match runs automatically on submission. Authority verifies → owner gets notified. |
| **Hotspot Clustering** | DBSCAN algorithm clusters theft locations → shows high-crime zones on map |
| **Trend Analytics** | Pandas aggregation of monthly theft/recovery rates per city |
| **Recovery Zones** | PostGIS `ST_DWithin` query — shows where bikes stolen near a given point were later found |
| **Notifications** | In-app notifications + email (Gmail SMTP) + SMS (Twilio) for high-priority events |
| **Rate Limiting** | Login throttled to 5 attempts per 15 minutes per IP |
| **Audit Log** | Every status change is logged — immutable, never deleted |

---

## Scenario 1 — Run on THIS Machine (Windows, Already Set Up)

This machine has the portable PostgreSQL at `C:\Users\Maaz\localdev\postgresql-15\`.

### Step 1 — Start PostgreSQL

Open a terminal in the project folder and run:

```bat
C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe ^
  -D C:\Users\Maaz\localdev\postgresql-15\data ^
  -o "-p 5433" ^
  -l C:\Users\Maaz\localdev\postgresql-15\data\pg.log ^
  start
```

Or just double-click **`start_dev.bat`** in the project root — it starts PostgreSQL and the Django server in one go.

### Step 2 — Activate the Virtual Environment

```bat
venv\Scripts\activate.bat
```

### Step 3 — Run the Server

```bat
python manage.py runserver
```

API is live at: **http://localhost:8000/api/**

### Step 4 — Run Tests (optional)

```bat
python -m pytest tests/
```

Expected: **341 tests, 80%+ coverage**.

### Step 5 — Stop PostgreSQL when done

```bat
C:\Users\Maaz\localdev\postgresql-15\pgsql\bin\pg_ctl.exe ^
  -D C:\Users\Maaz\localdev\postgresql-15\data stop
```

### Quick Reference — Existing Accounts

| Role | Email | Password |
|------|-------|----------|
| Admin (superuser) | siddiquimaaz88@gmail.com | *(the one you set during createsuperuser)* |

> **Tip:** To create demo data with multiple roles, run:
> ```bat
> python manage.py seed_demo_data
> ```
> This creates 120 realistic records plus demo accounts (see credentials in README.md).

---

## Scenario 2 — Run on Someone Else's Machine

### Prerequisites They Must Install

#### Option A — Linux / macOS (Recommended, easiest)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
    postgresql-15 postgresql-15-postgis-3 \
    gdal-bin libgdal-dev git

# macOS (Homebrew)
brew install python@3.11 postgresql@15 postgis gdal git
```

#### Option B — Windows

1. **Python 3.11** — download from https://www.python.org/downloads/  
   During install: check "Add Python to PATH"

2. **PostgreSQL 15 + PostGIS** — download the installer from https://www.enterprisedb.com/downloads/postgres-postgresql-downloads  
   During install: select the "PostGIS" component in the Stack Builder that opens after install.

3. **GDAL for GeoDjango** — run in PowerShell (admin):
   ```powershell
   winget install --id GISInternals.GDAL -e --accept-package-agreements
   ```
   Or download from https://trac.osgeo.org/osgeo4w/ (OSGeo4W installer, choose "GDAL").

---

### Setup Steps (all platforms)

#### 1. Get the Code

```bash
git clone https://github.com/YOUR_USERNAME/bike-theft-tracker.git
cd bike-theft-tracker
```

Or if no Git repo yet — copy the project folder to their machine.

#### 2. Create the Database

**Linux/macOS:**
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
EOF
```

**Windows (in psql shell — run as postgres user):**
```sql
CREATE DATABASE bikethefttracker;
CREATE USER bttadmin WITH PASSWORD 'localdevpass123';
GRANT ALL PRIVILEGES ON DATABASE bikethefttracker TO bttadmin;
ALTER USER bttadmin CREATEDB;
\c bikethefttracker
CREATE EXTENSION IF NOT EXISTS postgis;
\c template1
CREATE EXTENSION IF NOT EXISTS postgis;
```

> The `template1` PostGIS install is needed so test databases auto-inherit the extension.

#### 3. Create Virtual Environment & Install Dependencies

```bash
# Linux/macOS
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Windows (PowerShell)
py -3.11 -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

```ini
SECRET_KEY=any-random-50-char-string   # generate: python -c "import secrets; print(secrets.token_urlsafe(50))"
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=bikethefttracker
DB_USER=bttadmin
DB_PASSWORD=localdevpass123
DB_HOST=localhost
DB_PORT=5432          # change to 5433 if 5432 is occupied (e.g. WSL on Windows)

MEDIA_ROOT=/absolute/path/to/project/media    # must be absolute
FRONTEND_URL=http://localhost:3000

# Leave email/SMS as placeholders if not testing those features
EMAIL_HOST_USER=placeholder@gmail.com
EMAIL_HOST_PASSWORD=placeholder
TWILIO_ACCOUNT_SID=placeholder
TWILIO_AUTH_TOKEN=placeholder
TWILIO_FROM_NUMBER=+1234567890
```

**Windows only** — if Django fails to start with a GDAL error, add these to `.env`:
```ini
GDAL_LIBRARY_PATH=C:\Program Files\GDAL\gdal.dll
GEOS_LIBRARY_PATH=C:\Program Files\GDAL\geos_c.dll
```
*(adjust path to wherever GDAL was installed)*

#### 5. Run Migrations & Create Admin

```bash
python manage.py migrate
python manage.py createsuperuser
```

#### 6. Start the Server

```bash
python manage.py runserver
```

API at: **http://localhost:8000/api/**

#### 7. (Optional) Load Demo Data

```bash
python manage.py seed_demo_data
python manage.py run_hotspot_analysis --all-cities
python manage.py run_trend_analytics
```

---

## Scenario 3 — Deploy to GitHub + Third Person Runs It

### Part A — Push to GitHub

#### 1. Ensure `.gitignore` is Correct

The project should already have `.gitignore`. Verify these are listed:

```
.env
venv/
.venv/
__pycache__/
*.pyc
htmlcov/
media/
*.log
db.sqlite3
```

If `.gitignore` doesn't exist, create it with the above content.

#### 2. Initialize Git & Push

```bash
cd D:\scripts\bike_theft_tracker

git init
git add .
git commit -m "Initial commit — Bike Theft Tracker backend"

# Create a new repo on GitHub (github.com → New repository)
# Then:
git remote add origin https://github.com/YOUR_USERNAME/bike-theft-tracker.git
git branch -M main
git push -u origin main
```

> **NEVER commit `.env`** — it contains your DB password, secret key, and API tokens.  
> The `.env.example` file is what gets committed — it has placeholder values only.

#### 3. Verify on GitHub

Make sure these files are visible on GitHub:
- `README.md` and `GUIDE.md`
- `requirements.txt`
- `.env.example`
- `manage.py`
- `apps/` folder
- `tests/` folder
- `deploy/` folder
- `.gitignore`

And these are **NOT** there:
- `.env` (secret keys)
- `venv/` (too large, platform-specific)
- `media/` (uploaded files)

---

### Part B — Third Person Clones and Runs It

They follow these exact steps:

#### Step 1 — Install Prerequisites

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
    postgresql-15 postgresql-15-postgis-3 \
    gdal-bin libgdal-dev git
```

**macOS:**
```bash
brew install python@3.11 postgresql@15 postgis gdal
brew services start postgresql@15
```

**Windows:**
- Python 3.11 from python.org
- PostgreSQL 15 + PostGIS via EDB installer (enterprisedb.com)
- GDAL via `winget install GISInternals.GDAL` or OSGeo4W

#### Step 2 — Clone the Repo

```bash
git clone https://github.com/YOUR_USERNAME/bike-theft-tracker.git
cd bike-theft-tracker
```

#### Step 3 — Create Virtual Environment

```bash
# Linux/macOS
python3.11 -m venv venv
source venv/bin/activate

# Windows
py -3.11 -m venv venv
venv\Scripts\activate
```

#### Step 4 — Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 5 — Set Up the Database

Start PostgreSQL if not running, then:

```bash
# Linux/macOS
sudo -u postgres psql -c "CREATE DATABASE bikethefttracker;"
sudo -u postgres psql -c "CREATE USER bttadmin WITH PASSWORD 'localdevpass123';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE bikethefttracker TO bttadmin;"
sudo -u postgres psql -c "ALTER USER bttadmin CREATEDB;"
sudo -u postgres psql -d bikethefttracker -c "CREATE EXTENSION IF NOT EXISTS postgis;"
sudo -u postgres psql -d template1 -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

#### Step 6 — Configure Environment

```bash
cp .env.example .env
```

Edit `.env` — at minimum set:
```ini
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(50))">
DB_PASSWORD=localdevpass123
MEDIA_ROOT=/absolute/path/to/bike-theft-tracker/media
```

#### Step 7 — Run Migrations & Create Admin

```bash
python manage.py migrate
python manage.py createsuperuser
```

#### Step 8 — Start the Server

```bash
python manage.py runserver
```

**Done.** API is at http://localhost:8000/api/

---

## Testing the API (All Scenarios)

Once the server is running, use any of these tools:

### Using curl

```bash
# Register a new owner
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Ali Khan","email":"ali@test.com","role":"owner","cnic":"4200012345678","password":"Test@12345","confirm_password":"Test@12345"}'

# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"ali@test.com","password":"Test@12345"}'
# → returns {"access": "eyJ...", "refresh": "eyJ..."}

# Use the access token
curl http://localhost:8000/api/bikes/ \
  -H "Authorization: Bearer eyJ..."
```

### Using Postman / Insomnia

1. Import as HTTP requests
2. Set base URL to `http://localhost:8000`
3. For protected endpoints: Add header `Authorization: Bearer <access_token>`

### Using Django Admin Panel

Visit http://localhost:8000/admin/ — log in with the superuser account you created.

---

## Full API Endpoint List

### Authentication — `/api/auth/`

| Method | Endpoint | Who | What |
|--------|----------|-----|------|
| POST | `/register/` | Public | Register as Owner or Community Reporter |
| POST | `/login/` | Public | Get JWT access + refresh tokens |
| POST | `/token/refresh/` | Public | Get new access token using refresh token |
| POST | `/verify-email/{token}/` | Public | Verify email address (24h link) |
| POST | `/forgot-password/` | Public | Request password reset email |
| POST | `/reset-password/{token}/` | Public | Set new password (1h link, one-use) |
| POST | `/logout/` | Any logged-in | Invalidate refresh token |

### Bikes — `/api/bikes/`

| Method | Endpoint | Who | What |
|--------|----------|-----|------|
| POST | `/` | Owner | Register a new bike (engine no., chassis no., photo) |
| GET | `/` | Owner | List all my bikes |
| GET | `/{id}/` | Owner | Full bike detail including theft status |
| PUT | `/{id}/` | Owner | Update color, plate number, or photo |
| DELETE | `/{id}/` | Owner | Soft-delete bike (preserves theft evidence) |

### Reports — `/api/reports/`

| Method | Endpoint | Who | What |
|--------|----------|-----|------|
| POST | `/` | Owner | File a theft report for your bike |
| GET | `/` | Owner / Authority / Admin | Owner → own reports; Authority → city reports; Admin → all |
| GET | `/{id}/` | Any logged-in | Full report detail |
| PUT | `/{id}/status/` | Authority / Admin | Advance status (`stolen → under_investigation → recovered → closed`) |
| DELETE | `/{id}/` | Admin | Soft-delete report (evidence preserved) |
| POST | `/{id}/recovery/` | Authority | Log a recovery record for a report |
| GET | `/{id}/recovery/` | Any logged-in | Get recovery details (owners see limited view) |
| PUT | `/{id}/recovery/` | Authority | Amend recovery record |

**Status machine:**
```
stolen → under_investigation → recovered → closed
       ↘________________________↗
         (direct close allowed)
```

### Sightings — `/api/sightings/`

| Method | Endpoint | Who | What |
|--------|----------|-----|------|
| POST | `/` | Any logged-in | Submit a bike sighting (partial engine/chassis number OK) |
| GET | `/` | Authority / Admin | List all unverified sightings, ordered by fuzzy match score |
| GET | `/{id}/` | Any logged-in | Sighting detail with fuzzy match candidate |
| PUT | `/{id}/verify/` | Authority / Admin | Verify sighting, link to bike, notify owner |

### ML / Analytics — `/api/ml/`

| Method | Endpoint | Who | What |
|--------|----------|-----|------|
| GET | `/fuzzy-match/?engine={n}` | Authority | Search stolen bikes by engine number (returns confidence score) |
| GET | `/fuzzy-match/?chassis={n}` | Authority | Search stolen bikes by chassis number |
| GET | `/hotspots/?city={c}` | Authority / Admin | Theft hotspot cluster map data (DBSCAN) |
| GET | `/trends/` | Admin | Monthly theft + recovery trend data per city |
| GET | `/recovery-zones/?lat=&lng=&radius_km=` | Admin | Where bikes stolen near a point were later recovered |
| POST | `/trigger-reanalysis/` | Admin | Force re-run hotspot + trend analysis immediately |

### Notifications — `/api/notifications/`

| Method | Endpoint | Who | What |
|--------|----------|-----|------|
| GET | `/` | Any logged-in | My notifications + unread count in response |
| PUT | `/{id}/read/` | Any logged-in | Mark one notification as read |
| PUT | `/read-all/` | Any logged-in | Mark all notifications as read |

### Admin — `/api/admin/`

| Method | Endpoint | Who | What |
|--------|----------|-----|------|
| GET | `/users/` | Admin | All users — filter by role/city/status |
| POST | `/users/authority/` | Admin | Create a police authority account |
| PUT | `/users/{id}/status/` | Admin | Activate, deactivate, or change a user's role |
| GET | `/analytics/` | Admin | Live KPI dashboard (report counts, recovery rate, city breakdown) |
| GET | `/audit-logs/` | Admin | Immutable log of every case status change |

---

## Running the Test Suite

```bash
# All tests with coverage report
python -m pytest tests/

# Single test file
python -m pytest tests/test_auth.py -v

# With HTML coverage report (opens at htmlcov/index.html)
python -m pytest tests/ --cov-report=html

# Skip coverage threshold (for quick checks)
python -m pytest tests/ --no-cov -q
```

**Expected result:** 241 tests passing, ≥ 80% coverage.

---

## ML Management Commands

```bash
# Run DBSCAN hotspot analysis (saves to ML cache table)
python manage.py run_hotspot_analysis              # All cities (national)
python manage.py run_hotspot_analysis --city Karachi
python manage.py run_hotspot_analysis --all-cities

# Run monthly trend analytics
python manage.py run_trend_analytics

# Seed realistic demo data
python manage.py seed_demo_data                    # 120 records
python manage.py seed_demo_data --count 200        # More records
python manage.py seed_demo_data --clear            # Wipe and reseed
```

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `could not connect to server: port 5432` | PostgreSQL not running | Start PostgreSQL service (`pg_ctl start` or Windows Services) |
| `OSError: [WinError 127] GDAL not found` | Wrong GDAL path in `.env` | Set `GDAL_LIBRARY_PATH` to the correct `.dll` path |
| `django.db.utils.OperationalError: postgis not installed` | PostGIS extension missing | Run `CREATE EXTENSION postgis;` in the database as superuser |
| `KeyError: '15min'` on login | Old cached `.pyc` with old throttle class | Delete `__pycache__` folders and restart server |
| `bttadmin does not have CREATEDB privilege` | User missing permission | Run `ALTER USER bttadmin CREATEDB;` in psql |
| `ModuleNotFoundError: No module named 'rasterio'` | Wrong venv activated | Activate correct venv: `venv\Scripts\activate` |
| Port 5432 blocked on Windows | Hyper-V / WSL reserves it | Use port 5433 — set `DB_PORT=5433` in `.env` |

---

## Project Structure

```
bike_theft_tracker/
├── apps/
│   ├── users/          # Auth, JWT, user management, RBAC permissions
│   ├── bikes/          # Bike registration and management
│   ├── reports/        # Theft reports, status machine, recovery records
│   ├── sightings/      # Community sighting submission and verification
│   ├── notifications/  # In-app, email (Gmail), SMS (Twilio) notifications
│   └── ml/             # Fuzzy matching, DBSCAN clustering, trend analytics
├── config/
│   ├── settings.py     # Django settings (reads from .env)
│   └── urls.py         # Root URL routing
├── tests/              # pytest test suite (241 tests, 80%+ coverage)
├── deploy/             # Nginx, Gunicorn, cron configs for production
├── .env.example        # Template — copy to .env and fill in values
├── requirements.txt    # All Python dependencies
├── manage.py           # Django management CLI
├── start_dev.bat       # One-click startup script (Windows, this machine)
├── README.md           # Tech stack + API reference summary
└── GUIDE.md            # This file — complete run and deploy guide
```
