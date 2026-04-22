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
  NEW_CASE:             'new_case',
  UNDER_REVIEW:         'under_review',
  ACTIVE_INVESTIGATION: 'active_investigation',
  BIKE_LOCATED:         'bike_located',
  PENDING_VERIFICATION: 'pending_verification',
  RECOVERED:            'recovered',
  CLOSED:               'closed',
};

export const STATUS_LABELS = {
  new_case:             'New Case',
  under_review:         'Under Review',
  active_investigation: 'Active Investigation',
  bike_located:         'Bike Located',
  pending_verification: 'Pending Verification',
  recovered:           'Recovered',
  closed:              'Closed',
};

export const STATUS_COLORS = {
  new_case:             'red',
  under_review:         'orange',
  active_investigation: 'blue',
  bike_located:         'amber',
  pending_verification: 'purple',
  recovered:           'green',
  closed:              'gray',
};

// The legal status transitions for authority
export const STATUS_TRANSITIONS = {
  new_case:             'under_review',
  under_review:         'active_investigation',
  active_investigation: 'bike_located',
  bike_located:         'pending_verification',
  pending_verification: 'recovered',
  recovered:           'closed',
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
