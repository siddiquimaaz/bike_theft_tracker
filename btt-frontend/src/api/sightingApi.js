import API from './axios';

export const getSightings    = (params) => API.get('/api/sightings/', { params });
export const getSighting     = (id)     => API.get(`/api/sightings/${id}/`);
export const submitSighting  = (data)   => API.post('/api/sightings/', data);
export const verifySighting  = (id)     => API.put(`/api/sightings/${id}/verify/`, {});
