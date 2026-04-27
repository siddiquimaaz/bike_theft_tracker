export const ROLES = {
  OWNER:     'owner',
  COMMUNITY: 'community',
  AUTHORITY: 'authority',
  ADMIN:     'admin',
};

export const ROLE_LABELS = {
  owner:     'Bike Owner',
  community: 'Community',
  authority: 'Authority',
  admin:     'Admin',
};

export const ROLE_COLORS = {
  owner:     'amber',
  community: 'green',
  authority: 'blue',
  admin:     'purple',
};

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
  recovered:           'Recovered',
  closed:              'Closed',
};

export const STATUS_COLORS = {
  stolen:               'red',
  under_investigation:  'amber',

  new_case:             'red',
  under_review:         'orange',
  active_investigation: 'blue',
  bike_located:         'amber',
  pending_verification: 'purple',
  recovered:           'green',
  closed:              'gray',
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

export const MATCH_CONFIDENCE_COLORS = {
  HIGH:   'text-emerald-400',
  MEDIUM: 'text-amber-400',
  LOW:    'text-red-400',
};

export const ROLE_HOME = {
  owner:     '/owner/dashboard',
  community: '/community/dashboard',
  authority: '/authority/dashboard',
  admin:     '/admin/dashboard',
};
