# Diagram Generation Brief — Bike Theft Tracker (BTT)

Standalone context package for generating the figures used in [docs/TRD.md](TRD.md). No codebase access required — everything needed is below. The figure numbering matches the List of Figures convention used in the MuseAI reference document this TRD is modeled on (chapter-prefixed: `Figure <chapter>.<n>`), so BTT's own List of Figures should read the same way once these are produced:

```
Figure 4.1: System Architecture Diagram
Figure 4.2: UML Sequence Diagram (Theft-to-Recovery Case Flow)
Figure 4.3: UML Use Case Diagram
Figure 4.4: UML Class Diagram
Figure 4.5: Database Diagram (ER Diagram)
Figure 4.6: Interface Wireframes
Figure 5.1: Business Model Canvas
Figure 6.1: Software Development Cycle
Figure 6.2: Project Plan with Gantt Chart
Figure 7.1: Software Testing Life Cycle
Figure 7.2: Bug Life Cycle
```

Six of these (4.1–4.5, plus an earlier flat-numbered GUI flowchart being retired in favor of 4.6's wireframes — see §4.6) already exist as Mermaid source in `docs/diagrams/*.mmd`, rendered to matching `.png` files. Sections 1–3 below are shared background; sections 4–7 are per-figure briefs, one per entry in the list above.

## 1. Project summary

Bike Theft Tracker (BTT) is a web platform for reporting, tracking, and recovering stolen motorcycles in Karachi, Pakistan. Four roles share one case record instead of keeping separate paper trails: an **Owner** registers a bike and files a theft report; a **Community** member who spots a suspicious bike submits a sighting against a partial engine/chassis number; a police **Authority** account investigates the case through a structured workflow; an **Admin** manages users and sees system-wide analytics and the audit log. The system automatically fuzzy-matches partial identifiers, computes geospatial theft-hotspot and recovery-corridor analytics, and routes notifications by city.

**Stack:** Django 6.0.8 + Django REST Framework 3.17.1 backend, PostgreSQL 15 + PostGIS for spatial data, React 19.2.8 + Vite 8 frontend, JWT auth (`djangorestframework-simplejwt`), rapidfuzz for fuzzy matching, scikit-learn (DBSCAN) + pandas for analytics.

## 2. Roles and permissions

| Role | Can do |
|---|---|
| **Owner** | Register/login, register bikes, file theft reports on owned bikes, respond to sighting-match handshake (yes/no/not sure), confirm final bike receipt to close a case, view own reports and case timeline, receive notifications |
| **Community** | Register/login, submit sightings (partial identifier + optional photo), view own submitted sightings, receive notifications, get thanked when a case they contributed to closes |
| **Authority** | Login (provisioned by admin, not self-registered — requires a unique badge number), view a city-scoped case queue, verify sightings, advance case status (within a restricted whitelist — see §3), log recoveries with evidence photos, view city-scoped analytics dashboards |
| **Admin** | Login, manage all user accounts, view global (non-city-scoped) analytics, view the immutable audit log, override any case-status transition |

Scoping note: Authority and Community actions are **city-scoped** — an Authority account only sees/acts on cases in their own city; a theft report notifies Community accounts in the *same* city as the theft, not nationally.

## 3. Core entities, state machine, and case flow

Shared reference for Figures 4.2, 4.3, 4.4, 4.5, and 7.2.

### Entities and relationships (physical schema)

- **User** — hub entity. Fields: id, full_name, email, role (owner/authority/community/admin), city, badge_number (authority only, unique), cnic, is_verified, deleted_at (soft delete).
- **Bike** — id, owner (FK → User), engine_number (unique), chassis_number (unique), plate_number, make, model, year, color, city. Computed: is_stolen (derived from whether an active TheftReport exists).
- **TheftReport** — id, bike (FK → Bike), reported_by (FK → User, owner), status (9-value state machine below), theft_date, theft_city, theft_location (PostGIS Point), description, owner_recovery_confirmed fields, deleted_at.
- **RecoveryRecord** — id, theft_report (**one-to-one** FK → TheftReport), logged_by (FK → User, authority), recovery_location (PostGIS Point), fuzzy_match_score, evidence_photos (up to 5).
- **CaseTimeline** — id, theft_report (FK → TheftReport, many-to-one), actor (FK → User), action, metadata, timestamp. An append-only per-case event log — every state change writes one row here.
- **SightingReport** — id, bike (FK → Bike, nullable — filled only after authority verification), top_match_bike (FK → Bike, nullable — the fuzzy matcher's top candidate, may differ from the confirmed bike), sighter (FK → User, community), verified_by (FK → User, authority, nullable), sighting_location (PostGIS Point), engine_partial, chassis_partial, fuzzy_match_score, confidence label (HIGH/MEDIUM/LOW), owner_confirmation_status, is_archived.
- **Notification** — id, user (FK → User, recipient), report (FK → TheftReport, nullable), sighting (FK → SightingReport, nullable), type (9 event types), delivery_channel (in_app/email/sms), is_read, metadata, created_at.
- **AuditLog** — id, user (FK → User, `SET_NULL` — survives the actor's account being deleted), table_affected, record_id, action, old_value, new_value (JSON), ip_address, timestamp. Enforced immutable: application code blocks update/delete, and the database itself revokes UPDATE/DELETE grants on this table.
- **MLAnalysisCache** — id, analysis_type (hotspot_clusters / corridor_analysis / trend_analytics / recovery_zones / recovery_radius), scope_city (nullable = national), result_data (JSON), expires_at, record_count. No foreign keys — pure cached batch-job output, not a live relationship.

**Cardinalities:** User 1→* Bike (owns); User 1→* TheftReport (reported_by); Bike 1→* TheftReport (many over its life, only one *active* at a time); TheftReport 1→1 RecoveryRecord; TheftReport 1→* CaseTimeline; TheftReport 1→* SightingReport; TheftReport 1→* Notification; SightingReport 1→* Notification; User 1→* Notification (recipient); User 1→* AuditLog (actor, nullable).

### Theft-report state machine

Nine status values. Two are legacy (`stolen`, `under_investigation` — kept for old seeded data); the current pipeline is the other seven:

```
new_case → under_review → active_investigation → bike_located → pending_verification → recovered → closed
```

Every non-terminal state can also go directly to `closed`. `closed` is terminal.

**Two layers of transition rules** — show both if the diagram is meant to explain the design, not just the happy path:
1. **Model-level "physics"** — which transitions exist at all (the chain above, plus the closed-exit from each state).
2. **Authority's actual permission** — narrower. An Authority account may only drive: `new_case→under_review→active_investigation→bike_located→pending_verification`. **Authority cannot move a case to `recovered` directly, from any state.** That transition only happens via the *owner's* confirmation, or an Admin override — a deliberate control closing a gap an earlier version of the system had (Authority could previously skip the owner-confirmation step).

### End-to-end case flow (narrative)

Four participants: Owner, Community, Authority, System (API + notification service).

1. **Owner** files a theft report → System saves it as `new_case` → System notifies same-city Authority accounts and same-city Community accounts (no personal info in the community broadcast).
2. **Community** member submits a sighting with a partial engine/chassis number (+ optional photo) → System runs fuzzy matching automatically (rapidfuzz WRatio, against every bike under an active report) → System records a confidence score and label (HIGH ≥85, MEDIUM ≥70, LOW <70).
3. If the score ≥ 70, System notifies the **Owner**: "yes / no / not sure" prompt. If the score ≥ 85 *and* a photo was attached, System also immediately escalates to **Authority** as urgent (doesn't wait for the owner).
4. **Owner** responds "yes" → System escalates the sighting to **Authority** attention. (If the owner doesn't respond within 24 hours, System auto-escalates anyway.)
5. **Authority** advances the case through their allowed transitions (`under_review` → `active_investigation` → `bike_located` → `pending_verification`), verifying the sighting along the way.
6. **Authority** logs a recovery (location, evidence photos) → System updates the case, notifies the **Owner**.
7. **Owner** confirms final receipt of the bike → System closes the case (`closed`) → System sends a thank-you notification to every **Community** account that contributed a sighting to this case.

Every state-changing step also writes one row to CaseTimeline and one to AuditLog.

### Notifications

Nine event types: `theft_reported`, `status_update`, `recovery`, `recovery_amended`, `sighting_matched`, `sighting_owner_handshake`, `sighting_owner_response`, `community_closure`, `system/urgent`. Only **in-app** delivery is live; email and SMS (Twilio) service code exists and is unit-tested but deliberately not wired into the live flow yet.

### Geospatial analytics (four batch jobs, cached, not live queries)

| Job | What it does | Key parameters |
|---|---|---|
| Theft hotspot clustering | DBSCAN over recent theft locations (haversine metric) → named clusters with centroid, report count, radius | 180-day lookback, min 10 records, min_samples=3 |
| Theft-to-recovery corridor analysis | DBSCAN over theft→recovery displacement vectors (flat-earth km) → clusters labelled with a 16-point compass bearing (e.g. "SSE, ~8 km") | eps=8 km, min_samples=3, min 3 paired records |
| City trend analytics | Month-over-month theft count / recovery count / recovery-rate % per city, plus a national aggregate | Weekly refresh |
| Recovery-distance statistics | Mean/median/min/max/std of straight-line theft→recovery distance | Min 3 paired records |

## 4. Figures 4.1–4.5 — architecture and data model (already generated)

These five exist in `docs/diagrams/` and are used as-is in TRD.md Chapter 4. Listed here for completeness and so a regeneration keeps the same content if ever redrawn.

**4.1 System Architecture Diagram** — flowchart: Users (Admin/Authority/Owner/Community) → React Frontend (Vite) → Django REST API (JWT + RBAC) → PostgreSQL + PostGIS. API also branches to a Notification Service (→ SMTP, → Twilio — both present in the diagram but should be labelled "implemented, not yet live-wired," not shown as active) and an ML Analytics Service (→ MLAnalysisCache).

**4.2 UML Sequence Diagram** — the 7-step end-to-end case flow from §3, across Owner / Frontend / API / Community / Authority / Notification Service / PostgreSQL-PostGIS participants.

**4.3 UML Use Case Diagram** — actors (Admin, Authority, Owner, Community) against four grouped use-case clusters: Authentication & Access (Register, Login, Role-Based Access), Case Management (Register Bike, File Theft Report, Update Case Status, Log Recovery, Confirm Recovery), Sighting & Verification (Submit Sighting «include» Fuzzy Match «include» Owner Handshake «extend» Verify Sighting), Monitoring & Intelligence (View Notifications, View Analytics, Manage Users, View Audit Logs). SMTP/SMS shown as external services connected only to the notification use case.

**4.4 UML Class Diagram** — classes for User, Bike, TheftReport, RecoveryRecord, CaseTimeline, SightingReport, Notification, AuditLog, MLAnalysisCache, with the attributes and cardinalities from §3's entity list. (The current rendered version simplifies by folding RecoveryRecord and CaseTimeline into TheftReport/Notification for legibility — §3 above has the full physical version; use it if redrawing.)

**4.5 Database Diagram (ER)** — same entities as 4.4, in entity-relationship notation. Three PostGIS `Point` geometry columns: `TheftReport.theft_location`, `RecoveryRecord.recovery_location`, `SightingReport.sighting_location`. `MLAnalysisCache` is deliberately disconnected from every other table by foreign key (cached batch output, not a live relationship).

## 5. Figure 4.6 — Interface Wireframes (new)

Low-fidelity wireframes, one per key screen, not a navigation flowchart (a separate flow diagram — `docs/diagrams/figure6-gui-user-flow.mmd` — already covers navigation structure and can stay as supporting material). Each wireframe should show layout blocks (nav bar, form fields, buttons, cards, tables) at box-and-label fidelity, not real visual design.

Screens to wireframe:

1. **Login / Register** — email + password fields, role is assigned server-side (not user-selected) except Authority which is admin-provisioned; "Forgot password" link; toggle between login/register.
2. **Owner Dashboard** — top nav (My Bikes / My Reports / Notifications), a "My Bikes" card grid (bike photo placeholder, make/model, engine/chassis number, a "Report Stolen" button per bike), an active-reports summary panel.
3. **File Theft Report form** (Owner) — bike selector (dropdown of owned bikes), theft date picker, city field, location picker (map or lat/lng), free-text description, submit button.
4. **Submit Sighting form** (Community) — partial engine number field, partial chassis number field (at least one required), location picker, optional photo upload, submit button. No case ID required from the user — matching happens server-side.
5. **Owner Sighting Confirmation prompt** — a modal/card showing the matched bike's photo and details, confidence badge (HIGH/MEDIUM/LOW), three buttons: Yes / No / Not Sure.
6. **Authority Case Queue** — a filterable table (status, city already scoped to the officer) with columns: Report ID, Bike, Owner, Status, Filed Date, Action button ("Advance Status" opens the status-transition modal showing only the officer's currently-allowed next statuses per §3).
7. **Authority Recovery Log form** — case reference (read-only), recovery location picker, evidence photo upload (up to 5), fuzzy-match score display (read-only, populated from the matched sighting), submit button.
8. **Authority Analytics Dashboard** — four panels matching the four analytics jobs in §3: a hotspot map (cluster markers sized by report count), a corridor-bearing compass/rose visualization, a trend line chart (theft vs. recovery count by month), a recovery-distance summary stat block (mean/median/min/max).
9. **Admin User Management** — a table of users (name, email, role, city, verified status) with an "Add Authority Account" form (name, email, badge number, city).
10. **Admin Audit Log view** — a read-only, filterable table (timestamp, actor, action, table affected) — explicitly no edit/delete controls anywhere on this screen, reflecting that the underlying data is immutable.

## 6. Figure 5.1 — Business Model Canvas

Standard 9-block Business Model Canvas layout (Key Partners / Key Activities / Key Resources / Value Propositions / Customer Relationships / Channels / Cost Structure / Revenue Streams, with Customer Segments implicit in the four roles). Content, drawn directly from TRD.md Chapter 5:

- **Key Partners** — none currently (open-source stack only); natural future partners are city/provincial police authorities and existing citizen-reporting bodies (e.g. CPLC) whose gap in coverage motivated the project.
- **Key Activities** — maintaining the six backend apps and React frontend; operating the four scheduled analytics jobs; reviewing the audit log; onboarding Authority accounts city by city.
- **Key Resources** — the fuzzy-matching and geospatial analytics pipeline (the project's main technical differentiator); the role-gated case workflow and its audit trail; a zero-licensing-cost open-source stack.
- **Value Propositions** — Owner: a trackable case instead of a report that disappears into a call centre. Community: a way to act on a sighting immediately from a phone. Authority: a pre-organized case queue with owner-verification built in, plus hotspot/corridor analytics computed automatically. City: theft-pattern intelligence that improves as more reports are filed, at no software cost.
- **Customer Relationships** — self-service for Owner/Community; Authority accounts provisioned by Admin (badge-number verification required); ongoing engagement driven by the notification loop.
- **Channels** — direct browser access, no install; notification-driven return visits; potential distribution through partnership with an existing body like CPLC rather than building a user base from zero.
- **Cost Structure** — server/database hosting (PostGIS-capable), domain registration, reserved Twilio quota (not yet metered since SMS isn't live), development effort (~9,000 LOC, 4-person team). No per-seat or per-API-call licensing anywhere in the stack.
- **Revenue Streams** — none currently (academic project). Plausible future model: municipal/provincial licensing (a city or police department pays for a scoped deployment), mirroring how Punjab's AVLS is funded — a government-commissioned system, not a consumer subscription — while keeping owner/community-facing reporting free.

## 7. Figures 6.1–6.2 — Methodology and planning

**6.1 Software Development Cycle** — a simple iterative loop, not project-specific: `Backlog → Design → Build → Test → Review → Release`, looping back to Backlog. Illustrates the Iterative-and-Incremental methodology (TRD §6.1), chosen over Waterfall/Spiral/RAD because the team discovered several design decisions — like the Authority transition whitelist in §3 above — only by building and testing, not by upfront specification.

**6.2 Project Plan with Gantt Chart** — visualize the 11 milestones from TRD Table 6.2 against a timeline. No exact dates are recorded in the project; the git history spans roughly February–August 2026 based on available evidence (a coverage log dated 11 May 2026 sits mid-history, and the most recent commits are from August 2026), so a reasonable **illustrative** spread across a ~24-week window is:

| # | Milestone | Approx. week range |
|---|---|---|
| 1 | Requirements & literature review | 1–2 |
| 2 | System & database design | 2–4 |
| 3 | Authentication & RBAC | 4–6 |
| 4 | Bikes & theft reporting | 6–8 |
| 5 | Sightings & fuzzy matching | 8–11 |
| 6 | Case-workflow hardening | 11–12 |
| 7 | Geospatial analytics engine | 12–15 |
| 8 | Frontend feature build-out | 9–17 (overlaps 4–7, built alongside each backend app) |
| 9 | Notification hardening | 15–16 |
| 10 | Integration testing & bug fixing | 17–21 |
| 11 | Documentation & final report | 20–24 |

Adjust to the team's actual FYP calendar if real dates are available — this spread is inferred from commit history, not a recorded schedule.

## 8. Figures 7.1–7.2 — Testing

**7.1 Software Testing Life Cycle** — phased diagram matching BTT's actual approach (TRD §7.2, §7.4), not a generic textbook STLC: `Unit Testing (pytest, per backend module) → Integration Testing (cross-app: sighting save + fuzzy match in one request, status transition + timeline + audit log together) → System/API Testing (full endpoint behavior, black-box against Chapter 3 requirements) → End-to-End Testing (Playwright, full six-step cross-role narrative: owner report → community sighting → owner handshake → authority escalation → recovery → close) → User Acceptance Testing → Release`.

**7.2 Bug Life Cycle** — BTT tracks defects through git commit history directly, not a separate issue tracker (TRD §7.9.1), so the lifecycle is lighter than a formal enterprise flow. Recommended states, matching what the project's own bug table (TRD Table 7.9.5) actually uses: `Found (during dev/testing) → Root-caused → Fixed (commit + regression test added) → Verified (regression test passes in the suite) → Closed`, with an `Open` side-state for a bug that's identified and documented but not yet fixed (the project currently has one: a DBSCAN clustering-radius unit-conversion issue, tracked as Medium/P3/Open). If the diagram should instead match the generic enterprise bug-lifecycle taught in the course template (New → Assigned → Open → Fixed → Pending Retest → Retest → Verified → Reopen/Duplicate/Rejected/Deferred/Not-a-bug → Closed), that fuller state set is the standard one to use — but note it's more granular than BTT's actual lightweight process, so treat it as the idealized/taught version rather than a description of what really happened.
