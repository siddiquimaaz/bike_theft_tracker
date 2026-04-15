import API from './axios';

export const getUsers         = (params) => API.get('/api/admin/users/', { params });
export const createAuthority  = (data)   => API.post('/api/admin/users/authority/', data);
// API expects { is_active: boolean } or { role: string }
export const updateUserStatus = (id, isActive) => API.put(`/api/admin/users/${id}/status/`, { is_active: isActive });
export const getAnalytics     = ()       => API.get('/api/admin/analytics/');
export const getAuditLogs     = (params) => API.get('/api/admin/audit-logs/', { params });
