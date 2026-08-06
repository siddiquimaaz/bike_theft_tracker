import { useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { verifyEmail } from '../api';
import { apiErrorMessage } from '@/shared/lib/http';
import { Alert, Button, Spinner } from '@/shared/components/ui';

export default function VerifyEmailPage() {
  const { token } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      setError('Missing verification token.');
      return undefined;
    }

    let cancelled = false;
    setLoading(true);
    setError('');

    verifyEmail(token)
      .then(() => { if (!cancelled) setSuccess(true); })
      .catch((err) => { if (!cancelled) setError(apiErrorMessage(err, 'Verification failed.')); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [token]);

  if (loading) return <div className="w-[380px]"><Spinner /></div>;

  return (
    <div className="w-[380px]">
      <div className="card">
        <h2 className="font-heading font-semibold text-base text-gray-100 mb-2">Verify your email</h2>
        <p className="text-sm text-muted mb-5">We’re confirming your email address. This usually takes a second.</p>

        {success ? (
          <>
            <Alert type="success" message="Email verified successfully. You can now log in." />
            <Button variant="primary" className="w-full justify-center mt-4" onClick={() => navigate('/login')}>
              Continue to login
            </Button>
          </>
        ) : (
          <>
            <Alert type="error" message={error || 'Verification failed.'} />
            <div className="flex gap-2 mt-4">
              <Button variant="primary" className="flex-1 justify-center" onClick={() => window.location.reload()}>
                Try again
              </Button>
              <Button variant="ghost" className="flex-1 justify-center" onClick={() => navigate('/register')}>
                Register
              </Button>
            </div>
            <div className="divider" />
            <p className="text-xs text-muted text-center">
              <Link to="/login" className="text-primary hover:underline">← Back to login</Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
