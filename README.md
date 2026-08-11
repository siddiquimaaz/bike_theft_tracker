# Bike Theft Tracker

**Group 58 | Batch 2022F | BS Computer Science | SSUET, Karachi**

An intelligent web platform for reporting, tracking, and recovering stolen motorcycles.
Built with Django 6.0 + DRF (backend) and React 19 + Vite (frontend), backed by PostgreSQL/PostGIS and a suite of ML analysis tools.

---

## Install (Windows)

**Double-click `install.bat`.** That is the whole thing.

It installs Python 3.12+ and Node 18+ via winget if they are missing, builds the
`venv`, downloads a portable PostgreSQL 15 + PostGIS into `.localdb\`, creates
the database and role, writes `btt-backend\.env`, applies migrations, seeds the
demo data, and installs the frontend packages. It then proves the install by
running a real PostGIS query through Django.

Nothing needs administrator rights and nothing is installed system-wide except
Python and Node themselves. The database is a self-contained copy inside the
repo — **deleting `.localdb\` removes it completely**, leaving no trace on the
machine.

Re-running is safe: every step detects what is already present and skips it, so
after a failure you only redo the part that failed.

| Switch | Effect |
|--------|--------|
| `install.bat -RebuildVenv` | Rebuild the virtualenv from scratch |
| `install.bat -ResetDb` | Delete and recreate the database cluster |
| `install.bat -NoSeed` | Skip the demo users and demo data |
| `install.bat -Force` | Re-download PostgreSQL and PostGIS |

Python dependencies install from **`btt-backend\requirements.lock.txt`**, which
pins every package including transitive ones to the exact versions this project
was tested against. If a pinned wheel has no build for the target machine, the
installer falls back to the unpinned `requirements.txt`.

Everything lands inside this folder — `venv\`, `.localdb\`, `node_modules\`,
about 1.8 GB in total. Nothing is written anywhere else on the machine.

### Installing without internet

`install.bat` downloads ~410 MB (PostgreSQL and PostGIS). To install on a machine
with no internet, put those two archives in **`vendor\`** and it uses them instead
of downloading. See [vendor/README.md](vendor/README.md) for the filenames and
links. Python and Node still need internet if the machine has neither.

---

## Quick Start

**Double-click `run.bat`.** It starts the database, opens a window each for the
backend and frontend, and opens the app in your browser. On a fresh clone it
runs the installer first, so `run.bat` alone is enough.

```bat
:: Start (keeps existing data)
run.bat

:: Full reset + fresh seed (for demos / evaluations)
reset_and_start.bat

:: Stop everything, database included
kill_all.bat

:: Backend tests
run_tests.bat
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:8001/api/ |
| Admin panel | http://localhost:8001/admin/ |

Ports are probed at launch — if 3001 or 8001 is busy, the next free one is used
and both sides are told where the other landed.

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
| Backend | Python 3.12+ · Django 6.0 · DRF 3.17 |
| Database | PostgreSQL 15 + PostGIS 3.3 |
| Frontend | React 19 · Vite 8 · Tailwind CSS 4 |
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
├── tools/                # setup / run / stop / test PowerShell scripts
├── scripts/              # Older utility scripts, superseded by tools/
├── .localdb/             # Portable PostgreSQL + PostGIS (git-ignored)
├── install.bat           # One-click install
├── run.bat               # One-click start
├── reset_and_start.bat   # Full reset + start
├── kill_all.bat          # Stop everything
└── run_tests.bat         # Run backend tests (-E2E adds Playwright)
```

Every `.bat` at the root is a thin wrapper that derives its paths from the repo
location, so the project runs from any folder on any machine.

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
- **376 backend tests · 92.8 % coverage**

---

## Running Tests

`run_tests.bat` starts the database if it is not already up, then runs pytest.

```cmd
:: Backend suite with coverage
run_tests.bat

:: Faster, no coverage report
run_tests.bat -NoCov

:: One file or one pattern — extra arguments go straight to pytest
run_tests.bat -k fuzzy
run_tests.bat tests\test_reports.py -vv

:: Backend suite, then the Playwright end-to-end suite
run_tests.bat -E2E
```
