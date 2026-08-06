import { useState } from 'react';
import { Link } from 'react-router-dom';
import { forgotPassword } from '../api';
import { apiErrorMessage } from '@/shared/lib/http';
import { Alert, Button } from '@/shared/components/ui';

export default function ForgotPasswordPage() {
  const [email,   setEmail]   = useState('');
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');
  const [sent,    setSent]    = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(apiErrorMessage(err, 'Request failed.'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-[380px]">
      <div className="card">
        <div className="text-2xl mb-3">🔑</div>
        <h2 className="font-heading font-semibold text-base text-gray-100 mb-1">Forgot your password?</h2>
        <p className="text-sm text-muted mb-5">Enter your email and we'll send a reset link.</p>

        {sent ? (
          <Alert type="success" message="Reset link sent! Check your inbox." />
        ) : (
          <form onSubmit={handleSubmit}>
            <Alert type="error" message={error} onClose={() => setError('')} />
            <div className="form-row">
              <label>Email</label>
              <input type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
            </div>
            <Button variant="primary" type="submit" loading={loading} className="w-full justify-center">Send Reset Link</Button>
          </form>
        )}

        <div className="divider" />
        <p className="text-xs text-muted text-center">
          <Link to="/login" className="text-primary hover:underline">← Back to login</Link>
        </p>
      </div>
    </div>
  );
}
