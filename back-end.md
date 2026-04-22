# Bike Theft Tracker — Back-end (Django/DRF)

This project’s back-end is a **Django 4.2 + Django REST Framework** API that powers the Bike Theft Tracker app. It provides **JWT authentication**, **role-based access control**, and the core business workflows for tracking stolen bikes, handling sightings, and notifying users.

## What the back-end does

- **Authentication & accounts**
  - Registers users (primarily **Owner** and **Community** roles).
  - Logs users in and issues **JWT access/refresh tokens**.
  - Supports email verification + password reset flows (project-supported endpoints).
  - Enforces role-based permissions on endpoints (Owner/Authority/Admin/Community).

- **Bike registration (Owner)**
  - Owners can register bikes with identifying details (make/model/year, plate, engine/chassis, city).
  - Owners can list, update, and remove their own bikes.

- **Theft reports (Owner → Authority workflow)**
  - Owners file theft reports for a registered bike with date/city/location details.
  - Authorities manage the report lifecycle (status transitions such as *stolen → under_investigation → recovered → closed*).
  - Recovery details can be recorded and viewed (role-scoped).

- **Sightings + verification (Community/Authority → Authority workflow)**
  - Community/Authority users can submit sightings with partial numbers and location context.
  - Authority users can review sightings, verify a match, and link the sighting to a bike/report.
  - The system integrates a **fuzzy matching** approach to help identify likely matches from partial/dirty identifiers.

- **Notifications (all authenticated roles)**
  - Produces notifications for key events (e.g., status updates, verified sightings).
  - Users can list notifications, mark one read, or mark all read.

- **ML/analytics endpoints (Authority/Admin)**
  - Provides analytics such as **hotspots** (clustered theft locations) and **trend** reporting.
  - Supports “reanalysis” style operations (admin-only) to recompute analytics after new data.

## Data & infrastructure

- **Database**: PostgreSQL (port **5433** locally) with **PostGIS** enabled for GIS/location features.
- **GeoDjango dependencies**: Uses GDAL/GEOS on Windows for spatial functionality.
- **Project structure**: Back-end code lives in `btt-backend/` with feature apps under `btt-backend/apps/`.

## API surface (high-level)

Base URL (local): `http://localhost:8000`

- **Auth**: `/api/auth/*` (login/register/refresh/logout, etc.)
- **Bikes**: `/api/bikes/*`
- **Reports**: `/api/reports/*`
- **Sightings**: `/api/sightings/*`
- **Notifications**: `/api/notifications/*`
- **ML/Analytics**: `/api/ml/*`
- **Admin**: `/api/admin/*`

## Local development (quick)

From repo root:

```cmd
call venv\Scripts\activate.bat
cd btt-backend
python manage.py migrate
python manage.py create_demo_users
python manage.py runserver 8000
```

## Testing

Back-end tests are written with **pytest** and run from `btt-backend/` with the venv active:

```cmd
cd D:\scripts\bike_theft_tracker
call venv\Scripts\activate.bat
cd btt-backend
pytest --tb=short -q
```

## Useful project docs

- `COMMANDS.md`: Full command reference (startup, DB, testing, troubleshooting)
- `RESET_RUNBOOK.md`: Full reset + restart checklist for demos
- `btt-backend/.env.example`: Environment variables template

