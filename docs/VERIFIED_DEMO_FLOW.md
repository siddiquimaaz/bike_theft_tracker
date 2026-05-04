# Bike Theft Tracker — Verified End-to-End Demo Flow (As Built)

This is the current source-of-truth demo flow based on backend implementation.

---

## 0) Before You Start

Use one of these setup paths:

- Fixed single demo accounts:
  - `python manage.py create_demo_users`
- Full dataset with many records:
  - `python manage.py seed_demo_data`

Important seed note:

- Seeded reports use legacy statuses (`stolen`, `recovered`) for backward compatibility.
- For a clean modern lifecycle demo, create one fresh report manually after seeding so you can show:
  - `new_case -> under_review -> active_investigation -> bike_located -> pending_verification -> recovered -> closed`

---

## 1) Demo Users

### 1.1 `create_demo_users` (fixed accounts)

| Role | Email | Password |
|---|---|---|
| Admin | `admin@demo.btt` | `DemoAdmin@2024` |
| Authority (Karachi) | `authority.karachi@demo.btt` | `Authority@2024` |
| Owner | `owner000@demo.btt` | `Owner@2024` |
| Community | `community@demo.btt` | `Community@2024` |

### 1.2 `seed_demo_data` (full dataset mode)

- Creates admin + two authority accounts (Karachi and Lahore), many owners, bikes, theft reports, and partial recoveries.
- Includes:
  - `admin@demo.btt / DemoAdmin@2024`
  - `authority.karachi@demo.btt / Authority@2024`
  - `authority.lahore@demo.btt / Authority@2024`
  - `owner000@demo.btt / Owner@2024`

---

## 2) Phase 1 — Auth and Role Gate

### 2.1 Register (if not using demo users)

- `POST /api/auth/register/`
- Allowed self-registration roles: `owner`, `community`.
- System generates `email_verification_token`.

### 2.2 Verify email

- `POST /api/auth/verify-email/{token}/`
- User becomes verified.
- Login and role-gated actions depend on verification checks.

### 2.3 Login

- `POST /api/auth/login/`
- Returns JWT (`access`, `refresh`) plus role in user payload.
- Frontend should drive route exposure by returned role.

### 2.4 Enforcement highlights

- Owner-protected flows use `IsOwner`:
  - `POST /api/bikes/`
  - `POST /api/reports/`
  - `PUT /api/reports/{id}/recovery/confirm/`
- If user is authenticated but unverified, permission message indicates email verification is required.

---

## 3) Phase 2 — Owner Case Flow

### 3.1 Owner registers bike

- `POST /api/bikes/`
- Core attributes include engine/chassis identifiers.
- Engine and chassis are treated as identity-grade fields and are not mutable through update serializer path.

### 3.2 Owner files theft report

- `POST /api/reports/`
- Default status is `new_case` (modern flow).
- Case timeline event is written (`report_filed`).
- Current notification behavior: owner receives in-app theft reported notification.

### 3.3 Authority/Admin advances case status

- `PUT /api/reports/{id}/status/`
- Uses state machine transition rules.
- Writes timeline event and sends status-change notification.
- Owner notifications fire on milestones: `bike_located`, `pending_verification`, and `recovered`.
- When status enters `pending_verification` (including authority-driven status update),
  owner notification is actionable and includes recovery confirmation CTA metadata.
- For full lifecycle demo, explicitly run these transitions in order:
  - `new_case -> under_review`
  - `under_review -> active_investigation`
  - `active_investigation -> bike_located`
- **Authority cannot set `closed`** — the view blocks it with HTTP 403. When
  a case reaches `pending_verification` or `recovered`, the authority CaseReportsPage
  shows an amber info banner: *"Awaiting owner confirmation — the bike owner must
  confirm receipt to close this case."*
- Only **the bike owner** (via `PUT /api/reports/{id}/recovery/confirm/`) or an
  **admin** (via the status endpoint) can transition a case to `closed`.

### 3.4 Authority logs recovery

- `POST /api/reports/{id}/recovery/`
- Exact backend guard allows recovery logging only when current report status is one of:
  - `under_investigation` (legacy)
  - `active_investigation`
  - `bike_located`
- Calls from statuses like `new_case` or `under_review` are rejected with `400`.
- Recovery logging is permitted when report is in `active_investigation`, `bike_located`, or `under_investigation` (legacy). It is blocked in earlier states.
- In the modern path, report moves to `pending_verification`.
- Owner receives recovery notification with explicit pickup/confirmation call-to-action.

### 3.5 Owner confirms recovery and closure

- **In-app (ReportsPage):** When authority logs a recovery, pending sightings of the
  owner's bike appear as an amber-bordered section at the top of the owner's ReportsPage
  — above the reports table — with three action buttons per sighting:
  ✅ *That's my bike* / ❌ *Not my bike* / 🤷 *Not sure*.
  Clicking a button calls `PUT /api/sightings/{id}/owner-confirm/` and the section
  auto-refreshes. This section only appears when there are pending sightings waiting for
  the owner's response (`is_about_my_bike=true`, `owner_confirmation_status='pending'`).
