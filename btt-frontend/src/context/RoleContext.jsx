import { createContext, useContext } from 'react';
import { useAuth } from './AuthContext';
import { ROLES } from '../utils/constants';

const RoleContext = createContext(null);

export function RoleProvider({ children }) {
  const { role } = useAuth();

  const can = {
    // Bikes
    manageBikes:       role === ROLES.OWNER,
    // Reports
    fileReport:        role === ROLES.OWNER,
    viewAllReports:    role === ROLES.AUTHORITY || role === ROLES.ADMIN,
    updateReportStatus:role === ROLES.AUTHORITY || role === ROLES.ADMIN,
    deleteReport:      role === ROLES.ADMIN,
    logRecovery:       role === ROLES.AUTHORITY || role === ROLES.ADMIN,
    // Sightings
    submitSighting:    true,
    verifySighting:    role === ROLES.AUTHORITY || role === ROLES.ADMIN,
    viewAllSightings:  role === ROLES.AUTHORITY || role === ROLES.ADMIN,
    // ML
    fuzzySearch:       role === ROLES.AUTHORITY || role === ROLES.ADMIN,
    viewHotspots:      role === ROLES.AUTHORITY || role === ROLES.ADMIN,
    viewTrends:        role === ROLES.ADMIN,
    triggerML:         role === ROLES.ADMIN,
    // Admin
    manageUsers:       role === ROLES.ADMIN,
    viewAuditLogs:     role === ROLES.ADMIN,
    viewAnalytics:     role === ROLES.ADMIN,
  };

  const is = {
    owner:     role === ROLES.OWNER,
    community: role === ROLES.COMMUNITY,
    authority: role === ROLES.AUTHORITY,
    admin:     role === ROLES.ADMIN,
  };

  return (
    <RoleContext.Provider value={{ role, can, is }}>
      {children}
    </RoleContext.Provider>
  );
}

export function useRole() {
  const ctx = useContext(RoleContext);
  if (!ctx) throw new Error('useRole must be used inside <RoleProvider>');
  return ctx;
}
