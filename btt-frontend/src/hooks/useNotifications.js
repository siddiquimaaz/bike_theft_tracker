import { useState, useEffect } from 'react';
import { getNotifications, markRead as apiMarkRead, markAllRead as apiMarkAll } from '../api/notificationApi';
import { normalizeNotificationList } from '../utils/notifications';

/**
 * Returns full notification state + actions.
 */
export function useNotifications() {
  const [notifications, setNotifications] = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState('');

  async function load() {
    setLoading(true);
    try {
      const { data } = await getNotifications();
      setNotifications(normalizeNotificationList(data));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function markRead(id) {
    await apiMarkRead(id);
    setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, is_read: true } : n));
  }

  async function markAll() {
    await apiMarkAll();
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
  }

  return {
    notifications,
    loading,
    error,
    unread: notifications.filter((n) => !n.is_read).length,
    markRead,
    markAll,
    refetch: load,
  };
}

/**
 * Lightweight hook used by the Sidebar (just the unread count).
 * Polls every 60 s in the background.
 */
export function useNotificationsCount() {
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    async function fetch() {
      try {
        const { data } = await getNotifications();
        const list = normalizeNotificationList(data);
        setUnread(list.filter((n) => !n.is_read).length);
      } catch { /* ignore */ }
    }
    fetch();
    const interval = setInterval(fetch, 60_000);
    return () => clearInterval(interval);
  }, []);

  return { unread };
}
