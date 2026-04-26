# Bike Theft Tracker

**Group 58 | Batch 2022F | BS Computer Science | SSUET, Karachi**

An intelligent web platform for reporting, tracking, and recovering stolen motorcycles.
Built with Django 4.2 + DRF (backend) and React 18 + Vite (frontend), backed by PostgreSQL/PostGIS and a suite of ML analysis tools.

---

## Quick Start

```bat
:: Daily start (keeps existing data)
start.bat

:: Full reset + fresh seed (for demos / evaluations)
reset_and_start.bat
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000/api/ |
| Admin panel | http://localhost:8000/admin/ |

**Demo logins after seeding:**

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@demo.btt | DemoAdmin@2024 |
| Authority (Karachi) | authority.karachi@demo.btt | Authority@2024 |
| Owner | owner000@demo.btt | Owner@2024 |
| Community | community@demo.btt | Community@2024 |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 · Django 4.2 · DRF |
| Database | PostgreSQL 15 + PostGIS 3.3 |
| Frontend | React 18 · Vite · Tailwind CSS |
| Auth | JWT (SimpleJWT) |
| ML | scikit-learn DBSCAN · rapidfuzz · pandas |
| Notifications | In-app · Email (SMTP) · SMS (Twilio) |

---

## Project Structure

```
bike_theft_tracker/
├── btt-backend/          # Django API (apps/, tests/, config/)
├── btt-frontend/         # React app (src/)
├── docs/                 # All documentation
├── scripts/              # Utility scripts
├── start.bat             # Daily start
├── reset_and_start.bat   # Full reset + start
├── kill_all.bat          # Stop everything
└── run_tests.bat         # Run backend + E2E tests
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [COMMANDS.md](docs/COMMANDS.md) | Complete command reference (startup, DB, ML, tests) |
| [GUIDE.md](docs/GUIDE.md) | Developer setup guide |
| [USER_STORIES.md](docs/USER_STORIES.md) | Role-by-role user stories + test coverage table |
| [VERIFIED_DEMO_FLOW.md](docs/VERIFIED_DEMO_FLOW.md) | End-to-end demo narrative for evaluators |
| [ROLE_MATRIX.md](docs/ROLE_MATRIX.md) | Capability matrix — what each role can do |
| [RESET_RUNBOOK.md](docs/RESET_RUNBOOK.md) | Step-by-step full reset checklist |
| [BACKEND.md](docs/BACKEND.md) | Backend architecture overview |
| [README_NEWMACHINE.md](docs/README_NEWMACHINE.md) | First-time setup on a new machine |
| [README_LOCAL.md](docs/README_LOCAL.md) | Local dev environment notes |
| [FYP Document.docx](docs/FYP%20Document.docx) | Original FYP proposal |

---

## Features

- **4 roles**: Admin · Authority · Owner · Community — each with scoped dashboards and permissions
- **Bike registry**: engine + chassis number, plate, city, photo
- **Theft reports**: file → investigate → locate → verify → recover → close state machine
- **Sightings**: community submits partial numbers; rapidfuzz auto-matches against active cases
- **Owner handshake**: owner confirms/denies sightings; authority escalated automatically on deadline
- **City-scoped notifications**: authority and community alerted when a theft is filed in their city
- **ML dashboard** (Authority / Admin):
  - DBSCAN hotspot clustering — theft concentration zones
  - Theft→recovery corridor analysis — dominant movement directions
  - Recovery radius statistics — average km between theft and recovery
  - Trend analytics — monthly theft/recovery rates per city
  - Recovery zone analysis — PostGIS spatial query
- **Audit log**: append-only, DB-level REVOKE prevents modification
- **378 backend tests · ≥ 90 % coverage**

---

## Running Tests

```cmd
:: Backend (pytest)
cd btt-backend
pytest

:: Or use the batch shortcut
run_tests.bat
```
