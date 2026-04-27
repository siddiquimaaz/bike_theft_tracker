# Bike Theft Tracker — User Stories & Role Verification

**Group 58 | Batch 2022F | BS Computer Science | SSUET, Karachi**

This document defines how each role interacts with the system, maps every
action to the backing test case, and describes the full six-event inter-role
sync flow that ties all roles together.

---

## Table of Contents

1. [System Roles Overview](#1-system-roles-overview)
2. [Role: Admin](#2-role-admin)
3. [Role: Authority](#3-role-authority)
4. [Role: Owner (Bike Owner)](#4-role-owner-bike-owner)
5. [Role: Community Reporter](#5-role-community-reporter)
6. [Inter-Role Sync — Full Demo Narrative](#6-inter-role-sync--full-demo-narrative)
7. [Test Coverage Summary](#7-test-coverage-summary)
8. [Notification Matrix](#8-notification-matrix)

---

## 1. System Roles Overview

| Role | How Created | Self-Register? | Purpose |
|---|---|---|---|
| **Admin** | `createsuperuser` or `seed_demo_data` | No | System oversight, user management, analytics |
| **Authority** | Admin creates via API/dashboard | No | Investigates cases, logs recoveries, verifies sightings |
| **Owner** | Self-register + email verify | Yes | Registers bikes, files theft reports, confirms recovery |
| **Community** | Self-register + email verify | Yes | Submits sightings of suspected stolen bikes |

**Demo credentials (after `python manage.py create_demo_users`):**

| Role | Email | Password |
|---|---|---|
| Admin | admin@demo.btt | DemoAdmin@2024 |
| Authority (Karachi) | authority.karachi@demo.btt | Authority@2024 |
| Authority (Lahore) | authority.lahore@demo.btt | Authority@2024 |
| Owner | owner000@demo.btt | Owner@2024 |
| Community | community000@demo.btt | Community@2024 |

---

## 2. Role: Admin

### Who they are
The system super-user. Created once via `python manage.py createsuperuser`.
Responsible for onboarding authority officers, monitoring the platform, and
viewing forensic audit trails.

### User Stories

---

**US-A1 — View and filter all users**
> *As an Admin, I want to see every registered user and filter by role,
> activation status, or verification status so I can monitor the user base.*

- `GET /api/admin/users/` returns all users.
- Query params: `?role=owner`, `?is_active=true`, `?is_verified=false`.
- **Tests:** `test_admin_can_list_users`, `test_filter_by_role`,
  `test_filter_by_is_active`, `test_filter_by_is_verified`,
  `test_owner_cannot_list_users`, `test_authority_cannot_list_users`,
  `test_unauthenticated_rejected`

---

**US-A2 — Create an Authority account**
> *As an Admin, I want to create verified Authority accounts for police officers
> so they can start managing cases immediately without going through the public
> registration flow.*

- `POST /api/admin/users/authority/` with `{email, full_name, badge_number, city, password}`.
- Account is created already verified — authority can log in immediately.
- Self-registration for `role: authority` is blocked at `/api/auth/register/`.
- **Tests:** `test_admin_can_create_authority`, `test_owner_cannot_create_authority`,
  `test_authority_self_registration_rejected`

---

**US-A3 — Activate / deactivate / delete users**
> *As an Admin, I want to deactivate a user who is abusing the platform and
> reactivate them if appropriate.*

- `PUT /api/admin/users/{id}/status/` with `{is_active: false}`.
- Deactivated users cannot log in (login endpoint returns 401).
- **Tests:** `test_admin_can_deactivate_user`, `test_admin_can_reactivate_user`,
  `test_inactive_user_rejected`, `test_admin_can_delete_authority_user`,
  `test_owner_cannot_update_status`

---

**US-A4 — View analytics dashboard**
> *As an Admin, I want to see KPI stats (total reports, active cases, recovery
> rate, top theft cities) so I can assess platform health.*

- `GET /api/admin/analytics/` — returns aggregated KPI data.
- Only Admin can access; Authority and Owner are blocked.
- **Tests:** `test_admin_can_get_analytics`, `test_admin_analytics_with_no_data`,
  `test_authority_cannot_access_analytics`, `test_owner_cannot_access_analytics`

---

**US-A5 — View immutable audit log**
> *As an Admin, I want to see a forensic trail of every sensitive action
> (status changes, logins, deletions) so I can investigate misuse.*

- `GET /api/admin/audit-logs/` — append-only log (DB-level REVOKE enforces this).
- Only Admin can read; Owner returns 403.
- **Tests:** `test_admin_can_list_audit_logs`, `test_owner_cannot_access_audit_logs`

---

**US-A6 — Soft-delete a report**
> *As an Admin, I want to soft-delete a fraudulent report so it is hidden from
> users but preserved for audit purposes.*

- `DELETE /api/reports/{id}/` — sets `deleted_at`, does not remove the row.
- **Tests:** `test_admin_soft_delete_object_still_exists_with_deleted_at`

---

## 3. Role: Authority

### Who they are
A verified police officer or investigator assigned to a specific city. Created
by Admin. Manages the entire case lifecycle from intake to recovery.

### User Stories

---

**US-AU1 — View all theft reports in my city**
> *As an Authority officer in Karachi, I want to see all theft reports filed
> for Karachi so I can manage my caseload.*

- `GET /api/reports/` returns only reports matching the officer's city.
- A Lahore officer cannot see Karachi reports and vice versa.
- **Tests:** `test_authority_sees_city_reports`,
  `test_lahore_authority_cannot_see_karachi_report`

---

**US-AU2 — Advance a case through the status lifecycle**
> *As an Authority, I want to move a case from `new_case` through the
> investigation pipeline to `bike_located` so the system reflects real progress.*

Status machine (authority-reachable transitions shown with →; owner/admin-only shown with ⇒):
```
new_case → under_review → active_investigation → bike_located
                                                     ↓ (log recovery)
                                           pending_verification
                                                     ↓
                                                 recovered
                                                     ↓
                                     ⇒ closed  (owner confirm OR admin override only)
```

- `PUT /api/reports/{id}/status/` with `{status: "under_review"}`.
- Invalid transitions (e.g., skipping steps) return 400.
- Only the officer assigned to that city can transition; cross-city returns 403/404.
- **Authority cannot set `closed`** — doing so returns HTTP 403 with an error message
  directing them to the owner-confirmation flow. Only the bike owner (via
  `PUT /api/reports/{id}/recovery/confirm/`) or an admin can close a case.
- **Tests:** `test_authority_transitions_new_case_to_under_review`,
  `test_authority_chains_under_review_to_active_investigation`,
  `test_invalid_status_transition_rejected`,
  `test_lahore_authority_gets_404_transitioning_karachi_report`,
  `test_owner_cannot_change_report_status`,
  `test_regression_under_review_to_new_case_returns_400`,
  `test_any_transition_on_closed_case_returns_400`,
  `test_authority_cannot_close_case_directly`,
  `test_admin_can_close_case_directly`

---

**US-AU3 — Log a recovery record**
> *As an Authority, once I locate the bike I want to log where and when it was
> recovered and its condition.*

- `POST /api/reports/{id}/recovery/` with `{recovery_date, recovery_city, bike_condition}`.
- Only allowed when report is `active_investigation` or `bike_located`.
- Owner can view recovery details; Community cannot.
- **Tests:** `test_authority_can_log_recovery`, `test_duplicate_recovery_rejected`,
  `test_recovery_rejected_when_report_not_under_investigation`,
  `test_authority_logs_recovery_owner_can_get_recovery_date`,
  `test_community_cannot_get_recovery_record`

---

**US-AU4 — Receive URGENT notification when owner confirms sighting**
> *As an Authority, I want to be alerted immediately when a bike owner confirms
> that a community sighting matches their stolen bike.*

- When owner responds `yes` to a handshake, an `URGENT` notification fires to
  the authority in that sighting's city.
- Also fires immediately (without waiting for owner) when sighting score ≥ 85
  and a photo is present (high-confidence routing).
- **Tests:** `test_confidence_routing_high`, `test_owner_responds_yes_sets_confirmation_status`,
  `test_authority_verifies_sighting_owner_gets_notification`,
  `test_high_confidence_sighting_alerts_authority_with_high_confidence_message`,
  `test_notify_status_changed_on_bike_located_notifies_owner`

---

**US-AU5 — Verify a sighting and link it to a bike**
> *As an Authority, I want to formally verify a community sighting and link it
> to a specific stolen bike in the system.*

- `POST /api/sightings/{id}/verify/` with `{bike_id: N}`.
- Only Authority in the same city as the sighting can verify.
- Owner and Community cannot call this endpoint.
- **Tests:** `test_authority_verifies_sighting_owner_gets_notification`,
  `test_owner_cannot_verify_sighting`, `test_community_cannot_verify_sighting`,
  `test_karachi_authority_cannot_verify_lahore_sighting`,
  `test_karachi_authority_can_verify_karachi_sighting`

---

**US-AU6 — View ML hotspots and trends**
> *As an Authority, I want to see theft hotspot clusters and monthly trends for
> my city so I can deploy resources effectively.*

- `GET /api/ml/hotspots/?city=Karachi` — DBSCAN cluster data.
- `GET /api/ml/trends/` — monthly theft/recovery trend analytics.
- `GET /api/ml/fuzzy-match/?engine=ENG123` — search by partial engine number.
- **Tests covered in:** `tests/test_ml.py`

---

## 4. Role: Owner (Bike Owner)

### Who they are
A registered bike owner. Self-registers with CNIC, email, city. Must verify
email before logging in. Registers their bikes and is the primary case owner
for any theft report.

### User Stories

---

**US-O1 — Register an account**
> *As a bike owner, I want to create an account so I can register my bikes.*

- `POST /api/auth/register/` with `{full_name, email, cnic, role: "owner", city, password}`.
- System sends a verification email (console in dev — printed to terminal).
- Duplicate email and invalid CNIC are rejected immediately.
- Inline availability checks: `GET /api/auth/check-email/` and
  `GET /api/auth/check-cnic/` fire onBlur on the register form.
- **Tests:** `test_owner_registration_success`, `test_duplicate_email_rejected`,
  `test_invalid_cnic_rejected`, `test_blank_cnic_phone_normalized_for_registration`,
  `test_registration_returns_verification_link_in_local_dev_mode`

---

**US-O2 — Verify email and log in**
> *As a new owner, I want to verify my email and then log in to access my
> dashboard.*

- `GET /api/auth/verify-email/{token}/` — activates the account.
- Expired (>24 h) or already-used tokens are rejected.
- Login is blocked for unverified accounts.
- **Tests:** `test_valid_token_verifies_user`, `test_invalid_token_rejected`,
  `test_expired_token_rejected`, `test_valid_credentials_return_tokens`

---

**US-O3 — Register a bike**
> *As an owner, I want to register my bike with its engine number, chassis
> number, make, model, and city so the system can match it against future
> sightings.*

- `POST /api/bikes/` — creates the bike linked to this owner.
- Engine/chassis numbers are normalised to uppercase.
- Duplicate engine number is rejected.
- Only Owner role can register bikes; Authority is blocked.
- **Tests:** `test_owner_can_register_bike`, `test_engine_number_normalized_to_uppercase`,
  `test_non_owner_cannot_register_bike`, `test_duplicate_engine_number_rejected`,
  `test_owner_sees_only_own_bikes`

---

**US-O4 — File a theft report**
> *As an owner, I want to file a theft report for my stolen bike with the date,
> city, and location detail so it enters the investigation queue.*

- **Two entry points:**
  1. **My Bikes page** — each non-stolen bike card shows a 🚨 **Report Stolen**
     button. Clicking it opens the report form pre-filled with that bike so the
     owner never has to select it manually from a dropdown.
  2. **My Reports page** — the **+ File Report** button opens the same form
     with an empty bike selector (useful if navigating from the reports tab).
- `POST /api/reports/` with `{bike, theft_date, theft_city, description}`.
- Future theft dates are rejected.
- Can only file against own bikes; another owner's bike returns 403.
- Duplicate reports (same bike, open status) are rejected.
- After filing, the bike card status badge switches from `Active` to `Stolen`
  and the 🚨 button disappears (already reported).
- **Tests:** `test_owner_can_file_report`, `test_future_theft_date_rejected`,
  `test_cannot_report_other_owners_bike`, `test_cannot_file_duplicate_report`,
  `test_stolen_bike_flagged`, `test_no_owner_data_in_public_search`

---

**US-O5 — Track my report status**
> *As an owner, I want to see the current status of my report so I know if
> police are investigating.*

- `GET /api/reports/` returns only this owner's reports.
- Owner cannot see another owner's reports.
- Owner can see the report detail but cannot change the status.
- Owner receives a notification when status moves to `bike_located`.
- **Tests:** `test_owner_sees_own_reports`, `test_owner_sees_updated_status_after_authority_transition`,
  `test_owner_cannot_see_another_owners_report`, `test_owner_cannot_change_report_status`,
  `test_notify_status_changed_on_bike_located_notifies_owner`

---

**US-O6 — Respond to a sighting handshake**
> *As an owner, I receive a notification asking "Is this your bike?" when a
> community sighting matches my bike. I respond yes, no, or not sure.*

- `PUT /api/sightings/{id}/owner-confirm/` with `{response: "yes"}`.
- `yes` → URGENT notification fires to Authority; sighting is linked.
- `no` → sighting is archived; no escalation.
- `not_sure` → sighting stays open for auto-escalation after deadline.
- Only the matched bike's owner can respond; cross-owner and Authority are blocked.
- Double confirmation returns 400.
- **UI (ReportsPage):** Pending sightings of the owner's bike appear as an amber-bordered
  section above the reports table with three action buttons per sighting:
  ✅ *That's my bike* / ❌ *Not my bike* / 🤷 *Not sure*. The section is hidden when
  there are no pending sightings. The backend `GET /api/sightings/` now returns both
  sightings submitted *by* the owner and sightings *of* their bike pending confirmation
  (flagged `is_about_my_bike: true`).
- **Tests:** `test_owner_responds_yes_sets_confirmation_status`,
  `test_owner_responds_no_archives_sighting`,
  `test_owner_handshake_not_sure`,
  `test_owner_cannot_confirm_sighting_for_another_owners_bike`,
  `test_authority_cannot_confirm_sighting_on_behalf_of_owner`,
  `test_double_confirmation_second_call_returns_400`,
  `test_invalid_response_value_returns_400`

---

**US-O7 — Confirm bike pickup and close the case**
> *As an owner, once police notify me the bike has been recovered, I want to
> confirm I picked it up so the case officially closes.*

- `PUT /api/reports/{id}/recovery/confirm/` — transitions case to `closed`.
- Sets `owner_recovery_confirmed = True` and timestamps the event.
- Triggers a thank-you `COMMUNITY_CLOSURE` notification to all community
  sighters who contributed to this case.
- Another owner, Authority, or Community cannot call this endpoint.
- **Admin fallback:** if the owner is unresponsive, an admin can close the case
  via `PUT /api/reports/{id}/status/` with `{status: "closed"}`. Authority
  cannot do this — the 403 guard is authority-specific, not admin-specific.
- **Tests:** `test_owner_confirm_recovery_closes_case`,
  `test_owner_confirm_recovery_updates_transition_audit_fields`,
  `test_owner_confirms_recovery_case_becomes_closed`,
  `test_owner_cannot_confirm_recovery_for_another_owners_report`,
  `test_authority_cannot_call_recovery_confirm`,
  `test_recovery_confirm_on_closed_report_returns_400`

---

**US-O8 — View notifications**
> *As an owner, I want to see all my notifications and mark them read.*

- `GET /api/notifications/` — returns this owner's notifications only.
- `PUT /api/notifications/{id}/read/` — marks one read.
- `PUT /api/notifications/read-all/` — marks all read.
- Owner cannot see another role's notifications.
- **Tests:** `test_owner_can_list_notifications`,
  `test_owner_cannot_see_other_roles_notifications_in_api`

---

## 5. Role: Community Reporter

### Who they are
Any registered citizen who spots what looks like a stolen bike. Self-registers
(no CNIC required for community role). Contributes intelligence by submitting
sightings with partial identifying information.

### User Stories

---

**US-C1 — Register an account**
> *As a community member, I want to register without providing my CNIC so I
> can report suspicious bikes.*

- `POST /api/auth/register/` with `{role: "community"}` — CNIC is optional.
- Same email verification flow as Owner.
- **Tests:** `test_community_registration_no_cnic`

---

**US-C2 — Submit a sighting**
> *As a community member, I want to report a suspicious bike I saw by entering
> partial engine/chassis numbers and location so police can investigate.*

- `POST /api/sightings/` with partial identifiers, date, city, optional photo.
- System immediately runs a RapidFuzz WRatio fuzzy match against all stolen bikes.
- **Confidence routing:**
  - Score ≥ 85 + photo → Owner gets handshake **AND** Authority gets immediate URGENT.
  - Score ≥ 70 (no photo, or score < 85) → Owner gets handshake only; Authority waits.
  - Score < 70 → System receipt only; no escalation.
- Sighter always receives a system receipt notification confirming submission.
- **Tests:** `test_confidence_routing_high`, `test_confidence_routing_low`,
  `test_sighter_always_gets_system_receipt_notification`,
  `test_high_confidence_sighting_alerts_authority_with_high_confidence_message`,
  `test_low_confidence_sighting_no_sighting_matched_for_owner`

---

**US-C3 — View only my own sightings**
> *As a community member, I want to track the sightings I have submitted and
> see their status.*

- `GET /api/sightings/` returns only this user's own sightings.
- Community cannot see other users' sighting details.
- Community cannot access theft report data (`/api/reports/`).
- **Tests:** `test_community_sees_only_own_sightings`,
  `test_community_gets_404_on_another_users_sighting_detail`,
  `test_community_cannot_list_reports`, `test_community_cannot_view_report_detail`,
  `test_community_cannot_post_report`

---

**US-C4 — Receive a thank-you when a case closes**
> *As a community reporter, I want to be notified when a case I helped solve
> is successfully closed so I know my contribution mattered.*

- When an Owner confirms pickup (`recovery/confirm/`), a `COMMUNITY_CLOSURE`
  notification is broadcast to every community user who submitted a sighting
  that was linked to that case.
- Owner and Authority do **not** receive this notification type.
- **Tests:** `test_contributor_closure_notification`,
  `test_case_closure_notifies_community_contributors`

---

**US-C5 — Access restrictions are enforced**
> *As a community member, I should not be able to access theft reports, verify
> sightings, log recoveries, or view admin data.*

- Reports list: 200 with empty queryset (no data leaked).
- Recovery endpoint: 404.
- Sighting verify endpoint: 403.
- Admin endpoints: 403.
- **Tests:** `test_community_cannot_list_reports`,
  `test_community_cannot_post_report`, `test_community_gets_404_on_recovery_get`,
  `test_community_cannot_verify_sighting`, `test_community_cannot_call_owner_confirm`

---

## 6. Inter-Role Sync — Full Demo Narrative

This is the six-event flow that exercises every role in sequence.
Fully verified by `tests/test_inter_role_sync.py::test_full_demo_scenario_runs_end_to_end`
and mirrored by the Playwright spec at `btt-frontend/tests/e2e/demo_narrative.spec.js`.

```
Event 1 ─── Owner registers bike + files theft report
    │            Notification: THEFT_REPORTED → Owner
    │
Event 2 ─── Community submits sighting (high confidence + photo)
    │            Fuzzy match score ≥ 85 + photo detected
    │            Notification: SIGHTING_OWNER_HANDSHAKE → Owner
    │            Notification: URGENT → Authority (immediate, high-confidence path)
    │
Event 3 ─── Owner receives handshake, responds "Yes"
    │            Notification: URGENT escalation confirmed → Authority
    │            Notification: SIGHTING_OWNER_RESPONSE receipt → Owner
    │            CaseTimeline: owner_confirmed_sighting
    │
Event 4 ─── Authority sees URGENT notification
    │            Advances case: active_investigation → bike_located
    │            CaseTimeline: status_changed
    │
Event 5 ─── Authority logs recovery record
    │            Case moves to pending_verification
    │            Notification: RECOVERY → Owner ("Your bike has been found")
    │
Event 6 ─── Owner confirms pickup
                 PUT /api/reports/{id}/recovery/confirm/
                 Case → closed, owner_recovery_confirmed = True
                 Notification: COMMUNITY_CLOSURE → community sighter
                 CaseTimeline: owner_confirmed_recovery_receipt, contributors_notified
```

**Alternate paths also tested:**
- Owner responds `not_sure` → sighting stays open, timeline records it.
- Owner misses deadline → `auto_escalate_pending_owner_responses()` escalates automatically.
- Owner responds `no` → sighting archived, no escalation.
- City isolation: Lahore Authority cannot touch Karachi cases.
- Privacy: public search shows stolen status but never reveals owner's email or name.

---

## 7. Test Coverage Summary

| Test File | Tests | What It Covers |
|---|---|---|
| `test_auth.py` | 17 | Registration, email verify, login, logout, inactive blocking |
| `test_auth_extended.py` | 15 | Password reset, token refresh, edge cases |
| `test_bikes.py` | 17 | Bike register, update, soft-delete, public search, stolen flag |
| `test_reports.py` | 20 | File report, status transitions, recovery, role scoping |
| `test_reports_extended.py` | 20 | Recovery confirm, owner transitions, city isolation edge cases |
| `test_sightings.py` | 30 | Submit sighting, fuzzy match, verify, role guards |
| `test_sighting_handshake.py` | 4 | Handshake yes/no/not_sure, deadline auto-escalation |
| `test_enhanced_flows.py` | 9 | Confidence routing, owner handshake, closure broadcast, timeline |
| `test_notifications.py` | 36 | All notification types, read/unread, cross-role isolation |
| `test_admin.py` | 25 | User CRUD, analytics, audit log, RBAC enforcement |
| `test_ml.py` | 33 | Fuzzy match accuracy, hotspot API, trends, recovery zones |
| `test_inter_role_sync.py` | 67 | Cross-role data isolation, full lifecycle, full demo narrative |
| `test_case_timeline.py` | 1 | Timeline audit trail |
| `test_coverage_boost.py` | 10 | Edge cases and serializer branches |
| `test_security.py` | 22 | Auth hardening, throttle, RBAC exhaustive |
| `test_bike_serializers_extra.py` | 2 | Serializer edge cases |
| `test_fuzzy_match.py` | 15 | WRatio scoring accuracy at various thresholds |
| `test_theft_alert_notifications.py` | 16 | City-scoped theft alert fan-out (owner/authority/community) |
| `test_ml_corridors.py` | 21 | Recovery radius + corridor analysis endpoints + unit tests |
| **Total** | **380** | **≥90% coverage — threshold met ✅** |

---

## 8. Notification Matrix

Which role receives which notification, and when:

| Event | Owner | Authority (same city) | Community (same city) | Admin |
|---|---|---|---|---|
| Theft report filed | ✅ THEFT_REPORTED | ✅ THEFT_REPORTED (new case alert) | ✅ SYSTEM (public awareness, no PII) | — |
| Status → `bike_located` | ✅ STATUS_UPDATE | — | — | — |
| Recovery logged | ✅ RECOVERY | — | — | — |
| Sighting matched (owner alert) | ✅ SIGHTING_OWNER_HANDSHAKE | — | — | — |
| High-confidence sighting (≥85 + photo) | ✅ SIGHTING_OWNER_HANDSHAKE | ✅ URGENT | — | — |
| Owner confirms sighting (`yes`) | ✅ SIGHTING_OWNER_RESPONSE | ✅ URGENT | — | — |
| Owner responds `not_sure` | ✅ SIGHTING_OWNER_RESPONSE | — | — | — |
| Owner missed deadline (auto-escalate) | — | ✅ URGENT | — | — |
| Sighting submitted (receipt) | — | — | ✅ SYSTEM | — |
| Case closed (owner confirmed pickup) | — | — | ✅ COMMUNITY_CLOSURE | — |
