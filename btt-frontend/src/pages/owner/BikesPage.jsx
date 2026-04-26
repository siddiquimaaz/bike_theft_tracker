import { useState } from 'react';
import { useFetch }   from '../../hooks/useFetch';
import { getBikes, deleteBike } from '../../api/bikeApi';
import { Button, Modal, EmptyState, Spinner, ConfirmDialog } from '../../components/UI';
import BikeCard   from '../../components/cards/BikeCard';
import BikeForm   from '../../components/forms/BikeForm';
import ReportForm from '../../components/forms/ReportForm';

export default function BikesPage() {
  const { data, loading, refetch } = useFetch(getBikes, []);
  const bikes = data?.results ?? data ?? [];

  const [showAdd,       setShowAdd]       = useState(false);
  const [deleteId,      setDeleteId]      = useState(null);
  const [deleting,      setDeleting]      = useState(false);
  const [reportBike,    setReportBike]    = useState(null); // bike object to pre-fill report form

  async function handleDelete() {
    setDeleting(true);
    try { await deleteBike(deleteId); refetch(); }
    finally { setDeleting(false); setDeleteId(null); }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="page-title">My Bikes</h1>
          <p className="page-sub m-0">Manage your registered vehicles</p>
        </div>
        <Button variant="primary" onClick={() => setShowAdd(true)}>+ Register Bike</Button>
      </div>

      {loading ? <Spinner /> : bikes.length === 0 ? (
        <div className="card"><EmptyState icon="🏍️" title="No bikes registered yet" subtitle="Register your first bike to start tracking." /></div>
      ) : (
        <div className="flex flex-col gap-3">
          {bikes.map((b) => (
            <BikeCard
              key={b.id}
              bike={b}
              onDelete={(id) => setDeleteId(id)}
              onReportStolen={(bike) => setReportBike(bike)}
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
