import { useCallback, useState } from 'react';
import { useList } from '@/shared/hooks/useFetch';
import { getBikes, deleteBike } from '../api';
import BikeCard from '../components/BikeCard';
import BikeForm from '../components/BikeForm';
import ReportForm from '@/features/reports/components/ReportForm';
import PageHeader from '@/shared/components/layout/PageHeader';
import { Button, Modal, EmptyState, Spinner, ConfirmDialog } from '@/shared/components/ui';

export default function BikesPage() {
  const { items: bikes, loading, refetch } = useList(getBikes, []);

  const [showAdd,    setShowAdd]    = useState(false);
  const [deleteId,   setDeleteId]   = useState(null);
  const [deleting,   setDeleting]   = useState(false);
  const [reportBike, setReportBike] = useState(null); // bike object to pre-fill report form

  async function handleDelete() {
    setDeleting(true);
    try { await deleteBike(deleteId); refetch(); }
    finally { setDeleting(false); setDeleteId(null); }
  }

  // Stable so the memoised BikeCard does not re-render on every parent update.
  const handleAskDelete   = useCallback((id) => setDeleteId(id), []);
  const handleReportStolen = useCallback((bike) => setReportBike(bike), []);

  return (
    <div>
      <PageHeader
        title="My Bikes"
        subtitle="Manage your registered vehicles"
        action={<Button variant="primary" onClick={() => setShowAdd(true)}>+ Register Bike</Button>}
      />

      {loading ? <Spinner /> : bikes.length === 0 ? (
        <div className="card">
          <EmptyState icon="🏍️" title="No bikes registered yet" subtitle="Register your first bike to start tracking." />
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {bikes.map((b) => (
            <BikeCard
              key={b.id}
              bike={b}
              onDelete={handleAskDelete}
              onReportStolen={handleReportStolen}
            />
          ))}
        </div>
      )}

      {/* Register new bike */}
      {showAdd && (
        <Modal title="Register New Bike" onClose={() => setShowAdd(false)}>
          <BikeForm onSuccess={() => { setShowAdd(false); refetch(); }} onCancel={() => setShowAdd(false)} />
        </Modal>
      )}

      {/* Report stolen — pre-filled with the selected bike */}
      {reportBike && (
        <Modal
          title={`Report Stolen — ${reportBike.make ?? ''} ${reportBike.model ?? ''}`}
          onClose={() => setReportBike(null)}
          size="lg"
        >
          <ReportForm
            initialBikeId={reportBike.id}
            onSuccess={() => { setReportBike(null); refetch(); }}
            onCancel={() => setReportBike(null)}
          />
        </Modal>
      )}

      {deleteId && (
        <ConfirmDialog
          title="Remove Bike"
          message="This will soft-delete the bike. All theft evidence is preserved."
          loading={deleting}
          onConfirm={handleDelete}
          onClose={() => setDeleteId(null)}
        />
      )}
    </div>
  );
}
