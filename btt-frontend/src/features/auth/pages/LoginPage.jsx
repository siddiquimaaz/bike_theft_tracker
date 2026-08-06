import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { useForm } from '@/shared/hooks/useForm';
import { ROLE_HOME } from '@/shared/lib/constants';
import { Alert, Button, PasswordInput } from '@/shared/components/ui';

const DEMO_ACCOUNTS = [
  { role: 'Admin',     email: 'admin@demo.btt',             pass: 'DemoAdmin@2024' },
  { role: 'Authority', email: 'authority.karachi@demo.btt', pass: 'Authority@2024' },
  { role: 'Owner',     email: 'owner000@demo.btt',          pass: 'Owner@2024' },
  { role: 'Community', email: 'community@demo.btt',         pass: 'Community@2024' },
];

export default function LoginPage() {
  const { values: form, set, setValues } = useForm({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const { login, error, clearError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const setField = (key) => (e) => { clearError(); set(key)(e); };

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const user = await login(form.email, form.password);
      const redirectTo = location.state?.from?.pathname;
      navigate(redirectTo ?? ROLE_HOME[user.role] ?? '/', { replace: true });
    } catch {
      // AuthContext already surfaced the message in `error`.
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-[380px]">
      {/* Logo */}
      <div className="text-center mb-8">
        <div className="w-14 h-14 bg-primary rounded-2xl flex items-center justify-center text-2xl mx-auto mb-4">🏍️</div>
        <h1 className="font-heading text-2xl font-bold text-gray-100">Bike Theft Tracker</h1>
        <p className="text-xs text-faint mt-1">Group 58 · SSUET Karachi · Batch 2022F</p>
      </div>

      <div className="card">
        <h2 className="font-heading font-semibold text-base text-gray-100 mb-5">Sign in to your account</h2>

        <Alert type="error" message={error} onClose={clearError} />

        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <label>Email address</label>
            <input type="email" placeholder="you@example.com" value={form.email} onChange={setField('email')} required autoFocus />
          </div>
          <div className="form-row">
            <label>Password</label>
            <PasswordInput placeholder="••••••••" value={form.password} onChange={setField('password')} required />
          </div>

          <div className="flex justify-end mb-4">
            <Link to="/forgot-password" className="text-xs text-muted hover:text-primary transition-colors">Forgot password?</Link>
          </div>

          <Button variant="primary" type="submit" loading={loading} className="w-full justify-center">
            Sign In →
          </Button>
        </form>

        <div className="divider" />
        <p className="text-xs text-muted text-center">
          No account?{' '}
          <Link to="/register" className="text-primary hover:underline">Register here</Link>
        </p>

        {/* Demo credentials */}
        <div className="mt-4 p-3 bg-btt-700 rounded-btt border border-white/[.06]">
          <p className="text-[11px] text-faint font-medium mb-2 uppercase tracking-wider">Demo accounts</p>
          {DEMO_ACCOUNTS.map(({ role, email, pass }) => (
            <button
              key={role}
              type="button"
              className="w-full text-left text-[11px] text-muted hover:text-gray-100 py-0.5 transition-colors"
              onClick={() => { clearError(); setValues({ email, password: pass }); }}
            >
              <span className="text-primary font-medium">{role}:</span> {email}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
