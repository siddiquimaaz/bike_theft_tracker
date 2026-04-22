import { useState } from 'react';
import { useFetch }   from '../../hooks/useFetch';
import { getReports, getReport } from '../../api/reportApi';
import { Button, Modal, EmptyState, Spinner } from '../../components/UI';
import Badge  from '../../components/UI/Badge';
import ReportForm from '../../components/forms/ReportForm';
import { STATUS_COLORS, STATUS_LABELS } from '../../utils/constants';
import { formatDate } from '../../utils/formatters';
import CaseTimeline from '../../components/timeline/CaseTimeline';

export default function ReportsPage() {
  const { data, loading, refetch } = useFetch(getReports, []);
  const reports = data?.results ?? data ?? [];
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
