import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { getUsers, createAuthority, updateUserStatus } from '../../api/adminApi';
import { Button, Modal, Badge, Alert, EmptyState, Spinner } from '../../components/UI';
import { ROLE_COLORS, ROLE_LABELS } from '../../utils/constants';

const EMPTY_AUTH = { full_name: '', email: '', cnic: '', badge_number: '', city: '', password: '' };

export default function UsersPage() {
  const { data, loading, refetch } = useFetch(getUsers, []);
  const users = data?.results ?? data ?? [];

  const [showAdd, setShowAdd] = useState(false);
  const [form,    setForm]    = useState(EMPTY_AUTH);
  const [error,   setError]   = useState('');
  const [saving,  setSaving]  = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function handleCreate(e) {
    e.preventDefault(); setSaving(true); setError('');
    try {
      await createAuthority(form);
      setShowAdd(false); setForm(EMPTY_AUTH); refetch();
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
        <Button variant="primary" onClick={() => { setShowAdd(true); setError(''); setForm(EMPTY_AUTH); }}>+ Add Authority</Button>
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
        <Modal title="Create Authority Account" onClose={() => setShowAdd(false)}>
          <form onSubmit={handleCreate}>
            <Alert type="error" message={error} onClose={() => setError('')} />
            <div className="form-row"><label>Full Name *</label><input placeholder="Inspector Ali Khan" value={form.full_name} onChange={set('full_name')} required /></div>
            <div className="form-row"><label>Email *</label><input type="email" value={form.email} onChange={set('email')} required /></div>
            <div className="grid grid-cols-2 gap-x-3">
              <div className="form-row"><label>Badge Number *</label><input placeholder="KHI-0042" value={form.badge_number} onChange={set('badge_number')} required /></div>
              <div className="form-row"><label>CNIC *</label><input placeholder="4210100000001" value={form.cnic} onChange={set('cnic')} required /></div>
            </div>
            <div className="form-row"><label>City *</label><input placeholder="Karachi" value={form.city} onChange={set('city')} required /></div>
            <div className="form-row"><label>Password *</label><input type="password" value={form.password} onChange={set('password')} required /></div>
            <div className="flex justify-end gap-2 mt-2">
              <Button onClick={() => setShowAdd(false)}>Cancel</Button>
              <Button variant="primary" type="submit" loading={saving}>Create Authority</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
