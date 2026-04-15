import { Outlet, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * Thin wrapper used by public/auth pages (login, register, etc.).
 * Already authenticated users are redirected straight to their home.
 */
export default function MainLayout() {
  const { isAuthenticated, homeRoute } = useAuth();
  if (isAuthenticated) return <Navigate to={homeRoute} replace />;

  return (
    <div className="min-h-screen bg-btt-900 flex items-center justify-center px-4"
         style={{ background: 'radial-gradient(ellipse at 30% 20%, rgba(245,158,11,.05) 0%, transparent 55%), #06091a' }}>
      <Outlet />
    </div>
  );
}
