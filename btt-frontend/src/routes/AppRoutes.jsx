import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { RoleProvider } from '../context/RoleContext';

import ProtectedRoute  from './ProtectedRoute';
import RoleRoute       from './RoleRoute';
import MainLayout      from '../layouts/MainLayout';
import DashboardLayout from '../layouts/DashboardLayout';

// Auth pages
import LoginPage          from '../pages/auth/LoginPage';
import RegisterPage       from '../pages/auth/RegisterPage';
import ForgotPasswordPage from '../pages/auth/ForgotPasswordPage';
import ResetPasswordPage  from '../pages/auth/ResetPasswordPage';
import VerifyEmailPage    from '../pages/auth/VerifyEmailPage';

// Owner pages
import OwnerDashboard from '../pages/owner/OwnerDashboard';
import BikesPage      from '../pages/owner/BikesPage';
import ReportsPage    from '../pages/owner/ReportsPage';

// Authority pages
import AuthorityDashboard from '../pages/authority/AuthorityDashboard';
import CaseReportsPage    from '../pages/authority/CaseReportsPage';
import SightingsPage      from '../pages/authority/SightingsPage';
import FuzzySearchPage    from '../pages/authority/FuzzySearchPage';
import HotspotPage        from '../pages/authority/HotspotPage';

// Admin pages
import AdminDashboard from '../pages/admin/AdminDashboard';
import UsersPage      from '../pages/admin/UsersPage';
import AnalyticsPage  from '../pages/admin/AnalyticsPage';
import AuditLogsPage  from '../pages/admin/AuditLogsPage';

// Community pages
import CommunityDashboard  from '../pages/community/CommunityDashboard';
import SubmitSightingPage  from '../pages/community/SubmitSightingPage';

// Shared pages
import NotificationsPage from '../pages/shared/NotificationsPage';
import UnauthorizedPage  from '../pages/shared/UnauthorizedPage';
import NotFoundPage      from '../pages/shared/NotFoundPage';

function RoleRedirect() {
  const { isAuthenticated, homeRoute } = useAuth();
  return isAuthenticated ? <Navigate to={homeRoute} replace /> : <Navigate to="/login" replace />;
}

export default function AppRoutes() {
  return (
    <RoleProvider>
      <Routes>
        {/* Root redirect */}
        <Route path="/" element={<RoleRedirect />} />

        {/* ── Auth (no sidebar) ────────────────────────────────── */}
        <Route element={<MainLayout />}>
          <Route path="/login"                     element={<LoginPage />} />
          <Route path="/register"                  element={<RegisterPage />} />
          <Route path="/verify-email/:token"       element={<VerifyEmailPage />} />
          <Route path="/forgot-password"           element={<ForgotPasswordPage />} />
          <Route path="/reset-password/:token"     element={<ResetPasswordPage />} />
        </Route>

        {/* ── Owner ────────────────────────────────────────────── */}
        <Route path="/owner" element={
          <ProtectedRoute>
            <RoleRoute roles={['owner']}>
              <DashboardLayout />
            </RoleRoute>
          </ProtectedRoute>
        }>
          <Route path="dashboard" element={<OwnerDashboard />} />
          <Route path="bikes"     element={<BikesPage />} />
          <Route path="reports"   element={<ReportsPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
        </Route>

        {/* ── Authority ────────────────────────────────────────── */}
        <Route path="/authority" element={
          <ProtectedRoute>
            <RoleRoute roles={['authority']}>
              <DashboardLayout />
            </RoleRoute>
          </ProtectedRoute>
        }>
          <Route path="dashboard"  element={<AuthorityDashboard />} />
          <Route path="reports"    element={<CaseReportsPage />} />
          <Route path="sightings"  element={<SightingsPage />} />
          <Route path="fuzzy"      element={<FuzzySearchPage />} />
          <Route path="hotspots"   element={<HotspotPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
        </Route>

        {/* ── Admin ────────────────────────────────────────────── */}
        <Route path="/admin" element={
          <ProtectedRoute>
            <RoleRoute roles={['admin']}>
              <DashboardLayout />
            </RoleRoute>
          </ProtectedRoute>
        }>
          <Route path="dashboard"   element={<AdminDashboard />} />
          <Route path="users"       element={<UsersPage />} />
          <Route path="analytics"   element={<AnalyticsPage />} />
          <Route path="audit"       element={<AuditLogsPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
        </Route>

        {/* ── Community ────────────────────────────────────────── */}
        <Route path="/community" element={
          <ProtectedRoute>
            <RoleRoute roles={['community']}>
              <DashboardLayout />
            </RoleRoute>
          </ProtectedRoute>
        }>
          <Route path="dashboard"  element={<CommunityDashboard />} />
          <Route path="sightings"  element={<SubmitSightingPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
        </Route>

        {/* ── Misc ─────────────────────────────────────────────── */}
        <Route path="/unauthorized" element={<UnauthorizedPage />} />
        <Route path="*"             element={<NotFoundPage />} />
      </Routes>
    </RoleProvider>
  );
}
