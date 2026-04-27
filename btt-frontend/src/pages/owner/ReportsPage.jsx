import { useState } from 'react';
import { useFetch }   from '../../hooks/useFetch';
import { getReports, getReport } from '../../api/reportApi';
import { getSightings, ownerConfirmSighting } from '../../api/sightingApi';
import { Button, Modal, EmptyState, Spinner } from '../../components/UI';
import Badge  from '../../components/UI/Badge';
import ReportForm from '../../components/forms/ReportForm';
import { STATUS_COLORS, STATUS_LABELS } from '../../utils/constants';
import { formatDate } from '../../utils/formatters';
import CaseTimeline from '../../components/timeline/CaseTimeline';

export default function ReportsPage() {
  const { data, loading, refetch } = useFetch(getReports, []);
  const reports = data?.results ?? data ?? [];

  // Sightings of my bikes that still need owner confirmation
  const { data: sightingsData, refetch: refetchSightings } = useFetch(getSightings, []);
  const allSightings = sightingsData?.results ?? sightingsData ?? [];
  const pendingSightings = allSightings.filter(
    (s) => s.is_about_my_bike && s.owner_confirmation_status === 'pending'
  );

  const [confirmingId, setConfirmingId] = useState(null);

  async function handleConfirm(sightingId, response) {
    setConfirmingId(sightingId);
    try {
      await ownerConfirmSighting(sightingId, response);
      refetchSightings();
    } catch (err) {
      alert(err.response?.data?.error ?? 'Failed to submit response.');
    } finally {
      setConfirmingId(null);
    }
  }

  const [showFile, setShowFile] = useState(false);
  const [detail,   setDetail]   = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  async function openDetail(reportId) {
    setLoadingDetail(true);
    try {
      const { data } = await getReport(reportId);
      setDetail(data);
    } finally {
      setLoadingDetail(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="page-title">My Reports</h1>
          <p className="page-sub m-0">Track all your theft case filings</p>
        </div>
        <Button variant="primary" onClick={() => setShowFile(true)}>+ File Report</Button>
      </div>

      {/* ── Pending sightings needing owner response ─────────────────────── */}
      {pendingSightings.length > 0 && (
        <div className="card mb-6" style={{ borderColor: 'rgba(251,191,36,.3)', border: '1px solid rgba(251,191,36,.3)' }}>
          <h2 className="font-heading font-semibold text-sm text-amber-300 mb-4">
            🔔 Sightings Awaiting Your Response ({pendingSightings.length})
          </h2>
          <div className="flex flex-col gap-3">
            {pendingSightings.map((s) => (
              <div key={s.id} className="rounded-lg p-4 flex items-start justify-between gap-4 bg-white/[.04]">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-gray-100">
                    {s.top_match_info?.make} {s.top_match_info?.model} spotted in {s.sighting_city}
                  </div>
                  <div className="text-xs text-muted mt-1">
                    {formatDate(s.sighting_date)}
                    {s.raw_engine_number && <> · Reported engine: <span className="mono">{s.raw_engine_number}</span></>}
                    {s.fuzzy_match_score != null && <> · Match score: <span className="mono">{Number(s.fuzzy_match_score).toFixed(1)}</span></>}
                  </div>
                  {s.sighting_description && (
                    <div className="text-xs text-faint mt-1 line-clamp-2">{s.sighting_description}</div>
                  )}
                  {s.owner_response_deadline && (
                    <div className="text-xs text-amber-400/70 mt-1">
                      ⏱ Respond by {formatDate(s.owner_response_deadline)} — authority will act on your answer
                    </div>
                  )}
                </div>
                <div className="flex gap-2 flex-shrink-0 flex-wrap justify-end">
                  <button
                    disabled={confirmingId === s.id}
                    className="px-3 py-1.5 rounded text-xs font-semibold bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/40 border border-emerald-600/30 disabled:opacity-50"
                    onClick={() => handleConfirm(s.id, 'yes')}
                  >✅ That's my bike</button>
                  <button
                    disabled={confirmingId === s.id}
                    className="px-3 py-1.5 rounded text-xs font-semibold bg-red-600/20 text-red-400 hover:bg-red-600/40 border border-red-600/30 disabled:opacity-50"
                    onClick={() => handleConfirm(s.id, 'no')}
                  >❌ Not my bike</button>
                  <button
                    disabled={confirmingId === s.id}
                    className="px-3 py-1.5 rounded text-xs font-semibold bg-gray-600/20 text-gray-400 hover:bg-gray-600/40 border border-gray-600/30 disabled:opacity-50"
                    onClick={() => handleConfirm(s.id, 'not_sure')}
                  >🤷 Not sure</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading ? <Spinner /> : (
        <div className="card p-0 overflow-hidden">
          {reports.length === 0
            ? <EmptyState icon="📋" title="No reports filed yet" subtitle="File a theft report for any of your registered bikes." />
            : (
              <table className="tbl">
                <thead className="bg-btt-700"><tr>
                  <th>ID</th><th>Bike</th><th>Status</th><th>City</th><th>Date</th>
                </tr></thead>
                <tbody>
                  {reports.map((r) => (
                    <tr key={r.id} className="cursor-pointer" onClick={() => openDetail(r.id)}>
                      <td><span className="mono text-primary">#{r.id}</span></td>
                      <td>
                        <div className="text-xs text-muted">{r.bike_info?.make ?? ''} {r.bike_info?.model ?? ''}</div>
                        <div className="mono text-gray-300">{r.bike_info?.engine_number ?? '—'}</div>
                      </td>
                      <td><Badge variant={STATUS_COLORS[r.status] ?? 'gray'}>{STATUS_LABELS[r.status] ?? r.status}</Badge></td>
                      <td className="text-muted">{r.theft_city ?? '—'}</td>
                      <td className="text-faint text-xs">{formatDate(r.theft_date ?? r.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>
      )}

      {showFile && (
        <Modal title="File Theft Report" onClose={() => setShowFile(false)} size="lg">
          <ReportForm onSuccess={() => { setShowFile(false); refetch(); }} onCancel={() => setShowFile(false)} />
        </Modal>
      )}

      {loadingDetail && <Spinner />}
      {detail && (
        <Modal title={`Report #${detail.id} — ${detail.reference_number ?? ''}`} onClose={() => setDetail(null)}>
          <Badge variant={STATUS_COLORS[detail.status] ?? 'gray'} className="mb-4">{STATUS_LABELS[detail.status] ?? detail.status}</Badge>
          <table className="tbl mt-3">
            <tbody>
              {[
                ['Reference',   detail.reference_number],
                ['City',        detail.theft_city],
                ['Theft Date',  formatDate(detail.theft_date)],
                ['Filed',       formatDate(detail.created_at)],
                ['Location',    detail.theft_location_detail],
                ['Description', detail.description],
              ].filter(([, v]) => v).map(([k, v]) => (
                <tr key={k}><td className="text-faint text-xs w-28 border-none py-1">{k}</td><td className="text-sm text-gray-100 border-none py-1">{v}</td></tr>
              ))}
            </tbody>
          </table>
          <CaseTimeline events={detail.timeline ?? []} />
        </Modal>
      )}
    </div>
  );
}
