import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { resetPassword } from '../../api/authApi';
import { Alert, Button } from '../../components/UI';

export default function ResetPasswordPage() {
  const { token } = useParams();
  const navigate   = useNavigate();
  const [form,    setForm]    = useState({ password: '', confirm: '' });
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function handleSubmit(e) {
    e.preventDefault();
    if (form.password !== form.confirm) { setError("Passwords don't match."); return; }
    setLoading(true);
    try { await resetPassword(token, { password: form.password }); navigate('/login'); }
    catch (err) { setError(err.response?.data?.detail ?? err.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="w-[380px]">
      <div className="card">
        <h2 className="font-heading font-semibold text-base text-gray-100 mb-5">Set new password</h2>
        <Alert type="error" message={error} onClose={() => setError('')} />
        <form onSubmit={handleSubmit}>
          <div className="form-row"><label>New Password</label><input type="password" placeholder="Min 8 chars" value={form.password} onChange={set('password')} required /></div>
          <div className="form-row"><label>Confirm</label><input type="password" placeholder="Repeat" value={form.confirm} onChange={set('confirm')} required /></div>
          <Button variant="primary" type="submit" loading={loading} className="w-full justify-center">Reset Password</Button>
        </form>
      </div>
    </div>
  );
}
