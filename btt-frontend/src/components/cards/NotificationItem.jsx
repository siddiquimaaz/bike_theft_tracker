import { formatDateTime } from '../../utils/formatters';
import Button from '../UI/Button';

const ICONS = { sighting: '👁️', recovery: '✅', status: '📋', report: '🚨', default: '🔔' };

export default function NotificationItem({ notif, onRead }) {
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
    </div>
  );
}
