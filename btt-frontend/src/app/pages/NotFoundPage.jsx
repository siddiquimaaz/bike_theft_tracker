import { useNavigate } from 'react-router-dom';
import { Button } from '@/shared/components/ui';

export default function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-btt-900 flex items-center justify-center">
      <div className="text-center max-w-sm">
        <div className="font-heading text-8xl font-bold text-btt-600 mb-4">404</div>
        <h1 className="font-heading text-xl font-bold text-gray-100 mb-2">Page not found</h1>
        <p className="text-sm text-muted mb-6">This page doesn't exist or has been moved.</p>
        <Button variant="primary" onClick={() => navigate('/')}>← Go Home</Button>
      </div>
    </div>
  );
}
