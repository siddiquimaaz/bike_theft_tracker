import { useState } from 'react';
import { useList } from '@/shared/hooks/useFetch';
import { getUsers, createAuthority, updateUserStatus } from '../api';
import { useEmailAvailability, useCnicAvailability } from '@/features/auth/useAvailabilityCheck';
import FieldStatus from '@/features/auth/components/FieldStatus';
import PageHeader from '@/shared/components/layout/PageHeader';
import { useForm } from '@/shared/hooks/useForm';
import { apiErrorMessage } from '@/shared/lib/http';
import { ROLE_COLORS, ROLE_LABELS } from '@/shared/lib/constants';
import { Alert, Badge, Button, Modal, EmptyState, Spinner, PasswordInput } from '@/shared/components/ui';

const EMPTY_AUTH = { full_name: '', email: '', cnic: '', badge_number: '', city: '', password: '' };

export default function UsersPage() {
  const { items: users, loading, refetch } = useList(getUsers, []);

  const { values: form, set, setValue, reset } = useForm(EMPTY_AUTH);
  const [showAdd, setShowAdd] = useState(false);
  const [error,   setError]   = useState('');
  const [saving,  setSaving]  = useState(false);

  const email = useEmailAvailability(form.email);
  const cnic  = useCnicAvailability(form.cnic);

  // Reset the indicator the moment the field is edited; the debounce (or the
  // next blur) re-runs the check.
  const setEmail = (e) => { email.clear(); setValue('email', e.target.value); };
  const setCnic  = (e) => { cnic.clear();  setValue('cnic',  e.target.value); };

  const canSubmit = !saving && !email.blocksSubmit && !cnic.blocksSubmit;

  function resetModalState() {
    reset();
    setError('');
    email.reset();
    cnic.reset();
  }

  function closeModal() {
    setShowAdd(false);
    resetModalState();
  }

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    // Force a final sync check — catches fast submits before debounce fires.
    await Promise.all([email.verify(), cnic.verify()]);
    if (!canSubmit) { setSaving(false); return; }

    try {
      await createAuthority(form);
      closeModal();
      refetch();
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to create authority.'));
    } finally {
      setSaving(false);
    }
  }

  async function toggleStatus(id, isActive) {
    try {
      // Send the new desired state (opposite of current)
      await updateUserStatus(id, !isActive);
      refetch();
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to update user status.'));
    }
  }

  return (
    <div>
      <PageHeader
        title="User Management"
        subtitle="All registered system users"
        action={<Button variant="primary" onClick={() => { resetModalState(); setShowAdd(true); }}>+ Add Authority</Button>}
      />

      {!showAdd && <Alert type="error" message={error} onClose={() => setError('')} />}

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
        <Modal title="Create Authority Account" onClose={closeModal}>
          <form onSubmit={handleCreate}>
            <Alert type="error" message={error} onClose={() => setError('')} />

            <div className="form-row">
              <label>Full Name *</label>
              <input placeholder="Inspector Ali Khan" value={form.full_name} onChange={set('full_name')} required />
            </div>

            <div className="form-row">
              <label>Email *</label>
              <input type="email" value={form.email} onChange={setEmail} onBlur={email.onBlur} required />
              <FieldStatus state={email.state} message={email.message} />
            </div>

            <div className="grid grid-cols-2 gap-x-3">
              <div className="form-row">
                <label>Badge Number *</label>
                <input placeholder="KHI-0042" value={form.badge_number} onChange={set('badge_number')} required />
              </div>
              <div className="form-row">
                <label>CNIC *</label>
                <input placeholder="4210100000001" inputMode="numeric" maxLength={13}
                       value={form.cnic} onChange={setCnic} onBlur={cnic.onBlur} required />
                <FieldStatus state={cnic.state} message={cnic.message} />
              </div>
            </div>

            <div className="form-row">
              <label>City *</label>
              <input placeholder="Karachi" value={form.city} onChange={set('city')} required />
            </div>

            <div className="form-row">
              <label>Password *</label>
              <PasswordInput value={form.password} onChange={set('password')} minLength={8} required />
            </div>

            <div className="flex justify-end gap-2 mt-2">
              <Button onClick={closeModal}>Cancel</Button>
              <Button variant="primary" type="submit" loading={saving} disabled={!canSubmit}>Create Authority</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