- **API closure:** `PUT /api/reports/{id}/recovery/confirm/`
- Owner confirms receipt; report transitions to `closed`.
- Contributor closure notifications are sent to relevant community contributors.
- **CTA surfaces:** owner can confirm from Notifications and from Owner Reports list/detail.

Important trigger detail:

- Contributor closure notifications are triggered by owner confirmation at `PUT /api/reports/{id}/recovery/confirm/` (not merely by intermediate status movement).

- Owner confirmation calls `transition_status(closed)` — audit semantics are now uniform with all other status transitions.

---

## 4) Phase 3 — Community Sighting Flow

### 4.1 Submit sighting

- `POST /api/sightings/`
- Any authenticated role can submit (`owner`, `community`, `authority`, `admin`).
- Fuzzy matching runs automatically against engine/chassis query values and stores:
  - `fuzzy_match_score`
  - possible `top_match_bike_id`

Critical API response caveat:

- Create endpoint uses `SightingCreateSerializer`.
- Do not assume create response includes full list-serializer fields like `top_match_info`.
- If your test/demo needs enriched match output, fetch via list/detail endpoint after create.

### 4.2 Confidence routing behavior

Notification service evaluates confidence and evidence context:

- High confidence + photo:
  - Owner handshake is sent.
  - Urgent authority alerts are sent.
- Medium confidence:
  - Owner handshake first.
  - Authority escalation follows owner confirmation or timeout escalation path.
- Very low/no confident match:
  - Sighter receives acknowledgement; no immediate urgent escalation.

### 4.3 Owner handshake response

- `PUT /api/sightings/{id}/owner-confirm/`
- Valid values: `yes`, `no`, `not_sure`.

Outcomes:

- `yes`:
  - Urgent authority escalation.
  - Timeline event for owner confirmation.
- `no`:
  - Sighting archived.
  - Sighter receives archive-result notification.
- `not_sure`:
  - Remains pending-like for timeout automation.
  - Auto-escalation can occur after deadline.

### 4.4 Authority handles queue

- `GET /api/sightings/` for authority/admin is prioritized by confidence.
- Authority can proceed with verification and downstream recovery workflow based on confirmed/escalated sightings.

### 4.5 Community same-city theft feed

- Community users now have a limited awareness feed:
  - `GET /api/reports/community-feed/`
- Feed is city-scoped to the logged-in community user's city and returns sanitized fields only
  (no owner PII, no full case internals).
- Access is role-restricted: non-community roles receive `403`.

---

## 5) Phase 4 — Timeouts and Escalations (Scheduled Commands)

### 5.1 `process_sighting_timeouts`

- Sends owner reminder nudge near response deadline.
- Auto-escalates expired pending/not_sure handshakes to authority.

### 5.2 `process_case_escalations`

- 48-hour inactivity:
  - Reminder to city authority.
- 7-day stale inactivity:
  - Escalation to admin users.

---

## 6) Phase 5 — Timeline and Notification Layer

### 6.1 CaseTimeline coverage

Timeline events are written across:

- report creation
- status transitions
- sighting submission and verification actions
- owner handshake responses
- recovery logging/amendments
- contributor closure notifications

### 6.2 Notification model behavior

- In-app notifications are primary and linked with report/sighting metadata.
- Email/SMS flows are available where configured, but in-app remains canonical for demo.

Known timeline caveat:

- Duplicate write path removed — `report_filed` is written once only.

---

## 7) Phase 6 — Admin Oversight and Closure Controls

- Admin oversight endpoints:
  - `GET /api/admin/analytics/`
  - `GET /api/admin/audit-logs/`
- Admin can move case status via report status endpoint where transitions allow, **including
  setting `closed`** — this is the admin override path for exceptional circumstances
  (e.g., owner is unreachable/unresponsive after the bike has been recovered).
- Authority cannot close a case — the `PUT /api/reports/{id}/status/` view blocks
  `status=closed` for authority users with HTTP 403. Admin is not restricted.
- Admin can trigger a full ML reanalysis (`POST /api/ml/trigger-reanalysis/`); this now
  runs synchronously and returns HTTP 200 only after all caches are written.
- Audit and timeline records provide operational traceability.

---

## 8) Known Breakage Risks to Call Out During Demo

| Risk | Where | Impact |
|---|---|---|
| Seed lifecycle mismatch | seeded data includes legacy statuses | Seed-only demos can miss modern lifecycle stages |
| Test DB teardown lock warning | parallel DB sessions during pytest teardown on local machine | Harmless warning, but can distract during automated demo checks |

Resolved in current build:

- City-scoped authority enforcement is applied in `verify_sighting` (regression-tested).
- Owner notification noise reduced to milestone statuses.
- Duplicate `report_filed` timeline write removed.
- Recovery confirm now closes through `transition_status`.
- Owner handshake route is guarded by `IsOwner` (regression-tested).
- **Authority cannot close cases directly** — `PUT /api/reports/{id}/status/` returns
  HTTP 403 for authority users when `status=closed`; only owner confirm or admin override
  can close (regression-tested: `test_authority_cannot_close_case_directly`,
  `test_admin_can_close_case_directly`).
