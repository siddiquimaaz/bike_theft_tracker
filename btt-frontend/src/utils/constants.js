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
  STOLEN:               'stolen',
  UNDER_INVESTIGATION:  'under_investigation',
  RECOVERED:            'recovered',
  CLOSED:               'closed',
};

export const STATUS_LABELS = {
  stolen:              'Stolen',
  under_investigation: 'Under Investigation',
  recovered:           'Recovered',
  closed:              'Closed',
};

export const STATUS_COLORS = {
  stolen:              'red',
  under_investigation: 'orange',
  recovered:           'green',
  closed:              'gray',
};

// The legal status transitions for authority
export const STATUS_TRANSITIONS = {
  stolen:              'under_investigation',
  under_investigation: 'recovered',
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
