import { useMemo, useState } from 'react';
import { useList } from '@/shared/hooks/useFetch';
import { getReports, getReport, updateStatus, logRecovery } from '../api';
import CaseTimeline from '../components/CaseTimeline';
import PageHeader from '@/shared/components/layout/PageHeader';
import DataTable from '@/shared/components/data/DataTable';
import DetailList from '@/shared/components/data/DetailList';
import { Alert, Badge, Button, Modal, Spinner } from '@/shared/components/ui';
import {
  STATUS_TRANSITIONS, canLogRecovery, isAwaitingOwner, statusColor, statusLabel,
} from '@/shared/lib/reportStatus';
import { useForm } from '@/shared/hooks/useForm';
import { apiErrorMessage } from '@/shared/lib/http';
import { formatDate } from '@/shared/lib/formatters';

const EMPTY_REC = { recovery_city: '', recovery_date: '', bike_condition: 'good', notes: '' };

const BIKE_CONDITIONS = [
  { value: 'good',     label: 'Good — no damage' },
  { value: 'damaged',  label: 'Damaged' },
  { value: 'stripped', label: 'Stripped — parts removed' },
  { value: 'burnt',    label: 'Burnt' },
];

export default function CaseReportsPage() {
  const { items: reports, loading, refetch } = useList(getReports, []);

  const [detail,        setDetail]        = useState(null);
  const [recovering,    setRecovering]    = useState(false);
  const [error,         setError]         = useState('');
  const [recError,      setRecError]      = useState('');
  const [saving,        setSaving]        = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const { values: recForm, set: setRec, reset: resetRec } = useForm(EMPTY_REC);

  async function openDetail(row) {
    setLoadingDetail(true);
    try {
      const { data } = await getReport(row.id);
      setDetail(data);
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to open report.'));
    } finally {
      setLoadingDetail(false);
    }
  }

  async function advance(id, nextStatus) {
    try {
      await updateStatus(id, nextStatus);
      refetch();
      setDetail(null);
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to advance case.'));
    }
  }

  function closeRecovery() {
    setRecovering(false);
    setRecError('');
    resetRec();
  }

  async function handleLogRecovery(e) {
    e.preventDefault();
    setSaving(true);
    setRecError('');
    try {
      await logRecovery(detail.id, recForm);
      closeRecovery();
      setDetail(null);
      refetch();
    } catch (err) {
      setRecError(apiErrorMessage(err, 'Failed to log recovery.'));
    } finally {
      setSaving(false);
    }
  }

  const columns = useMemo(() => [
    { key: 'id',         label: 'ID',       render: (v) => <span className="mono text-primary">#{v}</span> },
    { key: 'bike_info',  label: 'Engine #', render: (v) => <span className="mono">{v?.engine_number ?? '—'}</span> },
    { key: 'status',     label: 'Status',   render: (v) => <Badge variant={statusColor(v)}>{statusLabel(v)}</Badge> },
    { key: 'theft_city', label: 'City',     render: (v) => <span className="text-muted">{v ?? '—'}</span> },
    { key: 'created_at', label: 'Filed',    render: (v) => <span className="text-faint text-xs">{formatDate(v)}</span> },
    {
      key: 'actions',
      label: '',
      render: (_, row) => {
        const next = STATUS_TRANSITIONS[row.status];
        if (!next) return null;
        return (
          <Button variant="blue" size="sm" onClick={(e) => { e.stopPropagation(); advance(row.id, next); }}>
            → {statusLabel(next)}
          </Button>
        );
      },
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], []);

  const nextStatus = detail ? STATUS_TRANSITIONS[detail.status] : undefined;

  return (
    <div>
      <PageHeader title="Case Reports" subtitle="Manage and advance theft cases in your city" />

      <Alert type="error" message={error} onClose={() => setError('')} />

      <DataTable
        columns={columns}
        rows={reports}
        loading={loading}
        emptyIcon="📋"
        emptyTitle="No reports in your city"
        onRowClick={openDetail}
      />
      {loadingDetail && <Spinner />}

      {detail && !recovering && (
        <Modal title={`Report #${detail.id} — ${detail.reference_number ?? ''}`} onClose={() => setDetail(null)}>
          <div className="flex gap-2 flex-wrap mb-4">
            <Badge variant={statusColor(detail.status)}>{statusLabel(detail.status)}</Badge>
          </div>

          <DetailList
            className="mb-5"
            rows={[
              ['City',        detail.theft_city],
              ['Theft Date',  formatDate(detail.theft_date)],
              ['Filed',       formatDate(detail.created_at)],
              ['Location',    detail.theft_location_detail],
              ['Description', detail.description],
            ]}
          />

          <div className="flex gap-2 flex-wrap">
            {nextStatus && (
              <Button variant="blue" onClick={() => advance(detail.id, nextStatus)}>
                → Advance to {statusLabel(nextStatus)}
              </Button>
            )}
            {canLogRecovery(detail.status) && (
              <Button variant="green" onClick={() => setRecovering(true)}>📍 Log Recovery</Button>
            )}
          </div>

          {isAwaitingOwner(detail.status) && (
            <div className="mt-4 px-3 py-2 rounded bg-amber-400/10 border border-amber-400/30 text-xs text-amber-300">
              ⏳ Awaiting owner confirmation — the bike owner must confirm receipt to close this case.
              If the owner is unresponsive, an admin can close it on their behalf.
            </div>
          )}

          <CaseTimeline events={detail.timeline ?? []} />
        </Modal>
      )}

      {detail && recovering && (
        <Modal title="Log Recovery" onClose={closeRecovery}>
          <form onSubmit={handleLogRecovery}>
            <Alert type="error" message={recError} onClose={() => setRecError('')} />

            <div className="grid grid-cols-2 gap-x-3">
              <div className="form-row"><label>Recovery City *</label><input placeholder="Karachi" value={recForm.recovery_city} onChange={setRec('recovery_city')} required /></div>
              <div className="form-row"><label>Recovery Date *</label><input type="date" value={recForm.recovery_date} onChange={setRec('recovery_date')} required /></div>
            </div>

            <div className="form-row">
              <label>Bike Condition</label>
              <select value={recForm.bike_condition} onChange={setRec('bike_condition')}>
                {BIKE_CONDITIONS.map(({ value, label }) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>

            <div className="form-row">
              <label>Notes</label>
              <textarea placeholder="Condition of bike, where found, who reported it…" value={recForm.notes} onChange={setRec('notes')} />
            </div>

            <div className="flex justify-end gap-2 mt-2">
              <Button onClick={closeRecovery}>Cancel</Button>
              <Button variant="green" type="submit" loading={saving}>Log Recovery</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
