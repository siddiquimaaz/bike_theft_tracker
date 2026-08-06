import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { register } from '../api';
import { useEmailAvailability, useCnicAvailability } from '../useAvailabilityCheck';
import FieldStatus from '../components/FieldStatus';
import { useForm } from '@/shared/hooks/useForm';
import { apiErrorMessage } from '@/shared/lib/http';
import { Alert, Button, PasswordInput } from '@/shared/components/ui';

const EMPTY = { full_name: '', email: '', cnic: '', role: 'owner', city: '', password: '', confirm: '' };

const ROLE_OPTIONS = [
  { value: 'owner',     label: 'Bike Owner' },
  { value: 'community', label: 'Community Reporter' },
];

export default function RegisterPage() {
  const { values: form, set, setValue } = useForm(EMPTY);
  const [error,   setError]   = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const email = useEmailAvailability(form.email);
  const cnic  = useCnicAvailability(form.cnic);

  const navigate = useNavigate();

  const setField = (key) => (e) => { setError(''); set(key)(e); };
  // Reset the status indicator as soon as the user edits the field; the next
  // onBlur (or the debounce) re-runs the check.
  const setEmail = (e) => { setError(''); email.clear(); setValue('email', e.target.value); };
  const setCnic  = (e) => { setError(''); cnic.clear();  setValue('cnic',  e.target.value); };

  // Submit is blocked while either field is still checking or has a known error.
  const canSubmit = !loading && !email.blocksSubmit && !cnic.blocksSubmit;

  async function handleSubmit(e) {
    e.preventDefault();
    if (form.password !== form.confirm) { setError("Passwords don't match."); return; }
    // Force a final sync check if the user typed quickly and blurred before debounce.
    await Promise.all([email.verify(), cnic.verify()]);
    if (!canSubmit) return;

    setLoading(true);
    try {
      const { full_name, email: emailValue, cnic: cnicValue, role, city, password } = form;
      await register({
        full_name, email: emailValue, cnic: cnicValue, role, city, password,
        confirm_password: form.confirm,
      });
      setSuccess(true);
    } catch (err) {
      setError(apiErrorMessage(err, 'Registration failed.'));
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
          <div className="form-row">
            <label>Full Name *</label>
            <input placeholder="Ali Khan" value={form.full_name} onChange={setField('full_name')} required />
          </div>

          <div className="grid grid-cols-2 gap-x-3">
            <div className="form-row">
              <label>Email *</label>
              <input type="email" placeholder="you@example.com"
                     value={form.email} onChange={setEmail} onBlur={email.onBlur} required />
              <FieldStatus state={email.state} message={email.message} />
            </div>
            <div className="form-row">
              <label>CNIC *</label>
              <input placeholder="4200012345678" inputMode="numeric" maxLength={13}
                     value={form.cnic} onChange={setCnic} onBlur={cnic.onBlur} required />
              <FieldStatus state={cnic.state} message={cnic.message} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-x-3">
            <div className="form-row">
              <label>Role *</label>
              <select value={form.role} onChange={setField('role')}>
                {ROLE_OPTIONS.map(({ value, label }) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <label>City</label>
              <input placeholder="Karachi" value={form.city} onChange={setField('city')} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-x-3">
            <div className="form-row">
              <label>Password *</label>
              <PasswordInput placeholder="Min 8 chars" value={form.password} onChange={setField('password')} minLength={8} required />
            </div>
            <div className="form-row">
              <label>Confirm *</label>
              <PasswordInput placeholder="Repeat" value={form.confirm} onChange={setField('confirm')} minLength={8} required />
            </div>
          </div>

          <Button variant="primary" type="submit" loading={loading} disabled={!canSubmit} className="w-full justify-center mt-1">
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
