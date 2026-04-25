import { useState, useRef, useEffect } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { getUsers, createAuthority, updateUserStatus } from '../../api/adminApi';
import { checkEmail, checkCnic } from '../../api/authApi';
import { Button, Modal, Badge, Alert, EmptyState, Spinner, PasswordInput } from '../../components/UI';
import { ROLE_COLORS, ROLE_LABELS } from '../../utils/constants';

const EMPTY_AUTH = { full_name: '', email: '', cnic: '', badge_number: '', city: '', password: '' };

// Inline-validation states (shared shape with RegisterPage).
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

export default function UsersPage() {
  const { data, loading, refetch } = useFetch(getUsers, []);
  const users = data?.results ?? data ?? [];

  const [showAdd, setShowAdd] = useState(false);
  const [form,    setForm]    = useState(EMPTY_AUTH);
  const [error,   setError]   = useState('');
  const [saving,  setSaving]  = useState(false);

  // Availability-check state (mirrors RegisterPage).
  const [emailState, setEmailState] = useState({ state: FIELD_IDLE, message: '' });
  const [cnicState,  setCnicState]  = useState({ state: FIELD_IDLE, message: '' });
  const emailTimer = useRef(null);
  const cnicTimer  = useRef(null);
  const lastEmailChecked = useRef('');
  const lastCnicChecked  = useRef('');

  const set = (k) => (e) => {
    setForm((f) => ({ ...f, [k]: e.target.value }));
    if (k === 'email') setEmailState({ state: FIELD_IDLE, message: '' });
    if (k === 'cnic')  setCnicState({ state: FIELD_IDLE, message: '' });
  };

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

  // Debounced type-while-you-edit checks.
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

  const handleEmailBlur = () => { clearTimeout(emailTimer.current); runEmailCheck(form.email); };
  const handleCnicBlur  = () => { clearTimeout(cnicTimer.current);  runCnicCheck(form.cnic); };

  const canSubmit =
    !saving &&
    emailState.state !== FIELD_CHECKING &&
    cnicState.state  !== FIELD_CHECKING &&
    emailState.state !== FIELD_TAKEN &&
    emailState.state !== FIELD_INVALID &&
    cnicState.state  !== FIELD_TAKEN &&
    cnicState.state  !== FIELD_INVALID;

  function resetModalState() {
    setForm(EMPTY_AUTH);
    setError('');
    setEmailState({ state: FIELD_IDLE, message: '' });
    setCnicState({ state: FIELD_IDLE, message: '' });
    lastEmailChecked.current = '';
    lastCnicChecked.current = '';
  }

  async function handleCreate(e) {
    e.preventDefault(); setSaving(true); setError('');
    // Force a final sync check — catches fast submits before debounce fires.
    await Promise.all([runEmailCheck(form.email), runCnicCheck(form.cnic)]);
    if (!canSubmit) { setSaving(false); return; }
    try {
      await createAuthority(form);
      setShowAdd(false);
      resetModalState();
      refetch();
    } catch (err) {
      const data = err.response?.data;
      const msg  = typeof data === 'object'
        ? Object.values(data).flat().join(' ')
        : (data ?? err.message ?? 'Failed to create authority.');
      setError(msg);
    } finally { setSaving(false); }
  }

  async function toggleStatus(id, isActive) {
    try {
      // Send the new desired state (opposite of current)
      await updateUserStatus(id, !isActive);
      refetch();
    } catch (err) { alert(err.response?.data?.detail ?? err.message); }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div><h1 className="page-title">User Management</h1><p className="page-sub m-0">All registered system users</p></div>
        <Button variant="primary" onClick={() => { setShowAdd(true); resetModalState(); }}>+ Add Authority</Button>
      </div>

      {loading ? <Spinner /> : (
        <div className="card p-0 overflow-hidden">
          {users.length === 0
            ? <EmptyState icon="👥" title="No users found" />
            : (
              <table className="tbl">
                <thead className="bg-btt-700"><tr>
                  <th>Name</th><th>Email</th><th>Role</th><th>City</th><th>Status</th><th>Actions</th>
                </tr></thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td className="font-medium">{u.full_name ?? '—'}</td>
                      <td className="text-muted text-xs">{u.email}</td>
                      <td><Badge variant={ROLE_COLORS[u.role] ?? 'gray'}>{ROLE_LABELS[u.role] ?? u.role}</Badge></td>
                      <td className="text-muted">{u.city ?? '—'}</td>
                      <td><Badge variant={u.is_active ? 'green' : 'red'}>{u.is_active ? 'Active' : 'Inactive'}</Badge></td>
                      <td>
                        <Button
                          variant={u.is_active ? 'danger' : 'green'}
                          size="sm"
                          onClick={() => toggleStatus(u.id, u.is_active)}
                        >
                          {u.is_active ? 'Deactivate' : 'Activate'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>
      )}

      {showAdd && (
        <Modal title="Create Authority Account" onClose={() => { setShowAdd(false); resetModalState(); }}>
          <form onSubmit={handleCreate}>
            <Alert type="error" message={error} onClose={() => setError('')} />
            <div className="form-row"><label>Full Name *</label><input placeholder="Inspector Ali Khan" value={form.full_name} onChange={set('full_name')} required /></div>
            <div className="form-row">
              <label>Email *</label>
              <input type="email" value={form.email} onChange={set('email')} onBlur={handleEmailBlur} required />
              <FieldStatus state={emailState.state} message={emailState.message} />
            </div>
            <div className="grid grid-cols-2 gap-x-3">
              <div className="form-row"><label>Badge Number *</label><input placeholder="KHI-0042" value={form.badge_number} onChange={set('badge_number')} required /></div>
              <div className="form-row">
                <label>CNIC *</label>
                <input placeholder="4210100000001" inputMode="numeric" maxLength={13}
                       value={form.cnic} onChange={set('cnic')} onBlur={handleCnicBlur} required />
                <FieldStatus state={cnicState.state} message={cnicState.message} />
              </div>
            </div>
            <div className="form-row"><label>City *</label><input placeholder="Karachi" value={form.city} onChange={set('city')} required /></div>
            <div className="form-row">
              <label>Password *</label>
              <PasswordInput value={form.password} onChange={set('password')} minLength={8} required />
            </div>
            <div className="flex justify-end gap-2 mt-2">
              <Button onClick={() => { setShowAdd(false); resetModalState(); }}>Cancel</Button>
              <Button variant="primary" type="submit" loading={saving} disabled={!canSubmit}>Create Authority</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
