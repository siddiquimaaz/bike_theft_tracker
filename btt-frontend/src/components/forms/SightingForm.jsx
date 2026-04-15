import { useState } from 'react';
import { submitSighting } from '../../api/sightingApi';
import { Alert, Button } from '../UI';

export default function SightingForm({ onSuccess, onCancel }) {
  const [form,   setForm]   = useState({
    raw_engine_number: '', raw_chassis_number: '',
    sighting_city: '', sighting_date: '', sighting_description: '',
  });
  const [error,  setError]  = useState('');
  const [saving, setSaving] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.raw_engine_number && !form.raw_chassis_number) {
      setError('Provide at least a partial engine or chassis number.');
      return;
    }
    if (!form.sighting_date) {
      setError('Sighting date is required.');
      return;
    }
    setSaving(true); setError('');
    try {
      await submitSighting(form);
      onSuccess?.();
    } catch (err) {
      const data = err.response?.data;
      const msg  = typeof data === 'object'
        ? Object.values(data).flat().join(' ')
        : (data ?? err.message ?? 'Failed to submit sighting.');
      setError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <Alert type="info"  message="Partial numbers are OK — our AI fuzzy-match will find the best candidates." />
      <Alert type="error" message={error} onClose={() => setError('')} />

      <div className="form-row"><label>Partial Engine Number</label><input placeholder="HC12A-1234" value={form.raw_engine_number} onChange={set('raw_engine_number')} /></div>
      <div className="form-row"><label>Partial Chassis Number</label><input placeholder="MH-CY-12" value={form.raw_chassis_number} onChange={set('raw_chassis_number')} /></div>

      <div className="grid grid-cols-2 gap-x-3">
        <div className="form-row"><label>City *</label><input placeholder="Karachi" value={form.sighting_city} onChange={set('sighting_city')} required /></div>
        <div className="form-row"><label>Date spotted *</label><input type="date" value={form.sighting_date} onChange={set('sighting_date')} required /></div>
      </div>

      <div className="form-row"><label>Description / Location</label><textarea placeholder="Saddar Market, near Empress Market. Bike color, rider description…" value={form.sighting_description} onChange={set('sighting_description')} /></div>

      <div className="flex justify-end gap-2 mt-2">
        {onCancel && <Button onClick={onCancel}>Cancel</Button>}
        <Button variant="primary" type="submit" loading={saving}>Submit Sighting</Button>
      </div>
    </form>
  );
}
