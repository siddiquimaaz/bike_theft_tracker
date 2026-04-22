import { useNotifications } from '../../hooks/useNotifications';
import { Button, Spinner, EmptyState } from '../../components/UI';
import NotificationItem from '../../components/cards/NotificationItem';

export default function NotificationsPage() {
  const { notifications, loading, unread, markRead, markAll, refetch } = useNotifications();

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="page-title">Notifications</h1>
          <p className="page-sub m-0">{unread > 0 ? `${unread} unread` : 'All caught up'}</p>
        </div>
        {unread > 0 && (
          <Button variant="ghost" size="sm" onClick={markAll}>Mark all read</Button>
        )}
      </div>

      {loading ? <Spinner /> : notifications.length === 0 ? (
        <div className="card"><EmptyState icon="🔔" title="No notifications yet" subtitle="You'll be notified about case updates and sighting matches here." /></div>
      ) : (
        <div className="flex flex-col gap-2">
          {notifications.map((n) => (
            <NotificationItem key={n.id} notif={n} onRead={markRead} onRefresh={refetch} />
          ))}
        </div>
      )}
    </div>
  );
}
