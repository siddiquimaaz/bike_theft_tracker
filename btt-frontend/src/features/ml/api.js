import API from '@/shared/api/client';

export const fuzzyMatchEngine  = (n)      => API.get('/api/ml/fuzzy-match/', { params: { engine: n } });
export const fuzzyMatchChassis = (n)      => API.get('/api/ml/fuzzy-match/', { params: { chassis: n } });
export const getHotspots       = (city)   => API.get('/api/ml/hotspots/', { params: { city } });
export const getTrends         = ()       => API.get('/api/ml/trends/');
export const getRecoveryZones  = (params) => API.get('/api/ml/recovery-zones/', { params });
export const getRecoveryRadius = (city)   => API.get('/api/ml/recovery-radius/', { params: { city } });
export const getCorridors      = (city)   => API.get('/api/ml/corridors/', { params: { city } });
export const triggerReanalysis = ()       => API.post('/api/ml/trigger-reanalysis/');
