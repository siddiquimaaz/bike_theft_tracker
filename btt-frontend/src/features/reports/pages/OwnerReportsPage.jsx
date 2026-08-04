import { useMemo, useState } from 'react';
import { useList } from '@/shared/hooks/useFetch';
import { getReports, getReport, confirmRecoveryReceipt } from '../api';
import { getSightings } from '@/features/sightings/api';
import ReportForm from '../components/ReportForm';
import CaseTimeline from '../components/CaseTimeline';
import OwnerSightingPrompts from '@/features/sightings/components/OwnerSightingPrompts';
import PageHeader from '@/shared/components/layout/PageHeader';
import DetailList from '@/shared/components/data/DetailList';
import { Alert, Badge, Button, Modal, EmptyState, Spinner } from '@/shared/components/ui';
import { isAwaitingOwner, statusColor, statusLabel } from '@/shared/lib/reportStatus';
import { apiErrorMessage } from '@/shared/lib/http';
import { formatDate } from '@/shared/lib/formatters';

/** The owner may confirm receipt once the bike is located and not yet acknowledged. */
const canConfirmRecovery = (report) =>
  !!report && !report.owner_recovery_confirmed && isAwaitingOwner(report.status);

export default function OwnerReportsPage() {
  const { items: reports, loading, refetch } = useList(getReports, []);

  // Sightings of my bikes that still need owner confirmation
  const { items: allSightings, refetch: refetchSightings } = useList(getSightings, []);
  const pendingSightings = useMemo(
    () => allSightings.filter((s) => s.is_about_my_bike && s.owner_confirmation_status === 'pending'),
    [allSightings],
  );

  const [showFile,      setShowFile]      = useState(false);
  const [detail,        setDetail]        = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [confirmingId,  setConfirmingId]  = useState(null);
  const [error,         setError]         = useState('');

  async function openDetail(reportId) {
    setLoadingDetail(true);
    try {
      const { data } = await getReport(reportId);
      setDetail(data);
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to open report.'));
    } finally {
      setLoadingDetail(false);
    }
  }

  async function handleConfirmRecovery(reportId) {
    setConfirmingId(reportId);
    setError('');
    try {
      await confirmRecoveryReceipt(reportId);
      await refetch();
      if (detail?.id === reportId) await openDetail(reportId);
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to confirm bike receipt.'));
    } finally {
      setConfirmingId(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="My Reports"
        subtitle="Track all your theft case filings"
        action={<Button variant="primary" onClick={() => setShowFile(true)}>+ File Report</Button>}
      />

      <Alert type="error" message={error} onClose={() => setError('')} />

      <OwnerSightingPrompts sightings={pendingSightings} onResponded={refetchSightings} />

      {loading ? <Spinner /> : (
        <div className="card p-0 overflow-hidden">
          {reports.length === 0
            ? <EmptyState icon="📋" title="No reports filed yet" subtitle="File a theft report for any of your registered bikes." />
            : (
              <table className="tbl">
                <thead className="bg-btt-700"><tr>
                  <th>ID</th><th>Bike</th><th>Status</th><th>City</th><th>Date</th><th>Action</th>
                </tr></thead>
                <tbody>
                  {reports.map((r) => (
                    <tr key={r.id} className="cursor-pointer" onClick={() => openDetail(r.id)}>
                      <td><span className="mono text-primary">#{r.id}</span></td>
                      <td>
                        <div className="text-xs text-muted">{r.bike_info?.make ?? ''} {r.bike_info?.model ?? ''}</div>
                        <div className="mono text-gray-300">{r.bike_info?.engine_number ?? '—'}</div>
                      </td>
                      <td><Badge variant={statusColor(r.status)}>{statusLabel(r.status)}</Badge></td>
                      <td className="text-muted">{r.theft_city ?? '—'}</td>
                      <td className="text-faint text-xs">{formatDate(r.theft_date ?? r.created_at)}</td>
                      <td onClick={(e) => e.stopPropagation()}>
                        {canConfirmRecovery(r) ? (
                          <Button
                            size="sm"
                            variant="green"
                            loading={confirmingId === r.id}
                            onClick={() => handleConfirmRecovery(r.id)}
                          >
                            Confirm Bike Received
                          </Button>
                        ) : (
                          <span className="text-faint text-xs">—</span>
                        )}
                      </td>
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
          <Badge variant={statusColor(detail.status)} className="mb-4">{statusLabel(detail.status)}</Badge>

          <DetailList
            className="mt-3"
            rows={[
              ['Reference',   detail.reference_number],
              ['City',        detail.theft_city],
              ['Theft Date',  formatDate(detail.theft_date)],
              ['Filed',       formatDate(detail.created_at)],
              ['Location',    detail.theft_location_detail],
              ['Description', detail.description],
            ]}
          />

          {canConfirmRecovery(detail) && (
            <div className="mt-4">
              <Button
                variant="green"
                loading={confirmingId === detail.id}
                onClick={() => handleConfirmRecovery(detail.id)}
              >
                Confirm Bike Received
              </Button>
            </div>
          )}

          <CaseTimeline events={detail.timeline ?? []} />
        </Modal>
      )}
    </div>
  );
}
