import { createContext, useContext, useMemo } from 'react';
import { useAuth } from './AuthContext';
import { ROLES } from '@/shared/lib/constants';

const RoleContext = createContext(null);

export function RoleProvider({ children }) {
  const { role } = useAuth();

  // Memoised on `role`: without this every consumer re-rendered whenever any
  // ancestor did, because `can`/`is` were fresh object literals each render.
  const value = useMemo(() => {
    const isAuthority = role === ROLES.AUTHORITY;
    const isAdmin     = role === ROLES.ADMIN;
    const isOwner     = role === ROLES.OWNER;
    const staffLevel  = isAuthority || isAdmin;

    return {
      role,
      can: {
        // Bikes
        manageBikes:        isOwner,
        // Reports
        fileReport:         isOwner,
        viewAllReports:     staffLevel,
        updateReportStatus: staffLevel,
        deleteReport:       isAdmin,
        logRecovery:        staffLevel,
        // Sightings
        submitSighting:     true,
        verifySighting:     staffLevel,
        viewAllSightings:   staffLevel,
        // ML
        fuzzySearch:        staffLevel,
        viewHotspots:       staffLevel,
        viewTrends:         isAdmin,
        triggerML:          isAdmin,
        // Admin
        manageUsers:        isAdmin,
        viewAuditLogs:      isAdmin,
        viewAnalytics:      isAdmin,
      },
      is: {
        owner:     isOwner,
        community: role === ROLES.COMMUNITY,
        authority: isAuthority,
        admin:     isAdmin,
      },
    };
  }, [role]);

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
}

export function useRole() {
  const ctx = useContext(RoleContext);
  if (!ctx) throw new Error('useRole must be used inside <RoleProvider>');
  return ctx;
}
