import API from './axios';

export const getNotifications = ()   => API.get('/api/notifications/');
export const markRead         = (id) => API.put(`/api/notifications/${id}/read/`, {});
export const markAllRead      = ()   => API.put('/api/notifications/read-all/', {});
