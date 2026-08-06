import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { resetPassword } from '../api';
import { useForm } from '@/shared/hooks/useForm';
import { apiErrorMessage } from '@/shared/lib/http';
import { Alert, Button, PasswordInput } from '@/shared/components/ui';

export default function ResetPasswordPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { values: form, set } = useForm({ password: '', confirm: '' });
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    if (form.password !== form.confirm) { setError("Passwords don't match."); return; }
    setLoading(true);
    setError('');
    try {
      await resetPassword(token, { new_password: form.password, confirm_password: form.confirm });
      navigate('/login');
    } catch (err) {
      setError(apiErrorMessage(err, 'Password reset failed.'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-[380px]">
      <div className="card">
        <h2 className="font-heading font-semibold text-base text-gray-100 mb-5">Set new password</h2>
        <Alert type="error" message={error} onClose={() => setError('')} />
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <label>New Password</label>
            <PasswordInput placeholder="Min 8 chars" value={form.password} onChange={set('password')} minLength={8} required />
          </div>
          <div className="form-row">
            <label>Confirm</label>
            <PasswordInput placeholder="Repeat" value={form.confirm} onChange={set('confirm')} minLength={8} required />
          </div>
          <Button variant="primary" type="submit" loading={loading} className="w-full justify-center">Reset Password</Button>
        </form>
      </div>
    </div>
  );
}
