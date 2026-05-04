import API from './axios';

export const getReports      = (params)       => API.get('/api/reports/', { params });
export const getReport       = (id)           => API.get(`/api/reports/${id}/`);
export const fileReport      = (data)         => API.post('/api/reports/', data);
export const deleteReport    = (id)           => API.delete(`/api/reports/${id}/`);
export const updateStatus    = (id, status)   => API.put(`/api/reports/${id}/status/`, { status });
export const logRecovery     = (id, data)     => API.post(`/api/reports/${id}/recovery/`, data);
export const getRecovery     = (id)           => API.get(`/api/reports/${id}/recovery/`);
export const amendRecovery   = (id, data)     => API.put(`/api/reports/${id}/recovery/`, data);
export const confirmRecoveryReceipt = (id)    => API.put(`/api/reports/${id}/recovery/confirm/`, {});
export const getCommunityFeed = (params)      => API.get('/api/reports/community-feed/', { params });
