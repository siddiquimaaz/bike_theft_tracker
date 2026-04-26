import { useState, useEffect } from 'react';
import { fileReport } from '../../api/reportApi';
import { getBikes }   from '../../api/bikeApi';
import { Alert, Button } from '../UI';

export default function ReportForm({ onSuccess, onCancel, initialBikeId = '' }) {
  const [form,   setForm]   = useState({
    bike: initialBikeId ? String(initialBikeId) : '',
    theft_city: '', theft_date: '',
    theft_location_detail: '', description: '',
  });
  const [bikes,  setBikes]  = useState([]);
  const [error,  setError]  = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getBikes().then(({ data }) => setBikes(data?.results ?? data ?? [])).catch(() => {});
  }, []);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await fileReport({ ...form, bike: parseInt(form.bike) });
      onSuccess?.();
    } catch (err) {
      const data = err.response?.data;
      const msg  = typeof data === 'object'
        ? Object.values(data).flat().join(' ')
        : (data ?? err.message ?? 'Failed to file report.');
      setError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <Alert type="error" message={error} onClose={() => setError('')} />

      <div className="form-row">
        <label>Bike *</label>
        <select value={form.bike} onChange={set('bike')} required>
          <option value="">Select your bike…</option>
          {bikes.map((b) => (
            <option key={b.id} value={b.id}>
              {b.make} {b.model} — {b.chassis_number ?? b.engine_number}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-x-3">
        <div className="form-row"><label>City where stolen *</label><input placeholder="Karachi" value={form.theft_city} onChange={set('theft_city')} required /></div>
        <div className="form-row"><label>Theft Date *</label><input type="date" value={form.theft_date} onChange={set('theft_date')} required /></div>
      </div>

      <div className="form-row"><label>Location detail</label><textarea placeholder="Near Tariq Road, outside shop…" value={form.theft_location_detail} onChange={set('theft_location_detail')} /></div>
      <div className="form-row"><label>Additional details</label><textarea placeholder="Any extra info about the theft…" value={form.description} onChange={set('description')} /></div>

      <div className="flex justify-end gap-2 mt-2">
        <Button onClick={onCancel}>Cancel</Button>
        <Button variant="primary" type="submit" loading={saving}>File Report</Button>
      </div>
    </form>
  );
}
