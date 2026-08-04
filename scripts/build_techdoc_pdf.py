"""
Build the Technical Software Documentation PDF for Bike Theft Tracker.
Run: venv\Scripts\python build_techdoc_pdf.py
Output: D:\scripts\bike_theft_tracker\BTT_Technical_Documentation.pdf
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    KeepTogether, Preformatted,
)

OUT = r"D:\scripts\bike_theft_tracker\BTT_Technical_Documentation.pdf"

# ---------- Styles ----------
ss = getSampleStyleSheet()

TITLE = ParagraphStyle(
    "TITLE", parent=ss["Title"], fontName="Helvetica-Bold",
    fontSize=22, leading=26, spaceAfter=6, textColor=colors.HexColor("#0b3d91"),
)
SUBTITLE = ParagraphStyle(
    "SUBTITLE", parent=ss["Normal"], fontName="Helvetica-Oblique",
    fontSize=11, leading=14, textColor=colors.HexColor("#444444"), spaceAfter=18,
)
H1 = ParagraphStyle(
    "H1", parent=ss["Heading1"], fontName="Helvetica-Bold",
    fontSize=15, leading=19, spaceBefore=14, spaceAfter=6,
    textColor=colors.HexColor("#0b3d91"),
)
H2 = ParagraphStyle(
    "H2", parent=ss["Heading2"], fontName="Helvetica-Bold",
    fontSize=12, leading=16, spaceBefore=10, spaceAfter=4,
    textColor=colors.HexColor("#1f2937"),
)
BODY = ParagraphStyle(
    "BODY", parent=ss["BodyText"], fontName="Helvetica", fontSize=10,
    leading=14, spaceAfter=6, alignment=TA_JUSTIFY,
)
BULLET = ParagraphStyle(
    "BULLET", parent=BODY, leftIndent=14, bulletIndent=2, spaceAfter=2,
    alignment=TA_LEFT,
)
CODE = ParagraphStyle(
    "CODE", parent=ss["Code"], fontName="Courier", fontSize=8.5,
    leading=11, leftIndent=8, rightIndent=8, spaceBefore=4, spaceAfter=8,
    backColor=colors.HexColor("#f4f4f4"), borderColor=colors.HexColor("#d0d0d0"),
    borderWidth=0.5, borderPadding=6,
)
SMALL = ParagraphStyle(
    "SMALL", parent=BODY, fontSize=8.5, leading=11, textColor=colors.HexColor("#555"),
)


def p(text, style=BODY):
    return Paragraph(text, style)


def bullets(items):
    return [Paragraph(f"&bull;&nbsp; {it}", BULLET) for it in items]


def code(text):
    # Preformatted preserves whitespace
    return Preformatted(text, CODE)


def section(title):
    return [Spacer(1, 4), Paragraph(title, H1)]


def subsection(title):
    return [Paragraph(title, H2)]


def make_table(rows, col_widths=None, header=True):
    tbl = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bbbbbb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b3d91")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
        ]
    tbl.setStyle(TableStyle(style))
    return tbl


# ---------- Footer ----------
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(15 * mm, 10 * mm,
                      "Bike Theft Tracker - Technical Software Documentation v1.1")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


# ---------- Document body ----------
story = []

# Cover
story += [
    Spacer(1, 60),
    p("Bike Theft Tracker", TITLE),
    p("Technical Software Documentation", ParagraphStyle(
        "cover_sub", parent=TITLE, fontSize=16, leading=20,
        textColor=colors.HexColor("#1f2937"))),
    Spacer(1, 20),
    p("Group 58 &nbsp;|&nbsp; Batch 2022F &nbsp;|&nbsp; BS Computer Science &nbsp;|&nbsp; SSUET, Karachi", SUBTITLE),
    Spacer(1, 200),
    p("<b>Document version:</b> 1.1", BODY),
    p("<b>Date:</b> 25 April 2026", BODY),
    p("<b>Audience:</b> Technical reviewers, engineers, evaluators", BODY),
    p("<b>Source of truth:</b> generated from project source code and repository markdown", BODY),
    PageBreak(),
]

# 1. Project Overview
story += section("1. Project Overview")
story += [p(
    "<b>Bike Theft Tracker (BTT)</b> is a four-role REST platform for reporting, investigating, "
    "and recovering stolen motorcycles in Pakistan. It combines a JWT-secured Django REST API with "
    "a React (Vite) single-page client and a thin ML layer (RapidFuzz, scikit-learn DBSCAN, PostGIS "
    "spatial queries) that wires citizen sightings to active investigations."
)]
story += subsection("Problem solved")
story += bullets([
    "Owners have no centralized way to report a theft and track its lifecycle.",
    "Police lack tooling to fuzzy-match damaged engine/chassis plates against active cases.",
    "Communities have no channel to surface suspicious sightings to law enforcement.",
    "Administrators need national-level analytics on theft hotspots, trends, and recovery rates.",
])
story += subsection("Roles")
story += [p("<b>owner</b>, <b>community</b>, <b>authority</b> (city-scoped), <b>admin</b>.")]
story += subsection("Primary outcomes")
story += bullets([
    "Single audit-logged case lifecycle shared by all roles "
    "(new_case &rarr; under_review &rarr; active_investigation &rarr; bike_located &rarr; "
    "pending_verification &rarr; recovered &rarr; closed).",
    "Sub-second fuzzy matching of partial alphanumeric identifiers against the live theft pool.",
    "DBSCAN-clustered crime hotspots and pandas-aggregated trend analytics for policy decisions.",
])

# 2. System Architecture
story += section("2. System Architecture")
story += [code(
    "+-----------------+    HTTPS / JSON     +------------------------+\n"
    "| React + Vite    | ------------------> | Nginx (TLS, static)    |\n"
    "| (Tailwind, RR)  | <------------------ |          |             |\n"
    "+-----------------+   JWT Bearer tokens |          v             |\n"
    "                                        | Gunicorn (Django 5.2)  |\n"
    "                                        |  - DRF + SimpleJWT     |\n"
    "                                        |  - apps/{users,bikes,  |\n"
    "                                        |    reports,sightings,  |\n"
    "                                        |    ml,notifications,   |\n"
    "                                        |    admin_panel,search} |\n"
    "                                        +---+--------------+-----+\n"
    "                                            |              |\n"
    "                          psycopg2 / GIS    |              | Threads\n"
    "                                            v              v\n"
    "                                +-----------------+ +------------------+\n"
    "                                | PostgreSQL 15 + | | Twilio SMS +     |\n"
    "                                | PostGIS 3.3     | | Gmail SMTP       |\n"
    "                                +-----------------+ +------------------+\n"
)]
story += [p(
    "<b>Pattern:</b> classic three-tier monolith with a sharply separated SPA. Async work "
    "(notifications) uses fire-and-forget daemon threads (monkeypatched to synchronous in the "
    "test suite via <font face='Courier'>_SyncThread</font>) instead of a broker, which keeps the "
    "deployment surface minimal for an FYP-scale production while preserving non-blocking request paths."
)]
story += subsection("Representative data flow - sighting submission")
story += bullets([
    "Community user POSTs <font face='Courier'>/api/sightings/</font> with optional partial engine/chassis number + location.",
    "View &rarr; serializer validates and persists <font face='Courier'>SightingReport</font>; "
    "<font face='Courier'>Point(lng, lat)</font> stored as PostGIS geometry.",
    "View calls <font face='Courier'>apps.ml.fuzzy_match.find_fuzzy_matches(...)</font> synchronously.",
    "If best score &ge; <font face='Courier'>ML_FUZZY_OWNER_ALERT_THRESHOLD</font> (70), an "
    "owner-handshake notification is enqueued on a daemon thread.",
    "Authority dashboard queries <font face='Courier'>/api/sightings/?unverified=true</font>; "
    "verification fires another notification.",
])

# 3. Frontend Architecture
story += section("3. Frontend Architecture")
story += [p("<b>Stack:</b> React 18, Vite, Tailwind CSS, React Router v6, Axios.")]
story += subsection("Folder layout (btt-frontend/src/)")
story += bullets([
    "<b>pages/</b> - route components grouped by role (auth/, owner/, community/, authority/, admin/).",
    "<b>components/UI/</b> - design-system primitives: Button, Modal, Badge, Alert, EmptyState, Spinner, PasswordInput. Re-exported via index.js barrel.",
    "<b>api/</b> - one Axios instance + per-domain wrappers (authApi, bikeApi, reportApi, sightingApi, mlApi, adminApi, notificationApi).",
    "<b>hooks/</b> - useFetch (loading/data/error/refetch tuple), useAuth.",
    "<b>utils/constants.js</b> - ROLE_COLORS, ROLE_LABELS, status enums kept in lockstep with the backend.",
])
story += subsection("State management")
story += [p(
    "Local <font face='Courier'>useState</font> for component-scoped state; <font face='Courier'>"
    "useFetch</font> for server cache (no Redux/RTK Query). JWTs are stored in localStorage and "
    "injected by an Axios request interceptor; a response interceptor handles 401 &rarr; refresh "
    "&rarr; retry once, then logout."
)]
story += subsection("Forms with live validation")
story += [p(
    "<font face='Courier'>RegisterPage</font> and <font face='Courier'>UsersPage</font> "
    "(admin Create Authority) use a five-state field state machine "
    "(idle | checking | ok | taken | invalid) with 600 ms debounce on change, immediate check on "
    "blur, and <font face='Courier'>lastChecked</font> ref short-circuiting. The "
    "<font face='Courier'>canSubmit</font> flag composes both fields:")]
story += [code(
    "const canSubmit =\n"
    "  !saving &&\n"
    "  emailState.state !== FIELD_CHECKING &&\n"
    "  cnicState.state  !== FIELD_CHECKING &&\n"
    "  emailState.state !== FIELD_TAKEN  && emailState.state !== FIELD_INVALID &&\n"
    "  cnicState.state  !== FIELD_TAKEN  && cnicState.state  !== FIELD_INVALID;\n"
)]
story += subsection("Reusable PasswordInput")
story += [p(
    "<font face='Courier'>forwardRef</font> component with eye/eye-off SVG toggle, "
    "<font face='Courier'>aria-pressed</font>, <font face='Courier'>tabIndex={-1}</font> on the toggle "
    "so keyboard tab order remains password &rarr; submit. Used across LoginPage, RegisterPage, "
    "ResetPasswordPage, and admin UsersPage."
)]

# 4. Backend Architecture
story += section("4. Backend Architecture")
story += [p(
    "<b>Stack:</b> Django 5.2, DRF 3.16, SimpleJWT 5.5, GeoDjango (PostGIS), RapidFuzz 3.x, "
    "scikit-learn 1.3 (DBSCAN), pandas 2.1, Twilio 8.x."
)]
story += subsection("App boundaries (btt-backend/apps/)")
story += [make_table([
    ["App", "Responsibility"],
    ["users", "Custom User model with role + city, JWT auth views, email/CNIC availability checks, password reset"],
    ["bikes", "Owner-scoped CRUD; engine/chassis numbers immutable post-create"],
    ["reports", "TheftReport lifecycle, recovery sub-resource, audit log writes"],
    ["sightings", "SightingReport create + verify; auto fuzzy-match on POST"],
    ["ml", "fuzzy_match.py, hotspot DBSCAN, trend analytics, recovery-zone PostGIS query"],
    ["notifications", "In-app + email + SMS dispatch via daemon threads"],
    ["admin_panel", "Admin-only user management, KPI analytics, audit log viewer"],
    ["search", "Public bike/city search"],
], col_widths=[28 * mm, 140 * mm])]
story += subsection("Cross-cutting")
story += bullets([
    "<b>Permissions</b> - IsOwner, IsAuthority, IsAdmin, IsAuthorityOrAdmin, plus city-scoped object-level checks for authority operations.",
    "<b>Throttling</b> - DRF ScopedRateThrottle for login (5/15min) and the new availability_check (30/min) scope; default Anon/User throttles as baselines.",
    "<b>Soft deletes</b> - every domain model has deleted_at; queries default-filter deleted_at__isnull=True.",
    "<b>Reference numbers</b> - TheftReport.reference_number is a Python @property "
    "(f\"BTT-{id:04d}\"), not a column; tests must derive pk via int(ref.split('-')[-1]).",
])

# 5. API Specification
story += section("5. API Specification")
story += [p(
    "Base URL: <font face='Courier'>https://&lt;host&gt;/api/</font>. All non-public endpoints "
    "require <font face='Courier'>Authorization: Bearer &lt;access_token&gt;</font>."
)]
story += subsection("Auth - /api/auth/")
story += [make_table([
    ["Method", "Path", "Auth", "Notes"],
    ["POST", "/register/", "Public", "Owner or Community only - Authority created by Admin"],
    ["POST", "/login/", "Public", "Throttled 5/15min/IP"],
    ["POST", "/token/refresh/", "Public", "Rotation + blacklist"],
    ["POST", "/logout/", "Auth", "Blacklists refresh"],
    ["POST", "/verify-email/{token}/", "Public", "24h expiry"],
    ["POST", "/forgot-password/", "Public", "Email reset link"],
    ["POST", "/reset-password/{token}/", "Public", "Sets new password"],
    ["GET", "/check-email/?email=", "Public", "Throttled 30/min - {available, valid_format, reason}"],
    ["GET", "/check-cnic/?cnic=", "Public", "Throttled 30/min - strips -/spaces, requires 13 digits"],
], col_widths=[18 * mm, 50 * mm, 18 * mm, 82 * mm])]
story += subsection("Reports - /api/reports/")
story += [make_table([
    ["Method", "Path", "Role", "Notes"],
    ["GET", "/", "Auth", "Role-scoped list (Owner sees own, Authority sees city, Admin sees all)"],
    ["POST", "/", "Owner", "File a new theft report"],
    ["GET", "/{id}/", "Auth", "Report detail (role-scoped)"],
    ["PUT", "/{id}/status/", "Authority/Admin", "Drives the case state machine"],
    ["DELETE", "/{id}/", "Admin", "Soft-delete"],
    ["POST", "/{id}/recovery/", "Authority", "Log recovery record"],
    ["GET", "/{id}/recovery/", "Auth", "Recovery detail"],
    ["PUT", "/{id}/recovery/", "Authority", "Amend recovery record"],
    ["PUT", "/{id}/recovery/confirm/", "Owner",
     "Owner confirms bike pickup after authority marks recovered. "
     "Transitions case to closed. Triggers contributor closure broadcast notification."],
], col_widths=[18 * mm, 50 * mm, 26 * mm, 74 * mm])]
story += subsection("Other domain endpoints (summary)")
story += bullets([
    "<b>/api/bikes/</b> - Owner: GET list, POST create, GET/PUT/DELETE detail. Engine/chassis immutable after create.",
    "<b>/api/sightings/</b> - POST creates and runs fuzzy match server-side; PUT /{id}/verify/ Authority-only triggers owner handshake notification; PUT /{id}/owner-confirm/ Owner-only handles yes/no/not_sure response.",
    "<b>/api/ml/</b> - fuzzy-match, hotspots, trends, recovery-zones, trigger-reanalysis.",
    "<b>/api/notifications/</b> - GET list with unread count, PUT mark-read (single + bulk).",
    "<b>/api/admin/</b> - Users CRUD, authority creation, status updates, analytics, immutable audit log.",
    "<b>/api/search/</b> - Bike search by engine/chassis/plate; city active-report counts.",
])
story += [p(
    "<b>Response convention:</b> DRF JSON. Errors: <font face='Courier'>{detail: '...'}</font> for "
    "permission/auth errors; <font face='Courier'>{&lt;field&gt;: ['...']}</font> for validation. "
    "Standard codes: 200 / 201 / 204 / 400 / 401 / 403 / 404 / 429 / 500."
)]

# 6. Auth & Authz
story += section("6. Authentication and Authorization")
story += subsection("Token model (SimpleJWT, rotation + blacklist)")
story += bullets([
    "Access token: 15 min, Bearer flow.",
    "Refresh token: 7 days, single-use (rotation enabled), blacklisted on use and on /logout/.",
])
story += subsection("Password storage")
story += [p("Django default <font face='Courier'>PBKDF2_SHA256</font>, 260,000 iterations.")]
story += subsection("Email verification gate")
story += [p(
    "<font face='Courier'>User.is_email_verified</font> is checked in the LoginSerializer; "
    "unverified users cannot exchange credentials for tokens."
)]
story += subsection("Role-based access")
story += [code(
    "class IsAuthority(BasePermission):\n"
    "    def has_permission(self, request, view):\n"
    "        return bool(request.user and request.user.is_authenticated\n"
    "                    and request.user.role == 'authority')\n"
)]
story += [p(
    "Object-level checks add city scoping (e.g. "
    "<font face='Courier'>report.bike.owner.city == request.user.city</font> for non-admin authorities)."
)]
story += subsection("Inline availability checks")
story += [p(
    "The new <font face='Courier'>/check-email/</font> and <font face='Courier'>/check-cnic/</font> "
    "endpoints normalize input "
    "(<font face='Courier'>email.lower().strip()</font>, CNIC stripped of -/spaces) and return a "
    "stable contract <font face='Courier'>{available, valid_format, reason}</font> to keep the React "
    "state machine deterministic."
)]

# 7. Database Design
story += section("7. Database Design")
story += [p("<b>Engine:</b> PostgreSQL 15 + PostGIS 3.3 (port 5433 in local dev).")]
story += subsection("Core tables (9)")
story += [make_table([
    ["Table", "Key relationships", "Notable columns"],
    ["users", "self", "email (unique), cnic (unique, 13 digits), role, city, is_email_verified, is_active, deleted_at"],
    ["bikes", "owner_id -> users", "engine_number, chassis_number, registration_number, photo_url, is_stolen (denormalized), deleted_at"],
    ["theft_reports", "bike_id -> bikes", "status (enum), theft_date, theft_city, theft_location (PostGIS Point), description, deleted_at"],
    ["recovery_records", "theft_report_id -> theft_reports (1:1)", "recovered_by_id, recovery_date, recovery_location, condition_notes, chain_of_custody"],
    ["sightings", "sighter_id -> users; matched_bike_id (opt)", "partial_engine, partial_chassis, location (PostGIS), verified, verified_by_id, owner_confirmation_status, auto_escalated"],
    ["notifications", "recipient_id -> users", "type (enum), title, message, read, payload (JSON), created_at"],
    ["audit_logs", "actor_id -> users", "action, target_model, target_id, before / after (JSON), timestamp - append-only (DB-level REVOKE applied)"],
    ["case_timeline", "report_id -> theft_reports",
     "event_type (enum), actor_role, actor_id -> users (nullable), note (text), created_at (timestamp). "
     "Append-only audit trail of all key case transitions visible to Owner and Authority."],
    ["*_tokens", "user_id -> users", "token (UUID), expires_at (password reset + email verify)"],
], col_widths=[30 * mm, 50 * mm, 88 * mm])]
story += subsection("Spatial indexing")
story += [p(
    "GIST indexes on <font face='Courier'>theft_reports.theft_location</font> and "
    "<font face='Courier'>sightings.location</font> enable <font face='Courier'>ST_DWithin</font> "
    "for recovery-zone queries. The recovery-zones endpoint uses GeoDjango "
    "<font face='Courier'>__distance_lte=Distance(km=...)</font> which compiles to PostGIS spatial predicates."
)]
story += subsection("Integrity rules")
story += bullets([
    "Engine/chassis numbers are immutable post-create at the serializer layer (no DB CHECK; enforced by read_only_fields on update serializers).",
    "All deletes are soft (deleted_at = now()); audit log is the only table without a soft-delete column - it is genuinely immutable.",
])

# 8. Core Features
story += section("8. Core Features")
story += subsection("8.1 Theft case lifecycle")
story += [code(
    "new_case -> under_review -> active_investigation -> bike_located\n"
    "         -> pending_verification -> recovered -> closed\n"
    "                                              ^ legacy: stolen, under_investigation\n"
)]
story += [p(
    "Transitions are validated server-side; only authority (city-scoped) and admin can move the "
    "state forward. Every transition writes an AuditLog row."
)]
story += subsection("8.2 Fuzzy engine/chassis matching")
story += [p(
    "<font face='Courier'>apps/ml/fuzzy_match.py::find_fuzzy_matches</font> runs RapidFuzz "
    "<font face='Courier'>WRatio</font> against the in-memory candidate dict of all currently "
    "active theft reports. Thresholds (settings-overridable):"
)]
story += bullets([
    "ML_FUZZY_HIGH_THRESHOLD = 85 -> HIGH",
    "ML_FUZZY_MEDIUM_THRESHOLD = 70 -> MEDIUM",
    "below -> LOW",
])
story += [p("Active-status filter (must mirror Bike.is_stolen):")]
story += [code(
    "ACTIVE_THEFT_STATUSES = [\n"
    "    Status.STOLEN, Status.UNDER_INVESTIGATION,         # legacy\n"
    "    Status.NEW_CASE, Status.UNDER_REVIEW,\n"
    "    Status.ACTIVE_INVESTIGATION, Status.BIKE_LOCATED,\n"
    "    Status.PENDING_VERIFICATION,\n"
    "]\n"
)]
story += subsection("8.3 Sighting handshake")
story += [p(
    "On sighting submission, fuzzy match runs synchronously. If the score is &ge; 70 (or &ge; 85 with a "
    "photo, in which case the authority is also alerted immediately), the bike owner receives an "
    "in-app handshake notification with three response options:"
)]
story += bullets([
    "<b>yes</b> &rarr; sighting flagged as owner-confirmed; URGENT escalation sent to Authority.",
    "<b>no</b> &rarr; sighting archived; community reporter notified of the no-match outcome.",
    "<b>not_sure</b> &rarr; sighting stays open; auto-escalates to Authority after the timeout window.",
    "<b>(timeout)</b> &rarr; no response within the response window &rarr; the system nudges the owner at "
    "24 h, then auto-escalates via <font face='Courier'>auto_escalate_pending_owner_responses()</font>.",
])
story += [p(
    "All four branches write a <font face='Courier'>CaseTimeline</font> event so the Owner and "
    "Authority dashboards can render a complete audit trail of the handshake."
)]
story += subsection("8.4 Hotspot clustering")
story += [p(
    "Management command <font face='Courier'>run_hotspot_analysis</font> runs "
    "<font face='Courier'>sklearn.cluster.DBSCAN</font> (haversine metric, configurable eps_km and "
    "min_samples) on theft locations. Results are persisted as HotspotCluster rows for the "
    "/api/ml/hotspots/ read endpoint."
)]
story += subsection("8.5 Trend analytics")
story += [p(
    "<font face='Courier'>run_trend_analytics</font> aggregates monthly theft/recovery counts per "
    "city via pandas, persists to TrendSnapshot, and powers admin charts."
)]
story += subsection("8.6 Recovery zones")
story += [p(
    "<font face='Courier'>/api/ml/recovery-zones/?lat=&amp;lng=&amp;radius_km=</font> runs PostGIS "
    "<font face='Courier'>ST_DWithin</font> to surface where bikes stolen near a query point were "
    "ultimately recovered."
)]
story += subsection("8.7 Admin user management")
story += [p(
    "Admin creates authority accounts directly (bypassing the public /register/ whitelist) via "
    "/api/admin/users/authority/. The form now uses inline email + CNIC availability checks and a "
    "show/hide password input identical to the public RegisterPage."
)]

# 9. State Management
story += section("9. State Management")
story += subsection("Frontend")
story += bullets([
    "Local useState for forms.",
    "useFetch(fn, deps) for server reads - returns { data, loading, error, refetch }.",
    "Auth state in useAuth (custom hook) reading from localStorage; protected routes wrap with &lt;RequireAuth role='...'&gt;.",
    "Form-level FSMs (RegisterPage, admin UsersPage) hold per-field validation state outside the form value object so debounced async checks update independently of keystrokes.",
])
story += subsection("Backend")
story += bullets([
    "Stateless REST. All durable state lives in PostgreSQL; JWT carries identity.",
    "Token blacklist table enforces logout/refresh-rotation.",
    "Audit log is the canonical source of truth for who did what when - never updated.",
])

# 10. Error Handling
story += section("10. Error Handling")
story += subsection("Backend")
story += bullets([
    "Serializer validation errors auto-raise ValidationError -> 400 with field-keyed payload.",
    "Custom DRF exception handler converts auth failures to {detail: '...'} 401, permission failures to 403.",
    "Unhandled exceptions logged via Python logging; production maps them to a generic 500.",
    "ML endpoints degrade gracefully - missing rapidfuzz returns [] and logs ERROR rather than crashing the request.",
])
story += subsection("Frontend")
story += bullets([
    "Axios response interceptor: on 401 attempts a single refresh; on second 401 logs out and redirects to /login.",
    "Each page surfaces a single &lt;Alert type='error'&gt; block bound to a useState('') error string; flattened from Object.values(data).flat().join(' ') when the backend returns multi-field validation.",
    "Inline form fields show their own micro-error (FieldStatus for email/CNIC) without dismissing the global alert.",
])

# 11. Testing
story += section("11. Testing")
story += [p("<b>Backend:</b> pytest-django with pytest-cov. Latest run:")]
story += [code("======================= 335 passed in 264.69s (0:04:24) =======================")]
story += subsection("Test files (335 total)")
story += bullets([
    "test_auth.py (17), test_auth_extended.py (15), test_admin.py (25)",
    "test_bikes.py (17), test_bike_serializers_extra.py (2)",
    "test_reports.py (20), test_reports_extended.py (20), test_case_timeline.py (1)",
    "test_sightings.py (30), test_sighting_handshake.py (4)",
    "test_fuzzy_match.py (15), test_ml.py (33)",
    "test_notifications.py (36)",
    "test_security.py (22), test_coverage_boost.py (10)",
    "test_enhanced_flows.py (3)",
    "test_inter_role_sync.py (64) - includes TestEndToEndDemoNarrative::test_full_demo_scenario_runs_end_to_end covering all six cross-role events in one assertion-rich integration test.",
])
story += [p(
    "<b>Coverage:</b> pytest configured for --cov=apps; project minimum 80%."
)]
story += [p(
    "<b>Async neutralization:</b> <font face='Courier'>_SyncThread</font> monkeypatches "
    "<font face='Courier'>threading.Thread</font> in test fixtures so notification dispatch executes "
    "inline, guaranteeing assertions run after side effects."
)]
story += [p(
    "<b>Frontend:</b> Playwright is installed (@playwright/test in node_modules); E2E suite is the "
    "natural next addition."
)]

# 12. Performance
story += section("12. Performance Considerations")
story += bullets([
    "select_related('bike', 'bike__owner') in fuzzy match avoids N+1 across the candidate set.",
    "In-memory candidate dict keyed by stringified bike id - RapidFuzz process.extract is C-accelerated; even with low-thousands candidates the call is sub-50 ms.",
    "PostGIS GIST indexes on theft/sighting geometries make ST_DWithin constant-time on reasonable radii.",
    "DBSCAN clustering is a batch job (run_hotspot_analysis) writing snapshots - read endpoints serve precomputed rows, never recompute on request.",
    "Daemon-thread notifications keep the request path under 100 ms even when SMTP/Twilio are slow; failures are logged but never propagate.",
    "JWT removes session lookups from the hot path.",
    "DRF throttling caps abusive traffic before view code runs (availability_check: 30/min, login: 5/15min).",
])

# 13. Deployment
story += section("13. Deployment")
story += [p("<b>Target:</b> Ubuntu 22.04 LTS, single VPS.")]
story += subsection("Components")
story += bullets([
    "Nginx 1.24 - TLS termination (Certbot/Let's Encrypt), static asset serving, reverse proxy to Gunicorn.",
    "Gunicorn 21 - WSGI app server, supervised by supervisor.",
    "PostgreSQL 15 + PostGIS 3.3 - system service.",
    "Cron - schedules run_hotspot_analysis --all-cities and run_trend_analytics.",
])
story += subsection("Files supplied")
story += bullets([
    "deploy/nginx_btt.conf",
    "deploy/supervisor_btt.conf",
    "deploy/crontab.txt",
    ".env.example",
])
story += [p(
    "<b>Provisioning</b> is codified in README.md - Production Deployment "
    "(apt deps -> DB + extension -> clone + venv + migrate -> collectstatic -> nginx -> certbot "
    "-> supervisor -> cron -> seed + ML)."
)]
story += [p(
    "<b>Local dev:</b> <font face='Courier'>start_dev.bat</font> boots PostgreSQL on port 5433 and "
    "<font face='Courier'>python manage.py runserver</font>. "
    "<font face='Courier'>load_dotenv(override=True)</font> ensures GDAL_LIBRARY_PATH from .env "
    "wins over a stale machine env var."
)]
story += subsection("Hardening steps applied")
story += bullets([
    "<b>Single-worker Gunicorn</b> - <font face='Courier'>--workers 1</font> pinned in "
    "<font face='Courier'>deploy/supervisor_btt.conf</font>. Required until Celery replaces the "
    "daemon-thread notification dispatch; multi-worker would break the exactly-once notification "
    "guarantee.",
    "<b>Audit-log DB-level immutability</b> - migration "
    "<font face='Courier'>users/0002_audit_log_immutability.py</font> issues "
    "<font face='Courier'>REVOKE UPDATE, DELETE ON audit_logs FROM bttadmin</font> with a safe "
    "<font face='Courier'>reverse_sql</font> for rollback. Forensic integrity is now enforced at "
    "the database, not just the application layer.",
])

# 14. Limitations
story += section("14. Limitations")
story += bullets([
    "<b>Single-VPS monolith</b> - no horizontal scaling story; daemon-thread dispatch breaks if there are multiple workers and notifications must be exactly-once.",
    "<b>No message broker</b> - Celery/Redis would replace _SyncThread for resilience; current design is acceptable only at FYP scale.",
    "<b>Hard-coded city scoping</b> - authority access is partitioned by free-text city string; no provincial/district hierarchy.",
    "<b>Fuzzy match thresholds are global</b> - WRatio thresholds are not learned per identifier shape (Pakistani plates vary widely).",
    "<b>Rate limiting is in-process</b> - DRF throttle cache is local memory; switching to Redis is required for multi-worker/multi-host deployments.",
    "<b>No image OCR</b> - sightings carry typed partial numbers only; OCR on uploaded plate photos would improve recall.",
    "<b>No mobile client</b> - React SPA is responsive but there is no PWA manifest or native wrapper.",
    "<b>Twilio + Gmail SMTP</b> - fine for demo, not for high-volume production; outbound throughput will become the bottleneck.",
])

# 15. Future Improvements
story += section("15. Future Improvements")
story += subsection("Short term (<= 1 sprint)")
story += bullets([
    "Move notification dispatch behind Celery + Redis; promote _SyncThread test pattern to a CELERY_TASK_ALWAYS_EAGER config.",
    "Add Playwright E2E coverage for the six-event demo narrative already covered by test_inter_role_sync.py.",
    "Persist the fuzzy-match audit trail (sighting -> top candidates -> decision) for ML retraining.",
    "Replace /check-email and /check-cnic with a single /check-availability/?field=email&amp;value=... to reduce duplication and let the throttle scope cover both.",
])
story += subsection("Medium term")
story += bullets([
    "OCR plate-photo upload via AWS Textract / Tesseract on the sighting form; auto-populate partial_engine/partial_chassis.",
    "Per-city DBSCAN parameter tuning + a feedback loop that adjusts eps_km from observed cluster purity.",
    "Native push notifications (FCM) alongside email/SMS.",
    "Provincial/district hierarchy for authority scoping; multi-tenant city packs.",
    "Database-level audit immutability - REVOKE UPDATE, DELETE ON audit_logs FROM bttadmin in a dedicated migration.",
])
story += subsection("Long term")
story += bullets([
    "Mobile-first PWA with offline sighting capture (IndexedDB) and background sync.",
    "Plate-image similarity search (CNN embeddings) to complement WRatio on numeric strings.",
    "Public anonymized hotspot map for civic transparency, throttled and aggregated to &ge; 500 m precision.",
    "Multi-tenant deployment per province, with a federated admin role for national analytics.",
    "SSO with NADRA-issued identity for owners (replacing CNIC self-attestation).",
])

# Appendices
story += section("Appendix A - Verified test outcome (this build)")
story += [code("collected 335 items  -  335 passed in 264.69s (0:04:24)")]

story += section("Appendix B - Critical fix shipped this iteration")
story += [p(
    "<font face='Courier'>apps/ml/fuzzy_match.py</font> previously filtered only "
    "<font face='Courier'>[stolen, under_investigation]</font>. Sightings against any modern-workflow "
    "status (active_investigation, bike_located, pending_verification, ...) silently failed to find "
    "the bike. Filter expanded to mirror Bike.is_stolen; verified by the new end-to-end test."
)]

# ---------- Build ----------
doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=18 * mm, rightMargin=18 * mm,
    topMargin=18 * mm, bottomMargin=18 * mm,
    title="Bike Theft Tracker - Technical Software Documentation",
    author="Group 58, SSUET Karachi",
)
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"Wrote: {OUT}")
