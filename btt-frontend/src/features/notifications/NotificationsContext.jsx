import { createContext, useContext, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getNotifications, markRead as apiMarkRead, markAllRead as apiMarkAll } from './api';
import { normalizeNotificationList } from './lib/normalize';
import { apiErrorMessage } from '@/shared/lib/http';

const POLL_INTERVAL_MS = 60_000;

const NotificationsContext = createContext(null);

/**
 * One poll for the whole dashboard.
 *
 * The sidebar badge and the notifications page used to run separate hooks
 * against the same endpoint, so an open notifications page issued two requests
 * a minute and the two copies could disagree after a "mark read".  Polling is
 * also suspended while the tab is hidden and resumed on focus.
 */
export function NotificationsProvider({ children }) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const inFlight = useRef(false);

  const refetch = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const { data } = await getNotifications();
      setNotifications(normalizeNotificationList(data));
      setError('');
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to load notifications.'));
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();

    let timer = null;
    const start = () => {
      if (timer === null) timer = setInterval(refetch, POLL_INTERVAL_MS);
    };
    const stop = () => {
      if (timer !== null) { clearInterval(timer); timer = null; }
    };

    const onVisibility = () => {
      if (document.visibilityState === 'visible') { refetch(); start(); }
      else stop();
    };

    if (document.visibilityState === 'visible') start();
    document.addEventListener('visibilitychange', onVisibility);

    return () => { stop(); document.removeEventListener('visibilitychange', onVisibility); };
  }, [refetch]);

  const markRead = useCallback(async (id) => {
    // Optimistic — the badge should drop the moment the button is clicked.
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    try {
      await apiMarkRead(id);
    } catch {
      refetch();
    }
  }, [refetch]);

  const markAll = useCallback(async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    try {
      await apiMarkAll();
    } catch {
      refetch();
    }
  }, [refetch]);

  const unread = useMemo(
    () => notifications.reduce((n, item) => (item.is_read ? n : n + 1), 0),
    [notifications],
  );

  const value = useMemo(
    () => ({ notifications, loading, error, unread, markRead, markAll, refetch }),
    [notifications, loading, error, unread, markRead, markAll, refetch],
  );

  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}

export function useNotifications() {
  const ctx = useContext(NotificationsContext);
  if (!ctx) throw new Error('useNotifications must be used inside <NotificationsProvider>');
  return ctx;
}
