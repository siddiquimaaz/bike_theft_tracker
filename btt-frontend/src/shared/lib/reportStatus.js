/**
 * Single source of truth for theft-report status semantics.
 *
 * Two generations of statuses coexist: the legacy pair (`stolen`,
 * `under_investigation`) still present in seeded data, and the current
 * seven-step flow.  Dashboards used to hard-code the legacy pair when counting
 * KPIs, so their tiles read zero for anything filed through the current flow.
 * Everything that needs to ask "is this case still open?" now asks here.
 */

export const REPORT_STATUSES = {
  // Legacy statuses (seeded data / backward compatibility)
  STOLEN:               'stolen',
  UNDER_INVESTIGATION:  'under_investigation',

  NEW_CASE:             'new_case',
  UNDER_REVIEW:         'under_review',
  ACTIVE_INVESTIGATION: 'active_investigation',
  BIKE_LOCATED:         'bike_located',
  PENDING_VERIFICATION: 'pending_verification',
  RECOVERED:            'recovered',
  CLOSED:               'closed',
};

export const STATUS_LABELS = {
  stolen:               'Stolen',
  under_investigation:  'Under Investigation',

  new_case:             'New Case',
  under_review:         'Under Review',
  active_investigation: 'Active Investigation',
  bike_located:         'Bike Located',
  pending_verification: 'Pending Verification',
  recovered:            'Recovered',
  closed:               'Closed',
};

export const STATUS_COLORS = {
  stolen:               'red',
  under_investigation:  'amber',

  new_case:             'red',
  under_review:         'orange',
  active_investigation: 'blue',
  bike_located:         'amber',
  pending_verification: 'purple',
  recovered:            'green',
  closed:               'gray',
};

// The legal status transitions for authority (one-step forward advance).
// NOTE: Authority officers cannot close a case — only the bike owner (via
// recovery confirmation) or an admin can do that.  Once a case reaches
// pending_verification the ball is in the owner's court: the owner must
// confirm receipt via /recovery/confirm/ to close.  No authority advance
// button should appear from pending_verification or recovered onward.
export const STATUS_TRANSITIONS = {
  // Legacy path (seeded data) — stolen only moves forward one step
  stolen:               'under_investigation',

  new_case:             'under_review',
  under_review:         'active_investigation',
  active_investigation: 'bike_located',
  bike_located:         'pending_verification',
  // pending_verification → owner-only confirm receipt (/recovery/confirm/)
  // under_investigation  → recovery is logged by authority (no direct status jump)
  // recovered            → owner-only confirm receipt or admin override
  // No entries deliberately: authority has NO advance button from here on.
};

/** Filed but nobody has picked it up yet. */
export const AWAITING_TRIAGE_STATUSES = [
  REPORT_STATUSES.STOLEN,
  REPORT_STATUSES.NEW_CASE,
];

/** An officer is actively working the case. */
export const INVESTIGATING_STATUSES = [
  REPORT_STATUSES.UNDER_INVESTIGATION,
  REPORT_STATUSES.UNDER_REVIEW,
  REPORT_STATUSES.ACTIVE_INVESTIGATION,
  REPORT_STATUSES.BIKE_LOCATED,
];

/** Terminal states — the case needs no further work. */
export const RESOLVED_STATUSES = [
  REPORT_STATUSES.RECOVERED,
  REPORT_STATUSES.CLOSED,
];

/** Everything that is not yet resolved, including owner-confirmation limbo. */
export const ACTIVE_STATUSES = [
  ...AWAITING_TRIAGE_STATUSES,
  ...INVESTIGATING_STATUSES,
  REPORT_STATUSES.PENDING_VERIFICATION,
];

export const isAwaitingTriage = (status) => AWAITING_TRIAGE_STATUSES.includes(status);
export const isInvestigating  = (status) => INVESTIGATING_STATUSES.includes(status);
export const isResolved       = (status) => RESOLVED_STATUSES.includes(status);
export const isActiveCase     = (status) => ACTIVE_STATUSES.includes(status);

/** Statuses from which an authority may log a recovery. */
export const CAN_LOG_RECOVERY_STATUSES = [
  REPORT_STATUSES.UNDER_INVESTIGATION,
  REPORT_STATUSES.ACTIVE_INVESTIGATION,
  REPORT_STATUSES.BIKE_LOCATED,
];

export const canLogRecovery = (status) => CAN_LOG_RECOVERY_STATUSES.includes(status);

/** Statuses where the case is parked waiting on the owner to confirm receipt. */
export const AWAITING_OWNER_STATUSES = [
  REPORT_STATUSES.PENDING_VERIFICATION,
  REPORT_STATUSES.RECOVERED,
];

export const isAwaitingOwner = (status) => AWAITING_OWNER_STATUSES.includes(status);

export const statusLabel = (status) => STATUS_LABELS[status] ?? status ?? '—';
export const statusColor = (status) => STATUS_COLORS[status] ?? 'gray';

/** Count how many reports fall into a status predicate. */
export const countByStatus = (reports, predicate) =>
  reports.reduce((n, r) => (predicate(r.status) ? n + 1 : n), 0);
