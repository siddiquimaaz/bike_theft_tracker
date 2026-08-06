import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import ProtectedRoute from './guards/ProtectedRoute';
import RoleRoute from './guards/RoleRoute';
import MainLayout from '@/shared/components/layout/MainLayout';
import DashboardLayout from '@/shared/components/layout/DashboardLayout';
import Spinner from '@/shared/components/ui/Spinner';

// Every page is code-split: the login screen no longer ships the admin
// dashboard, the ML pages or any role's tables in its first payload.

// Auth pages
const LoginPage          = lazy(() => import('@/features/auth/pages/LoginPage'));
const RegisterPage       = lazy(() => import('@/features/auth/pages/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('@/features/auth/pages/ForgotPasswordPage'));
const ResetPasswordPage  = lazy(() => import('@/features/auth/pages/ResetPasswordPage'));
const VerifyEmailPage    = lazy(() => import('@/features/auth/pages/VerifyEmailPage'));

// Dashboards
const OwnerDashboard     = lazy(() => import('@/features/dashboard/pages/OwnerDashboard'));
const AuthorityDashboard = lazy(() => import('@/features/dashboard/pages/AuthorityDashboard'));
const CommunityDashboard = lazy(() => import('@/features/dashboard/pages/CommunityDashboard'));
const AdminDashboard     = lazy(() => import('@/features/admin/pages/AdminDashboard'));

// Owner
const BikesPage        = lazy(() => import('@/features/bikes/pages/BikesPage'));
const OwnerReportsPage = lazy(() => import('@/features/reports/pages/OwnerReportsPage'));

// Authority
const CaseReportsPage = lazy(() => import('@/features/reports/pages/CaseReportsPage'));
const SightingsPage   = lazy(() => import('@/features/sightings/pages/SightingsPage'));
const FuzzySearchPage = lazy(() => import('@/features/ml/pages/FuzzySearchPage'));
const HotspotPage     = lazy(() => import('@/features/ml/pages/HotspotPage'));

// Admin
const UsersPage     = lazy(() => import('@/features/admin/pages/UsersPage'));
const AnalyticsPage = lazy(() => import('@/features/admin/pages/AnalyticsPage'));
const AuditLogsPage = lazy(() => import('@/features/admin/pages/AuditLogsPage'));

// Community
const SubmitSightingPage = lazy(() => import('@/features/sightings/pages/SubmitSightingPage'));

// Shared
const NotificationsPage = lazy(() => import('@/features/notifications/pages/NotificationsPage'));
const UnauthorizedPage  = lazy(() => import('./pages/UnauthorizedPage'));
const NotFoundPage      = lazy(() => import('./pages/NotFoundPage'));

/** Every role area is guarded the same way — auth, then role, then the shell. */
function roleArea(role) {
  return (
    <ProtectedRoute>
      <RoleRoute roles={[role]}>
        <DashboardLayout />
      </RoleRoute>
    </ProtectedRoute>
  );
}

function RoleRedirect() {
  const { isAuthenticated, homeRoute } = useAuth();
  return <Navigate to={isAuthenticated ? homeRoute : '/login'} replace />;
}

export default function AppRoutes() {
  return (
    <Suspense fallback={<Spinner fullscreen />}>
      <Routes>
        {/* Root redirect */}
        <Route path="/" element={<RoleRedirect />} />

        {/* ── Auth (no sidebar) ────────────────────────────────── */}
        <Route element={<MainLayout />}>
          <Route path="/login"                 element={<LoginPage />} />
          <Route path="/register"              element={<RegisterPage />} />
          <Route path="/verify-email/:token"   element={<VerifyEmailPage />} />
          <Route path="/forgot-password"       element={<ForgotPasswordPage />} />
          <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
        </Route>

        {/* ── Owner ────────────────────────────────────────────── */}
        <Route path="/owner" element={roleArea('owner')}>
          <Route path="dashboard"     element={<OwnerDashboard />} />
          <Route path="bikes"         element={<BikesPage />} />
          <Route path="reports"       element={<OwnerReportsPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
        </Route>

        {/* ── Authority ────────────────────────────────────────── */}
        <Route path="/authority" element={roleArea('authority')}>
          <Route path="dashboard"     element={<AuthorityDashboard />} />
          <Route path="reports"       element={<CaseReportsPage />} />
          <Route path="sightings"     element={<SightingsPage />} />
          <Route path="fuzzy"         element={<FuzzySearchPage />} />
          <Route path="hotspots"      element={<HotspotPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
        </Route>

        {/* ── Admin ────────────────────────────────────────────── */}
        <Route path="/admin" element={roleArea('admin')}>
          <Route path="dashboard"     element={<AdminDashboard />} />
          <Route path="users"         element={<UsersPage />} />
          <Route path="analytics"     element={<AnalyticsPage />} />
          <Route path="audit"         element={<AuditLogsPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
        </Route>

        {/* ── Community ────────────────────────────────────────── */}
        <Route path="/community" element={roleArea('community')}>
          <Route path="dashboard"     element={<CommunityDashboard />} />
          <Route path="sightings"     element={<SubmitSightingPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
        </Route>

        {/* ── Misc ─────────────────────────────────────────────── */}
        <Route path="/unauthorized" element={<UnauthorizedPage />} />
        <Route path="*"             element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}
