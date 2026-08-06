import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import { Button } from '@/shared/components/ui';

export default function UnauthorizedPage() {
  const { homeRoute } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-btt-900 flex items-center justify-center">
      <div className="text-center max-w-sm">
        <div className="text-6xl mb-4">🚫</div>
        <h1 className="font-heading text-2xl font-bold text-gray-100 mb-2">Access Denied</h1>
        <p className="text-sm text-muted mb-6">You don't have permission to view this page.</p>
        <Button variant="primary" onClick={() => navigate(homeRoute)}>Go to My Dashboard</Button>
      </div>
    </div>
  );
}
