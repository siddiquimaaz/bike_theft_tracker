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

export const ROLE_HOME = {
  owner:     '/owner/dashboard',
  community: '/community/dashboard',
  authority: '/authority/dashboard',
  admin:     '/admin/dashboard',
};

// Fuzzy-match score bands, shared by every surface that renders a confidence
// (sightings list, sighting detail, submit history, fuzzy search).
export const MATCH_CONFIDENCE_THRESHOLDS = { HIGH: 85, MEDIUM: 70 };

export const MATCH_CONFIDENCE_COLORS = {
  HIGH:   'text-emerald-400',
  MEDIUM: 'text-amber-400',
  LOW:    'text-red-400',
};

export const MATCH_CONFIDENCE_BARS = {
  HIGH:   'bg-emerald-500',
  MEDIUM: 'bg-amber-500',
  LOW:    'bg-red-500',
};
