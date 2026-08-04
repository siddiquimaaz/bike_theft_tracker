import { memo, useState } from 'react';
import { ownerConfirmSighting } from '@/features/sightings/api';
import { confirmRecoveryReceipt } from '@/features/reports/api';
import { formatDateTime } from '@/shared/lib/formatters';
import { apiErrorMessage } from '@/shared/lib/http';
import Button from '@/shared/components/ui/Button';

const ICONS = { sighting: '👁️', recovery: '✅', status: '📋', report: '🚨', default: '🔔' };

const HANDSHAKE_RESPONSES = [
  { value: 'yes',      label: 'Yes',      variant: 'green' },
  { value: 'no',       label: 'No',       variant: 'ghost' },
  { value: 'not_sure', label: 'Not Sure', variant: 'ghost' },
];

function NotificationItem({ notif, onRead, onRefresh }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function run(action) {
    setBusy(true);
    setError('');
    try {
      await action();
      onRefresh?.();
    } catch (err) {
      setError(apiErrorMessage(err, 'Action failed.'));
    } finally {
      setBusy(false);
    }
  }

  const needsHandshake =
    notif.type === 'sighting_owner_handshake' && notif.metadata?.requires_response && notif.sighting_id;
  const needsRecoveryConfirm =
    notif.type === 'recovery' && notif.metadata?.requires_owner_confirmation && notif.report_id;

  return (
    <div
      className={`card card-sm transition-opacity ${notif.is_read ? 'opacity-55' : ''}`}
      style={{ borderLeft: `2px solid ${notif.is_read ? 'transparent' : '#f59e0b'}` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="text-lg flex-shrink-0">{ICONS[notif.type] ?? ICONS.default}</span>
          <div>
            <p className={`text-sm ${notif.is_read ? 'text-muted' : 'text-gray-100 font-medium'}`}>
              {notif.message ?? notif.title ?? 'Notification'}
            </p>
            <p className="text-[11px] text-faint mt-0.5">{formatDateTime(notif.created_at)}</p>
          </div>
        </div>
        {!notif.is_read && onRead && (
          <Button variant="ghost" size="sm" onClick={() => onRead(notif.id)}>Mark read</Button>
        )}
      </div>

      {needsHandshake && (
        <div className="flex gap-2 mt-3">
          {HANDSHAKE_RESPONSES.map(({ value, label, variant }) => (
            <Button
              key={value}
              size="sm"
              variant={variant}
              loading={busy}
              onClick={() => run(() => ownerConfirmSighting(notif.sighting_id, value))}
            >
              {label}
            </Button>
          ))}
        </div>
      )}

      {needsRecoveryConfirm && (
        <div className="flex gap-2 mt-3">
          <Button
            size="sm"
            variant="green"
            loading={busy}
            onClick={() => run(() => confirmRecoveryReceipt(notif.report_id))}
          >
            Confirm Bike Received
          </Button>
        </div>
      )}

      {error && <p className="text-[11px] text-red-400 mt-2">{error}</p>}
    </div>
  );
}

export default memo(NotificationItem);
