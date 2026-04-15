import { useState } from 'react';
import { addBike } from '../../api/bikeApi';
import { Alert, Button } from '../UI';

const EMPTY = {
  make: '', model: '', year: '', color: '',
  engine_number: '', chassis_number: '',
  registration_number: '', registration_city: '',
};

export default function BikeForm({ onSuccess, onCancel }) {
  const [form,   setForm]   = useState(EMPTY);
  const [error,  setError]  = useState('');
  const [saving, setSaving] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await addBike({ ...form, year: form.year ? parseInt(form.year) : undefined });
      onSuccess?.();
    } catch (err) {
      const data = err.response?.data;
      const msg  = typeof data === 'object'
        ? Object.values(data).flat().join(' ')
        : (data ?? err.message ?? 'Failed to register bike.');
      setError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <Alert type="error" message={error} onClose={() => setError('')} />

      <div className="grid grid-cols-2 gap-x-3">
        <div className="form-row"><label>Make / Brand *</label><input placeholder="Honda" value={form.make} onChange={set('make')} required /></div>
        <div className="form-row"><label>Model *</label><input placeholder="CD 70" value={form.model} onChange={set('model')} required /></div>
      </div>

      <div className="grid grid-cols-2 gap-x-3">
        <div className="form-row"><label>Year *</label><input type="number" placeholder="2021" min="1900" max="2100" value={form.year} onChange={set('year')} required /></div>
        <div className="form-row"><label>Color</label><input placeholder="Black" value={form.color} onChange={set('color')} /></div>
      </div>

      <div className="form-row">
        <label>Engine Number *</label>
        <input placeholder="HC12A-123456" value={form.engine_number} onChange={set('engine_number')} required />
      </div>
      <div className="form-row">
        <label>Chassis Number *</label>
        <input placeholder="MH-CY-123456" value={form.chassis_number} onChange={set('chassis_number')} required />
      </div>

      <div className="grid grid-cols-2 gap-x-3">
        <div className="form-row"><label>Plate Number</label><input placeholder="ABC-123" value={form.registration_number} onChange={set('registration_number')} /></div>
        <div className="form-row"><label>Registration City</label><input placeholder="Karachi" value={form.registration_city} onChange={set('registration_city')} /></div>
      </div>

      <div className="flex justify-end gap-2 mt-2">
        <Button onClick={onCancel}>Cancel</Button>
        <Button variant="primary" type="submit" loading={saving}>Register Bike</Button>
      </div>
    </form>
  );
}
