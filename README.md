# Bike Theft Tracker — Backend

Django 4.2 + DRF REST API for the Bike Theft Tracker FYP.
Group 58 | Batch 2022F | BS Computer Science | SSUET, Karachi

---

## Demo Reset Guide

For a full "start from zero" reset (stop services, flush DB, rerun migrations, optional superuser/demo setup, restart app), use:
- `RESET_RUNBOOK.md`

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Runtime | Python | 3.11 |
| Framework | Django + DRF | 4.2 / 3.14 |
| Auth | djangorestframework-simplejwt | 5.3 |
| Database | PostgreSQL + PostGIS | 15 / 3.3 |
| Fuzzy Match | rapidfuzz | 3.x |
| Clustering | scikit-learn DBSCAN | 1.3 |
| Analytics | pandas | 2.1 |
| SMS | Twilio | 8.x |
| Email | Django SMTP (Gmail) | built-in |
| Web Server | Nginx + Gunicorn | 1.24 / 21 |

---

## Local Development Setup

### 1. Prerequisites

```bash
# PostgreSQL 15 with PostGIS extension
sudo apt install postgresql-15 postgresql-15-postgis-3

# Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip

# GDAL (required for Django GIS)
sudo apt install gdal-bin libgdal-dev
```

### 2. Database

```sql
-- Run as postgres user
CREATE DATABASE bikethefttracker;
CREATE USER bttadmin WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE bikethefttracker TO bttadmin;
\c bikethefttracker
CREATE EXTENSION postgis;
```

### 3. Python Environment

```bash
cd bike_theft_tracker
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**

```powershell
cd bike_theft_tracker
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

For GeoDjango/PostGIS support on Windows, install GDAL and set `GDAL_LIBRARY_PATH` if needed:

```powershell
winget install --id GISInternals.GDAL -e --accept-package-agreements --accept-source-agreements
# Example (adjust DLL version if different):
setx GDAL_LIBRARY_PATH "C:\Program Files\GDAL\gdal311.dll"
```

### 4. Environment Variables

```bash
cp .env.example .env
# Edit .env — fill in DB credentials, JWT secret, email, Twilio
```

### 5. Django Setup

```bash
python manage.py migrate          # Creates all 8 tables + PostGIS setup
python manage.py createsuperuser  # Initial admin account
python manage.py collectstatic
```

### 6. Seed Demo Data (for ML demonstrations)

```bash
python manage.py seed_demo_data           # 120 realistic theft records
python manage.py run_hotspot_analysis --all-cities
python manage.py run_trend_analytics
```

**Demo credentials after seeding:**

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@demo.btt | DemoAdmin@2024 |
| Authority (Karachi) | authority.karachi@demo.btt | Authority@2024 |
| Authority (Lahore) | authority.lahore@demo.btt | Authority@2024 |
| Owner | owner000@demo.btt | Owner@2024 |

### 7. Run Development Server

```bash
python manage.py runserver
```

API is available at `http://localhost:8000/api/`

---

## Running Tests

```bash
pytest                        # All tests with coverage
pytest tests/test_auth.py     # Auth tests only
pytest tests/test_fuzzy_match.py -v   # Fuzzy match accuracy
pytest --cov=apps --cov-report=html   # HTML coverage report
```

**Minimum coverage target: 80%**

---

## API Reference

### Authentication — `/api/auth/`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/register/` | Public | Register Owner or Community |
| POST | `/login/` | Public | Returns access + refresh tokens |
| POST | `/token/refresh/` | Public | Refresh access token |
| POST | `/verify-email/{token}/` | Public | Email verification (24h expiry) |
| POST | `/forgot-password/` | Public | Send reset link |
| POST | `/reset-password/{token}/` | Public | Set new password |
| POST | `/logout/` | Auth | Blacklist refresh token |

### Bikes — `/api/bikes/`

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET | `/` | Owner | List my bikes |
| POST | `/` | Owner | Register new bike |
| GET | `/{id}/` | Owner | Bike detail |
| PUT | `/{id}/` | Owner | Update color/plate/photo |
| DELETE | `/{id}/` | Owner | Soft-delete |

### Reports — `/api/reports/`

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | `/` | Owner | File theft report |
| GET | `/` | Auth | Role-scoped list |
| GET | `/{id}/` | Auth | Report detail |
| PUT | `/{id}/status/` | Authority/Admin | Status transition |
| DELETE | `/{id}/` | Admin | Soft-delete |
| POST | `/{id}/recovery/` | Authority | Log recovery |
| GET | `/{id}/recovery/` | Auth | Recovery details |
| PUT | `/{id}/recovery/` | Authority | Amend recovery |