- **Owner sighting CTA** — ReportsPage now shows pending sightings of the owner's bike
  with ✅ / ❌ / 🤷 response buttons; backend `GET /api/sightings/` expanded to include
  sightings of owner's bike (`is_about_my_bike` flag added).
- **ML trigger is now synchronous** — `trigger_reanalysis` writes all caches before
  returning 200; dashboards refetch immediately after trigger (no stale 202 state).
- **Password reset** uses `new_password` + `confirm_password` fields (frontend fixed to
  match the `PasswordResetConfirmSerializer` contract).

---

## 9) Presenter Demo Script (Role-Switch Run)

Use this sequence for a stable live demo in 10-15 minutes.

1. Setup mode:
   - Run `create_demo_users` for clean fixed accounts, or `seed_demo_data` for rich data.
2. Login as Owner (`owner000@demo.btt`):
   - Register a bike (if fresh DB).
3. Owner files theft report:
   - Confirm status starts at `new_case`.
4. Login as Community (`community@demo.btt`):
   - Submit a sighting with partial identifier and (ideally) photo.
5. Return to Owner:
   - Open handshake notification and respond (`yes` for escalation path).
   - Alternatively: navigate to **My Reports** — a pending sighting of the owner's
     bike appears in an amber-bordered section above the reports table. Click
     ✅ *That's my bike* to confirm (or ❌ / 🤷 for other paths).
6. Login as Authority (`authority.karachi@demo.btt`):
   - Open sightings/reports queue.
   - Advance report statuses explicitly:
     - `new_case -> under_review`
     - `under_review -> active_investigation`
     - `active_investigation -> bike_located`
7. Authority logs recovery:
   - Case moves to `pending_verification`.
   - Note: after this point, the authority UI shows an amber banner:
     *"Awaiting owner confirmation"* — they cannot advance further.
8. Back to Owner:
   - Open recovery notification/request from notifications screen, **or** go to
     **My Reports** where the pending sighting card reappears.
   - Confirm recovery via `/recovery/confirm/`.
   - Case closes (closure notification to contributors is triggered here).
9. Back to Community:
   - Show contributor closure notification.
10. Login as Admin:
    - Show analytics and audit logs for oversight view.
    - (Optional) demonstrate admin close override: if owner is unresponsive, admin
      can set `status=closed` directly via `PUT /api/reports/{id}/status/`.

If using `seed_demo_data`:

- Create one fresh owner report before steps 3-8 to guarantee modern lifecycle demonstration.

---

## 10) Quick Verification Checklist

- Auth works for all four roles.
- Owner-only endpoints enforce verification and role.
- Community user remains blocked from full theft reports API (`/api/reports/`) but can access limited same-city feed (`/api/reports/community-feed/`).
- A fresh report follows modern status lifecycle.
- Demo explicitly exercises `under_review`, `active_investigation`, and `bike_located` before recovery.
- Sighting handshake and escalation behavior is observable.
- Recovery confirm closes case and triggers contributor closure notifications.
- Admin visibility into analytics/audit is available.
- 381 tests passing (backend pytest suite, ≥90% coverage gate, 90.78% actual).

---

## 11) Common 400s During Demo (Quick Recovery)

| Endpoint | Likely cause | Quick fix |
|---|---|---|
| `POST /api/reports/{id}/recovery/` | Report status is not allowed for recovery logging | Move case to `active_investigation` or `bike_located` first, then retry |
| `PUT /api/reports/{id}/status/` | Invalid transition for current status | Check current status and apply only the next valid transition in sequence |
| `PUT /api/reports/{id}/status/` **(403)** | Authority officer attempting to set `status=closed` | Authority cannot close cases — wait for owner to confirm receipt, or ask admin to override |
| `PUT /api/reports/{id}/recovery/confirm/` | Case is not in `pending_verification` or `recovered` | Ensure Authority logged recovery first and case moved to `pending_verification` |
| `PUT /api/sightings/{id}/owner-confirm/` | Requesting user is not the matched bike owner | Login as the actual owner of `top_match_bike` before confirming |
| `PUT /api/sightings/{id}/owner-confirm/` | Caller is not owner role (`IsOwner` guard) | Use verified owner account; authority/community/admin are rejected |
| `PUT /api/sightings/{id}/owner-confirm/` | Invalid `response` value | Use only `yes`, `no`, or `not_sure` |
| `POST /api/auth/password-reset/confirm/` | Wrong field names | Use `new_password` + `confirm_password` (not `password`) |
| `POST /api/auth/verify-email/{token}/` | Token expired, invalid, or already used | Re-register/reissue token and verify again within validity window |
| `POST /api/bikes/` | Owner account not verified yet | Complete email verification, re-login, then retry |

