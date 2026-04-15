import API from './axios';

export const fuzzyMatchEngine  = (n)         => API.get(`/api/ml/fuzzy-match/?engine=${n}`);
export const fuzzyMatchChassis = (n)         => API.get(`/api/ml/fuzzy-match/?chassis=${n}`);
export const getHotspots       = (city)      => API.get('/api/ml/hotspots/', { params: { city } });
export const getTrends         = ()          => API.get('/api/ml/trends/');
export const getRecoveryZones  = (params)    => API.get('/api/ml/recovery-zones/', { params });
export const triggerReanalysis = ()          => API.post('/api/ml/trigger-reanalysis/');
