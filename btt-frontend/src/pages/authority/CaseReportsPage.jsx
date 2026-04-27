import { useState } from 'react';
import { useFetch }                  from '../../hooks/useFetch';
import { getReports, getReport, updateStatus, logRecovery } from '../../api/reportApi';
import { Badge, Button, Modal, Spinner, Alert } from '../../components/UI';
import DataTable from '../../components/tables/DataTable';
import { STATUS_COLORS, STATUS_LABELS, STATUS_TRANSITIONS } from '../../utils/constants';
import { formatDate } from '../../utils/formatters';
import CaseTimeline from '../../components/timeline/CaseTimeline';

const EMPTY_REC = { recovery_city: '', recovery_date: '', bike_condition: 'good', notes: '' };

export default function CaseReportsPage() {
  const { data, loading, refetch } = useFetch(getReports, []);
  const reports = data?.results ?? data ?? [];

  const [detail,     setDetail]     = useState(null);
  const [recovering, setRecovering] = useState(false);
  const [recForm,    setRecForm]    = useState(EMPTY_REC);
  const [recError,   setRecError]   = useState('');
  const [saving,     setSaving]     = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  async function openDetail(row) {
    setLoadingDetail(true);
    try {
      const { data } = await getReport(row.id);
      setDetail(data);
    } finally {
      setLoadingDetail(false);
    }
  }

  async function advance(id, nextStatus) {
    try { await updateStatus(id, nextStatus); refetch(); setDetail(null); }
    catch (err) { alert(err.response?.data?.detail ?? err.message); }
  }

  async function handleLogRecovery(e) {
    e.preventDefault(); setSaving(true); setRecError('');
    try {
      await logRecovery(detail.id, recForm);
      setRecovering(false); setDetail(null); setRecForm(EMPTY_REC); refetch();
    } catch (err) {
      const data = err.response?.data;
      const msg  = typeof data === 'object' ? Object.values(data).flat().join(' ') : (err.message ?? 'Failed.');
      setRecError(msg);
    } finally { setSaving(false); }
  }

  const columns = [
    { key: 'id',       label: 'ID',      render: (v) => <span className="mono text-primary">#{v}</span> },
    { key: 'bike_info', label: 'Engine #', render: (v) => <span className="mono">{v?.engine_number ?? '—'}</span> },
    { key: 'status',   label: 'Status',  render: (v) => <Badge variant={STATUS_COLORS[v] ?? 'gray'}>{STATUS_LABELS[v] ?? v}</Badge> },
    { key: 'theft_city', label: 'City',  render: (v) => <span className="text-muted">{v ?? '—'}</span> },
    { key: 'created_at', label: 'Filed', render: (v) => <span className="text-faint text-xs">{formatDate(v)}</span> },
    { key: 'actions', label: '', render: (_, row) => {
      const next = STATUS_TRANSITIONS[row.status];
      return next ? (
        <Button variant="blue" size="sm" onClick={(e) => { e.stopPropagation(); advance(row.id, next); }}>
          → {STATUS_LABELS[next] ?? next}
        </Button>
      ) : null;
    }},
  ];

  return (
    <div>
      <h1 className="page-title">Case Reports</h1>
      <p className="page-sub">Manage and advance theft cases in your city</p>

      <DataTable columns={columns} rows={reports} loading={loading} emptyIcon="📋" emptyTitle="No reports in your city" onRowClick={openDetail} />
      {loadingDetail && <Spinner />}

      {detail && !recovering && (
        <Modal title={`Report #${detail.id} — ${detail.reference_number ?? ''}`} onClose={() => setDetail(null)}>
          <div className="flex gap-2 flex-wrap mb-4">
            <Badge variant={STATUS_COLORS[detail.status] ?? 'gray'}>{STATUS_LABELS[detail.status] ?? detail.status}</Badge>
          </div>
          <table className="tbl mb-5">
            <tbody>
              {[
                ['City',       detail.theft_city],
                ['Theft Date', formatDate(detail.theft_date)],
                ['Filed',      formatDate(detail.created_at)],
                ['Location',   detail.theft_location_detail],
                ['Description',detail.description],
              ].filter(([, v]) => v).map(([k, v]) => (
                <tr key={k}><td className="text-faint text-xs w-28 border-none py-1">{k}</td><td className="text-sm text-gray-100 border-none py-1">{v}</td></tr>
              ))}
            </tbody>
          </table>
          <div className="flex gap-2 flex-wrap">
            {STATUS_TRANSITIONS[detail.status] && (
              <Button variant="blue" onClick={() => advance(detail.id, STATUS_TRANSITIONS[detail.status])}>
                → Advance to {STATUS_LABELS[STATUS_TRANSITIONS[detail.status]]}
              </Button>
            )}
            {(detail.status === 'active_investigation' || detail.status === 'bike_located' || detail.status === 'under_investigation') && (
              <Button variant="green" onClick={() => setRecovering(true)}>📍 Log Recovery</Button>
            )}
          </div>
          {(detail.status === 'pending_verification' || detail.status === 'recovered') && (
            <div className="mt-4 px-3 py-2 rounded bg-amber-400/10 border border-amber-400/30 text-xs text-amber-300">
              ⏳ Awaiting owner confirmation — the bike owner must confirm receipt to close this case.
              If the owner is unresponsive, an admin can close it on their behalf.
            </div>
          )}
          <CaseTimeline events={detail.timeline ?? []} />
        </Modal>
      )}

      {detail && recovering && (
        <Modal title="Log Recovery" onClose={() => { setRecovering(false); setRecForm(EMPTY_REC); }}>
          <form onSubmit={handleLogRecovery}>
            <Alert type="error" message={recError} onClose={() => setRecError('')} />
            <div className="grid grid-cols-2 gap-x-3">
              <div className="form-row"><label>Recovery City *</label><input placeholder="Karachi" value={recForm.recovery_city} onChange={(e) => setRecForm(f => ({ ...f, recovery_city: e.target.value }))} required /></div>
              <div className="form-row"><label>Recovery Date *</label><input type="date" value={recForm.recovery_date} onChange={(e) => setRecForm(f => ({ ...f, recovery_date: e.target.value }))} required /></div>
            </div>
            <div className="form-row">
              <label>Bike Condition</label>
              <select value={recForm.bike_condition} onChange={(e) => setRecForm(f => ({ ...f, bike_condition: e.target.value }))}>
                <option value="good">Good — no damage</option>
                <option value="damaged">Damaged</option>
                <option value="stripped">Stripped — parts removed</option>
                <option value="burnt">Burnt</option>
              </select>
            </div>
            <div className="form-row"><label>Notes</label><textarea placeholder="Condition of bike, where found, who reported it…" value={recForm.notes} onChange={(e) => setRecForm(f => ({ ...f, notes: e.target.value }))} /></div>
            <div className="flex justify-end gap-2 mt-2">
              <Button onClick={() => { setRecovering(false); setRecForm(EMPTY_REC); }}>Cancel</Button>
              <Button variant="green" type="submit" loading={saving}>Log Recovery</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
