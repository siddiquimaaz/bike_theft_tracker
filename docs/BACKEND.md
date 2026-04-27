# Bike Theft Tracker — Back-end (Django/DRF)

This project’s back-end is a **Django 4.2 + Django REST Framework** API that powers the Bike Theft Tracker app. It provides **JWT authentication**, **role-based access control**, and the core business workflows for tracking stolen bikes, handling sightings, and notifying users.

## What the back-end does

- **Authentication & accounts**
  - Registers users (primarily **Owner** and **Community** roles).
  - Logs users in and issues **JWT access/refresh tokens**.
  - Supports email verification + password reset flows (project-supported endpoints).
    Password reset confirmation (`POST /api/auth/password-reset/confirm/`) expects the body
    `{ "new_password": "...", "confirm_password": "..." }` — not a plain `password` field.
  - Enforces role-based permissions on endpoints (Owner/Authority/Admin/Community).

- **Bike registration (Owner)**
  - Owners can register bikes with identifying details (make/model/year, plate, engine/chassis, city).
  - Owners can list, update, and remove their own bikes.

- **Theft reports (Owner → Authority workflow)**
  - Owners file theft reports for a registered bike with date/city/location details.
  - Authorities manage the report lifecycle through the modern state machine:
    *new_case → under_review → active_investigation → bike_located → pending_verification → recovered → closed*.
    Legacy values (`stolen`, `under_investigation`) remain accepted on older reports for backwards compatibility.
  - **Authority cannot close a case directly.** `PUT /api/reports/{id}/status/` blocks
    `status=closed` for authority users and returns HTTP 403. Closure requires either:
    (a) the bike owner confirming receipt via `PUT /api/reports/{id}/recovery/confirm/`
    (transitions to `closed`, sets `owner_recovery_confirmed=True`), or (b) an admin
    using the status endpoint as an exceptional override for unresponsive owners.
    The CaseReportsPage authority UI shows an amber info banner on `pending_verification`
    and `recovered` cases explaining that owner confirmation is required.
  - Recovery details can be recorded and viewed (role-scoped); the owner finalises closure via
    `PUT /api/reports/<id>/recovery/confirm/`, which transitions the case to `closed` and broadcasts a
    thank-you to community contributors.

- **Sightings + verification (Community/Authority → Authority workflow)**
  - Community/Authority users can submit sightings with partial numbers and location context.
  - Authority users can review sightings, verify a match, and link the sighting to a bike/report.
  - The system integrates a **fuzzy matching** approach (RapidFuzz WRatio) to help identify likely
    matches from partial/dirty identifiers.
  - **Owner handshake**: when a sighting hits the owner-alert score, the owner is asked
    `yes` / `no` / `not_sure`. `yes` triggers an URGENT escalation to authorities;
    `not_sure` keeps the sighting open and auditable; missed-deadline sightings are
    auto-escalated by `auto_escalate_pending_owner_responses()`.
  - **Owner sighting visibility**: `GET /api/sightings/` for owner accounts returns both
    sightings submitted *by* the owner and sightings *of* their stolen bike that are pending
    owner confirmation (`owner_confirmation_status='pending'`, `is_archived=False`). Each
    sighting record includes an `is_about_my_bike` boolean flag. The frontend ReportsPage
    renders pending-confirmation sightings as an amber-bordered card section above the
    reports table with ✅ / ❌ / 🤷 response buttons.

- **Notifications (all authenticated roles)**
  - Produces notifications for key events (e.g., status updates, verified sightings).
  - Users can list notifications, mark one read, or mark all read.

- **ML/analytics endpoints (Authority/Admin)**
  - **Fuzzy match** (rapidfuzz WRatio) — engine/chassis number matching against all active theft reports.
  - **DBSCAN hotspot clustering** — identifies theft concentration zones from report location data.
  - **Trend analytics** — monthly theft/recovery counts and recovery rate per city.
  - **Recovery radius** — mean/median km distance between theft and recovery location (city-scoped).
  - **Corridor analysis** — DBSCAN on theft→recovery displacement vectors; identifies dominant movement directions (bearing + distance).
  - **Recovery zones** — PostGIS ST_DWithin query returning historical recovery points near a given location.
  - Admin can trigger full reanalysis (hotspot + trends + corridors + radius) on-demand via
    `POST /api/ml/trigger-reanalysis/`. Reanalysis runs **synchronously** — the endpoint
    returns HTTP 200 only after all four caches have been written, so the frontend can
    immediately refetch dashboards without polling or receiving stale 202 responses.
  - All heavy computation is cached in `MLAnalysisCache`; dashboards read from cache only.

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

