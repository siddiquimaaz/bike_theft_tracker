import API from '@/shared/api/client';

export const getSightings   = (params) => API.get('/api/sightings/', { params });
export const getSighting    = (id)     => API.get(`/api/sightings/${id}/`);
export const submitSighting = (data)   => API.post('/api/sightings/', data);
// bike_id is required — authority confirms which stolen bike this sighting matches
export const verifySighting = (id, bikeId) => API.put(`/api/sightings/${id}/verify/`, { bike_id: bikeId });
export const ownerConfirmSighting = (id, response) =>
  API.put(`/api/sightings/${id}/owner-confirm/`, { response });