### Sightings — `/api/sightings/`

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | `/` | Auth | Submit sighting (auto fuzzy-match) |
| GET | `/` | Authority/Admin | Unverified sightings list |
| GET | `/{id}/` | Auth | Sighting detail |
| PUT | `/{id}/verify/` | Authority | Verify sighting, notify owner |

### ML — `/api/ml/`

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET | `/fuzzy-match/?engine={n}` | Authority | WRatio match engine number |
| GET | `/fuzzy-match/?chassis={n}` | Authority | WRatio match chassis number |
| GET | `/hotspots/?city={c}` | Authority/Admin | DBSCAN cluster data |
| GET | `/trends/` | Admin | Monthly theft/recovery trends |
| GET | `/recovery-zones/?lat=&lng=&radius_km=` | Admin | PostGIS recovery scatter |
| POST | `/trigger-reanalysis/` | Admin | Manual ML recompute |

### Notifications — `/api/notifications/`

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET | `/` | Auth | All notifications + unread count |
| PUT | `/{id}/read/` | Auth | Mark single as read |
| PUT | `/read-all/` | Auth | Mark all as read |

### Admin — `/api/admin/`

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET | `/users/` | Admin | All users (filterable) |
| POST | `/users/authority/` | Admin | Create authority account |
| PUT | `/users/{id}/status/` | Admin | Activate/deactivate/change role |
| GET | `/analytics/` | Admin | KPI dashboard stats |
| GET | `/audit-logs/` | Admin | Immutable audit log |

### Public Search — `/api/search/`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/bike/?q={query}` | Public | Search by engine/chassis/plate |
| GET | `/city/{city}/` | Public | Active report count in city |

---

## Report Status State Machine

```
stolen → under_investigation → recovered → closed
       ↘                                 ↗
         ────────────────────────────────
              (direct close allowed)
```

---

## ML Management Commands

```bash
# DBSCAN hotspot clustering
python manage.py run_hotspot_analysis              # National
python manage.py run_hotspot_analysis --city Karachi
python manage.py run_hotspot_analysis --all-cities

# Trend analytics
python manage.py run_trend_analytics

# Seed demo data
python manage.py seed_demo_data
python manage.py seed_demo_data --clear           # Wipe and reseed
python manage.py seed_demo_data --count 200       # More records
```

---

## Production Deployment

### Step-by-step

```bash
# 1. Provision Ubuntu 22.04 LTS VPS

# 2. Install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install nginx postgresql-15 postgresql-15-postgis-3 \
    python3.11 python3-pip git supervisor \
    gdal-bin libgdal-dev certbot python3-certbot-nginx -y

# 3. Database
sudo -u postgres psql -c "CREATE DATABASE bikethefttracker;"
sudo -u postgres psql -c "CREATE USER bttadmin WITH PASSWORD 'STRONG_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE bikethefttracker TO bttadmin;"
sudo -u postgres psql -d bikethefttracker -c "CREATE EXTENSION postgis;"

# 4. Application
git clone https://github.com/your-repo/bike-theft-tracker.git /var/www/btt
cd /var/www/btt/backend
pip3 install -r requirements.txt
cp .env.example .env       # ← Fill in all production values
python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser

# 5. Nginx
sudo cp deploy/nginx_btt.conf /etc/nginx/sites-available/btt
sudo ln -s /etc/nginx/sites-available/btt /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 6. SSL
sudo certbot --nginx -d yourdomain.com

# 7. Supervisor
sudo mkdir -p /var/log/btt
sudo cp deploy/supervisor_btt.conf /etc/supervisor/conf.d/btt.conf
sudo supervisorctl reread && sudo supervisorctl update
sudo supervisorctl start btt

# 8. Cron jobs
crontab -e
# Paste contents of deploy/crontab.txt

# 9. Seed + run ML
python manage.py seed_demo_data
python manage.py run_hotspot_analysis --all-cities
python manage.py run_trend_analytics
```

---

## Security Checklist

- [x] JWT: 15-min access tokens, 7-day refresh tokens (Bearer token flow)
- [x] PBKDF2+SHA256 password hashing (260,000 iterations)
- [x] All DB queries via Django ORM parameterized queries — no raw SQL
- [x] DRF Serializers validate every field before view logic
- [x] RBAC enforced per endpoint via custom permission classes
- [x] Rate limiting: DRF anon/user throttles + scoped login throttle (5/15min)
- [x] File uploads: MIME type verified server-side (python-magic), 2MB max
- [x] Security headers: X-Frame-Options, X-Content-Type-Options, HSTS
- [x] Soft-deletes only — evidence records are never hard-deleted
- [x] Immutable audit log — no UPDATE/DELETE on audit_logs table
- [x] `.env` never committed — `.gitignore` covers it from day one

---

