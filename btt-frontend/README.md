# Bike Theft Tracker — Frontend

React + Vite + Tailwind CSS frontend for the BTT REST API backend.

**Group 58 | Batch 2022F | BS Computer Science | SSUET, Karachi**

For full system reset/start instructions across backend + DB + frontend, see `..\RESET_RUNBOOK.md`.

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 18 + Vite 5 |
| Routing | React Router v6 |
| HTTP | Axios (with silent token refresh) |
| Styling | Tailwind CSS v3 + custom design system |
| State | Context API (AuthContext + RoleContext) |

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Copy env template
cp .env.example .env
# Edit .env if your backend runs on a port other than 8000

# 3. Start the backend first (see GUIDE.md)

# 4. Start the frontend
npm run dev
# → http://localhost:3000
```

> **CORS note**: The Vite dev proxy (`/api → http://localhost:8000`) means you
> do NOT need to configure CORS in Django during development. For production,
> set `CORS_ALLOWED_ORIGINS` in Django settings.

## Folder Structure

```
src/
├── api/            # Axios instance + one file per API domain
├── context/        # AuthContext (JWT) + RoleContext (permissions)
├── layouts/        # MainLayout (auth pages) + DashboardLayout (sidebar)
├── routes/         # AppRoutes + ProtectedRoute + RoleRoute guards
├── pages/          # auth/ owner/ authority/ admin/ community/ shared/
├── components/
│   ├── UI/         # Button, Badge, Modal, Alert, Spinner, StatCard, EmptyState
│   ├── forms/      # BikeForm, ReportForm, SightingForm
│   ├── tables/     # DataTable (generic)
│   └── cards/      # BikeCard, NotificationItem
├── hooks/          # useFetch, useAuth, useNotifications
└── utils/          # constants.js, formatters.js, jwt.js
```

## Auth Flow

1. User submits login form → `POST /api/auth/login/`
2. Backend returns `{ access, refresh, user? }`
3. Tokens saved to `localStorage` via `utils/jwt.storage`
4. JWT decoded to extract `role` (owner / community / authority / admin)
5. User redirected to role-specific dashboard
6. Axios interceptor auto-refreshes the access token on 401

## Role Routing

| Role | Home |
|------|------|
| owner | `/owner/dashboard` |
| community | `/community/dashboard` |
| authority | `/authority/dashboard` |
| admin | `/admin/dashboard` |

## End-to-End Tests (Playwright)

Per-role smoke specs live under `e2e/` (`auth.spec.js`, `owner.spec.js`,
`authority.spec.js`, `admin.spec.js`, `community.spec.js`,
`api-connectivity.spec.js`). Run them with `npx playwright test` once the
backend (port 8000) and frontend (port 3000) are both up and demo users
have been seeded (`python manage.py create_demo_users`).

A separate **full demo-narrative** spec at
`tests/e2e/demo_narrative.spec.js` exercises all six cross-role events in
order (owner reports → community sights → owner handshake → authority
escalation → recovery → owner pickup confirmation → community closure
broadcast). It mirrors the backend
`tests/test_inter_role_sync.py::TestEndToEndDemoNarrative` integration
test and is intended as an opt-in pre-presentation rehearsal — run it
explicitly with:

```bash
npx playwright test tests/e2e/demo_narrative.spec.js
```

## Phase 4 Enhancements (Not Yet Implemented)

- **Map view** — install `react-leaflet` and render hotspot cluster coordinates
- **Real-time notifications** — WebSocket connection to Django Channels
- **File upload preview** — bike photo upload with preview in BikeForm
- **Charts** — install `recharts` and visualise monthly trend data in AnalyticsPage
