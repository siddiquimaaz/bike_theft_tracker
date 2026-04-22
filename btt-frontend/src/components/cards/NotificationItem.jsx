import { formatDateTime } from '../../utils/formatters';
import Button from '../UI/Button';
import { ownerConfirmSighting } from '../../api/sightingApi';
import { confirmRecoveryReceipt } from '../../api/reportApi';

const ICONS = { sighting: '👁️', recovery: '✅', status: '📋', report: '🚨', default: '🔔' };

export default function NotificationItem({ notif, onRead, onRefresh }) {
  async function respondToHandshake(response) {
    if (!notif.sighting_id) return;
    await ownerConfirmSighting(notif.sighting_id, response);
    if (onRefresh) onRefresh();
  }

  async function confirmRecovery() {
    if (!notif.report_id) return;
    await confirmRecoveryReceipt(notif.report_id);
    if (onRefresh) onRefresh();
  }

  return (
    <div className={`card card-sm transition-opacity ${notif.is_read ? 'opacity-55' : ''}`}
         style={{ borderLeft: `2px solid ${notif.is_read ? 'transparent' : '#f59e0b'}` }}>
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
      {notif.type === 'sighting_owner_handshake' && notif.metadata?.requires_response && (
        <div className="flex gap-2 mt-3">
          <Button size="sm" variant="green" onClick={() => respondToHandshake('yes')}>Yes</Button>
          <Button size="sm" onClick={() => respondToHandshake('no')}>No</Button>
          <Button size="sm" variant="ghost" onClick={() => respondToHandshake('not_sure')}>Not Sure</Button>
        </div>
      )}
      {notif.type === 'recovery' && notif.metadata?.requires_owner_confirmation && (
        <div className="flex gap-2 mt-3">
          <Button size="sm" variant="green" onClick={confirmRecovery}>Confirm Bike Received</Button>
        </div>
      )}
    </div>
  );
}
