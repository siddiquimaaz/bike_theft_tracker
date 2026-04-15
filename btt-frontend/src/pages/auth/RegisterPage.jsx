import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { register } from '../../api/authApi';
import { Alert, Button } from '../../components/UI';

const EMPTY = { full_name: '', email: '', cnic: '', role: 'owner', city: '', password: '', confirm: '' };

export default function RegisterPage() {
  const [form,    setForm]    = useState(EMPTY);
  const [error,   setError]   = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const set = (k) => (e) => { setError(''); setForm((f) => ({ ...f, [k]: e.target.value })); };

  async function handleSubmit(e) {
    e.preventDefault();
    if (form.password !== form.confirm) { setError("Passwords don't match."); return; }
    setLoading(true);
    try {
      const { full_name, email, cnic, role, city, password } = form;
      await register({ full_name, email, cnic, role, city, password, confirm_password: form.confirm });
      setSuccess(true);
    } catch (err) {
      const d = err.response?.data;
      setError(d?.detail ?? d?.email?.[0] ?? d?.password?.[0] ?? err.message ?? 'Registration failed.');
    } finally {
      setLoading(false);
    }
  }

  if (success) return (
    <div className="w-[380px] text-center">
      <div className="card">
        <div className="text-4xl mb-4">📧</div>
        <h2 className="font-heading font-semibold text-lg text-gray-100 mb-2">Check your inbox</h2>
        <p className="text-sm text-muted mb-5">A verification email has been sent. Click the link to activate your account, then log in.</p>
        <Button variant="primary" className="w-full justify-center" onClick={() => navigate('/login')}>Go to Login →</Button>
      </div>
    </div>
  );

  return (
    <div className="w-[420px]">
      <div className="text-center mb-6">
        <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center text-xl mx-auto mb-3">🏍️</div>
        <h1 className="font-heading text-xl font-bold text-gray-100">Create an account</h1>
      </div>

      <div className="card">
        <Alert type="error" message={error} onClose={() => setError('')} />

        <form onSubmit={handleSubmit}>
          <div className="form-row"><label>Full Name *</label><input placeholder="Ali Khan" value={form.full_name} onChange={set('full_name')} required /></div>

          <div className="grid grid-cols-2 gap-x-3">
            <div className="form-row"><label>Email *</label><input type="email" placeholder="you@example.com" value={form.email} onChange={set('email')} required /></div>
            <div className="form-row"><label>CNIC *</label><input placeholder="4200012345678" value={form.cnic} onChange={set('cnic')} required /></div>
          </div>

          <div className="grid grid-cols-2 gap-x-3">
            <div className="form-row">
              <label>Role *</label>
              <select value={form.role} onChange={set('role')}>
                <option value="owner">Bike Owner</option>
                <option value="community">Community Reporter</option>
              </select>
            </div>
            <div className="form-row"><label>City</label><input placeholder="Karachi" value={form.city} onChange={set('city')} /></div>
          </div>

          <div className="grid grid-cols-2 gap-x-3">
            <div className="form-row"><label>Password *</label><input type="password" placeholder="Min 8 chars" value={form.password} onChange={set('password')} required /></div>
            <div className="form-row"><label>Confirm *</label><input type="password" placeholder="Repeat" value={form.confirm} onChange={set('confirm')} required /></div>
          </div>

          <Button variant="primary" type="submit" loading={loading} className="w-full justify-center mt-1">
            Create Account →
          </Button>
        </form>

        <div className="divider" />
        <p className="text-xs text-muted text-center">
          Already have an account?{' '}
          <Link to="/login" className="text-primary hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
