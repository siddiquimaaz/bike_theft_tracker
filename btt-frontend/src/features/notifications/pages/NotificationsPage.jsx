import { useNotifications } from '../NotificationsContext';
import NotificationItem from '../components/NotificationItem';
import PageHeader from '@/shared/components/layout/PageHeader';
import { Alert, Button, Spinner, EmptyState } from '@/shared/components/ui';

export default function NotificationsPage() {
  const { notifications, loading, error, unread, markRead, markAll, refetch } = useNotifications();

  return (
    <div>
      <PageHeader
        title="Notifications"
        subtitle={unread > 0 ? `${unread} unread` : 'All caught up'}
        action={unread > 0
          ? <Button variant="ghost" size="sm" onClick={markAll}>Mark all read</Button>
          : undefined}
      />

      <Alert type="error" message={error} />

      {loading ? <Spinner /> : notifications.length === 0 ? (
        <div className="card">
          <EmptyState icon="🔔" title="No notifications yet" subtitle="You'll be notified about case updates and sighting matches here." />
        </div>
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
