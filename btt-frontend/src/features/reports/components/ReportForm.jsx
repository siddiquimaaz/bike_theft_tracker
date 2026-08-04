import { useState } from 'react';
import { fileReport } from '../api';
import { getBikes } from '@/features/bikes/api';
import { useList } from '@/shared/hooks/useFetch';
import { useForm } from '@/shared/hooks/useForm';
import { apiErrorMessage } from '@/shared/lib/http';
import { Alert, Button } from '@/shared/components/ui';

export default function ReportForm({ onSuccess, onCancel, initialBikeId = '' }) {
  const { values: form, set } = useForm({
    bike: initialBikeId ? String(initialBikeId) : '',
    theft_city: '', theft_date: '',
    theft_location_detail: '', description: '',
  });

  const { items: bikes } = useList(getBikes, []);
  const [error,  setError]  = useState('');
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await fileReport({ ...form, bike: parseInt(form.bike, 10) });
      onSuccess?.();
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to file report.'));
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
