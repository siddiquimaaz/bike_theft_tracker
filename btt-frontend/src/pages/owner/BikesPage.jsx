import { useState } from 'react';
import { useFetch }   from '../../hooks/useFetch';
import { getBikes, deleteBike } from '../../api/bikeApi';
import { Button, Modal, EmptyState, Spinner, ConfirmDialog } from '../../components/UI';
import BikeCard   from '../../components/cards/BikeCard';
import BikeForm   from '../../components/forms/BikeForm';

export default function BikesPage() {
  const { data, loading, refetch } = useFetch(getBikes, []);
  const bikes = data?.results ?? data ?? [];

  const [showAdd,   setShowAdd]   = useState(false);
  const [deleteId,  setDeleteId]  = useState(null);
  const [deleting,  setDeleting]  = useState(false);

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
            <BikeCard key={b.id} bike={b} onDelete={(id) => setDeleteId(id)} />
          ))}
        </div>
      )}

      {showAdd && (
        <Modal title="Register New Bike" onClose={() => setShowAdd(false)}>
          <BikeForm onSuccess={() => { setShowAdd(false); refetch(); }} onCancel={() => setShowAdd(false)} />
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
