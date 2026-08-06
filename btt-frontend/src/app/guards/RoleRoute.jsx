import { Navigate } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import Spinner from '@/shared/components/ui/Spinner';

/**
 * Wraps a route that is only accessible to specific roles.
 * Usage: <RoleRoute roles={['admin', 'authority']}> ... </RoleRoute>
 */
export default function RoleRoute({ roles, children }) {
  const { role, isAuthenticated, loading, homeRoute } = useAuth();

  if (loading) return <Spinner fullscreen />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!roles.includes(role)) return <Navigate to={homeRoute} replace />;
  return children;
}
