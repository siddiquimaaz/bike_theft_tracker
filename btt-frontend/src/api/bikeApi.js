import API from './axios';

export const getBikes    = ()         => API.get('/api/bikes/');
export const getBike     = (id)       => API.get(`/api/bikes/${id}/`);
export const addBike     = (data)     => API.post('/api/bikes/', data);
export const updateBike  = (id, data) => API.put(`/api/bikes/${id}/`, data);
export const deleteBike  = (id)       => API.delete(`/api/bikes/${id}/`);
