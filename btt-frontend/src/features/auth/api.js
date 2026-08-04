import API from '@/shared/api/client';

export const login          = (data)        => API.post('/api/auth/login/', data);
export const register       = (data)        => API.post('/api/auth/register/', data);
export const logout         = (refresh)     => API.post('/api/auth/logout/', { refresh });
export const refreshToken   = (refresh)     => API.post('/api/auth/token/refresh/', { refresh });
export const verifyEmail    = (token)       => API.post(`/api/auth/verify-email/${token}/`);
export const forgotPassword = (email)       => API.post('/api/auth/forgot-password/', { email });
export const resetPassword  = (token, data) => API.post(`/api/auth/reset-password/${token}/`, data);

// Pre-submit availability checks — return { available, valid_format, reason }
export const checkEmail = (email) => API.get('/api/auth/check-email/', { params: { email } });
export const checkCnic  = (cnic)  => API.get('/api/auth/check-cnic/',  { params: { cnic } });
