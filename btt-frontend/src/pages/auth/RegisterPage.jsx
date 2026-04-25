import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { register, checkEmail, checkCnic } from '../../api/authApi';
import { Alert, Button, PasswordInput } from '../../components/UI';

const EMPTY = { full_name: '', email: '', cnic: '', role: 'owner', city: '', password: '', confirm: '' };

// Inline-validation states for email / CNIC.
//   idle      — field untouched or empty
//   checking  — request in flight (debounce done)
//   ok        — available + valid format
//   taken     — format OK but already registered
//   invalid   — bad format (regex failed client-side or server returned valid_format=false)
const FIELD_IDLE     = 'idle';
const FIELD_CHECKING = 'checking';
const FIELD_OK       = 'ok';
const FIELD_TAKEN    = 'taken';
const FIELD_INVALID  = 'invalid';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CNIC_RE  = /^\d{13}$/;

function FieldStatus({ state, message }) {
  if (state === FIELD_IDLE) return null;
  const colorClass = {
    [FIELD_CHECKING]: 'text-muted',
    [FIELD_OK]:       'text-green-400',
    [FIELD_TAKEN]:    'text-red-400',
    [FIELD_INVALID]:  'text-red-400',
  }[state] ?? 'text-muted';
  return <p className={`text-[11px] mt-1 ${colorClass}`}>{message}</p>;
}

export default function RegisterPage() {
  const [form,    setForm]    = useState(EMPTY);
  const [error,   setError]   = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const [emailState, setEmailState] = useState({ state: FIELD_IDLE, message: '' });
  const [cnicState,  setCnicState]  = useState({ state: FIELD_IDLE, message: '' });

  // Debounce timers + "last checked" values so we can short-circuit
  // the request when the user re-blurs an unchanged field.
  const emailTimer = useRef(null);
  const cnicTimer  = useRef(null);
  const lastEmailChecked = useRef('');
  const lastCnicChecked  = useRef('');

  const navigate = useNavigate();

  const set = (k) => (e) => {
    setError('');
    setForm((f) => ({ ...f, [k]: e.target.value }));
    // Reset the status indicator as soon as the user edits the field;
    // the next onBlur (or debounce) will re-run the check.
    if (k === 'email') setEmailState({ state: FIELD_IDLE, message: '' });
    if (k === 'cnic')  setCnicState({ state: FIELD_IDLE, message: '' });
  };

  // ── Availability checkers ──────────────────────────────────────────────────
  async function runEmailCheck(value) {
    const v = (value ?? '').trim().toLowerCase();
    if (!v) { setEmailState({ state: FIELD_IDLE, message: '' }); return; }
    if (!EMAIL_RE.test(v)) {
      setEmailState({ state: FIELD_INVALID, message: 'Invalid email format.' });
      return;
    }
    if (v === lastEmailChecked.current) return;
    lastEmailChecked.current = v;
    setEmailState({ state: FIELD_CHECKING, message: 'Checking availability…' });
    try {
      const { data } = await checkEmail(v);
      if (!data.valid_format) setEmailState({ state: FIELD_INVALID, message: data.reason });
      else if (data.available) setEmailState({ state: FIELD_OK, message: 'Email is available.' });
      else setEmailState({ state: FIELD_TAKEN, message: data.reason || 'Email already registered.' });
    } catch {
      // Silent fallback — the server will still reject duplicates on submit.
      setEmailState({ state: FIELD_IDLE, message: '' });
      lastEmailChecked.current = '';
    }
  }

  async function runCnicCheck(value) {
    const v = (value ?? '').replace(/[-\s]/g, '');
    if (!v) { setCnicState({ state: FIELD_IDLE, message: '' }); return; }
    if (!CNIC_RE.test(v)) {
      setCnicState({ state: FIELD_INVALID, message: 'CNIC must be exactly 13 digits.' });
      return;
    }
    if (v === lastCnicChecked.current) return;
    lastCnicChecked.current = v;
    setCnicState({ state: FIELD_CHECKING, message: 'Checking availability…' });
    try {
      const { data } = await checkCnic(v);
      if (!data.valid_format) setCnicState({ state: FIELD_INVALID, message: data.reason });
      else if (data.available) setCnicState({ state: FIELD_OK, message: 'CNIC is available.' });
      else setCnicState({ state: FIELD_TAKEN, message: data.reason || 'CNIC already registered.' });
    } catch {
      setCnicState({ state: FIELD_IDLE, message: '' });
      lastCnicChecked.current = '';
    }
  }

  // Debounced checks as the user types (600ms after last keystroke).
  useEffect(() => {
    clearTimeout(emailTimer.current);
    if (!form.email) return;
    emailTimer.current = setTimeout(() => runEmailCheck(form.email), 600);
    return () => clearTimeout(emailTimer.current);

  }, [form.email]);

  useEffect(() => {
    clearTimeout(cnicTimer.current);
    if (!form.cnic) return;
    cnicTimer.current = setTimeout(() => runCnicCheck(form.cnic), 600);
    return () => clearTimeout(cnicTimer.current);

  }, [form.cnic]);

  // onBlur — fire immediately without waiting for debounce.
  const handleEmailBlur = () => { clearTimeout(emailTimer.current); runEmailCheck(form.email); };
  const handleCnicBlur  = () => { clearTimeout(cnicTimer.current);  runCnicCheck(form.cnic); };

  // Submit is blocked while either field is still checking or has a known error.
  const canSubmit =
    !loading &&
    emailState.state !== FIELD_CHECKING &&
    cnicState.state  !== FIELD_CHECKING &&
    emailState.state !== FIELD_TAKEN &&
    emailState.state !== FIELD_INVALID &&
    cnicState.state  !== FIELD_TAKEN &&
    cnicState.state  !== FIELD_INVALID;

  async function handleSubmit(e) {
    e.preventDefault();
    if (form.password !== form.confirm) { setError("Passwords don't match."); return; }
    // Force a final sync check if the user typed quickly and blurred before debounce.
    await Promise.all([runEmailCheck(form.email), runCnicCheck(form.cnic)]);
    if (!canSubmit) return;

    setLoading(true);
    try {
      const { full_name, email, cnic, role, city, password } = form;
      await register({ full_name, email, cnic, role, city, password, confirm_password: form.confirm });
      setSuccess(true);
    } catch (err) {
      const d = err.response?.data;
      setError(d?.detail ?? d?.email?.[0] ?? d?.cnic?.[0] ?? d?.password?.[0] ?? err.message ?? 'Registration failed.');
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
            <div className="form-row">
              <label>Email *</label>
              <input type="email" placeholder="you@example.com"
                     value={form.email} onChange={set('email')} onBlur={handleEmailBlur} required />
              <FieldStatus state={emailState.state} message={emailState.message} />
            </div>
            <div className="form-row">
              <label>CNIC *</label>
              <input placeholder="4200012345678" inputMode="numeric" maxLength={13}
                     value={form.cnic} onChange={set('cnic')} onBlur={handleCnicBlur} required />
              <FieldStatus state={cnicState.state} message={cnicState.message} />
            </div>
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
            <div className="form-row">
              <label>Password *</label>
              <PasswordInput placeholder="Min 8 chars" value={form.password} onChange={set('password')} minLength={8} required />
            </div>
            <div className="form-row">
              <label>Confirm *</label>
              <PasswordInput placeholder="Repeat" value={form.confirm} onChange={set('confirm')} minLength={8} required />
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
