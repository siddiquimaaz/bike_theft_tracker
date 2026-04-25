import { useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { verifyEmail } from '../../api/authApi';
import { Alert, Button, Spinner } from '../../components/UI';

export default function VerifyEmailPage() {
  const { token } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      setError('');
      try {
        await verifyEmail(token);
        if (!cancelled) setSuccess(true);
      } catch (err) {
        const msg =
          err.response?.data?.error ??
          err.response?.data?.detail ??
          err.message ??
          'Verification failed.';
        if (!cancelled) setError(msg);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    if (token) run();
    else { setLoading(false); setError('Missing verification token.'); }
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
              <Button variant="secondary" className="flex-1 justify-center" onClick={() => navigate('/register')}>
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

