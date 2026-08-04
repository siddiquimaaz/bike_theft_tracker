import Modal from './Modal';
import Button from './Button';

export default function ConfirmDialog({ title, message, onConfirm, onClose, loading }) {
  return (
    <Modal title={title} onClose={onClose}>
      <p className="text-sm text-muted mb-6">{message}</p>
      <div className="flex justify-end gap-2">
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="danger" loading={loading} onClick={onConfirm}>Confirm</Button>
      </div>
    </Modal>
  );
}
