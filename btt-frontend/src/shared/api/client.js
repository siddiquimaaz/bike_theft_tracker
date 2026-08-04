import axios from 'axios';
import { storage } from '@/shared/lib/jwt';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

const API = axios.create({
  // In dev, Vite proxies /api → http://localhost:8000 (see vite.config.js).
  // In prod, set VITE_API_BASE_URL in your .env.
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
});

// ── Request interceptor: attach Bearer token ──────────────────────
API.interceptors.request.use((config) => {
  const token = storage.getAccess();
  if (token) config.headers['Authorization'] = `Bearer ${token}`;
  return config;
});

// ── Response interceptor: silent token refresh on 401 ────────────
let refreshing = false;
let queue = [];

function processQueue(error, token = null) {
  queue.forEach(({ resolve, reject }) => error ? reject(error) : resolve(token));
  queue = [];
}

/**
 * Credential endpoints must never enter the refresh dance: a 401 from
 * /login/ means "wrong password", not "expired session".  Treating it as the
 * latter used to clear storage and hard-navigate to /login, reloading the page
 * out from under the error message the user was supposed to read.
 */
const isAuthEndpoint = (url = '') => url.includes('/api/auth/');

function redirectToLogin() {
  storage.clear();
  if (!window.location.pathname.startsWith('/login')) {
    window.location.href = '/login';
  }
}

API.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;

    if (error.response?.status !== 401 || !original || original._retry || isAuthEndpoint(original.url)) {
      return Promise.reject(error);
    }

    // No refresh token means there was never a session to renew — surface the
    // 401 to the caller rather than bouncing through /login.
    const refresh = storage.getRefresh();
    if (!refresh) return Promise.reject(error);

    if (refreshing) {
      return new Promise((resolve, reject) => queue.push({ resolve, reject }))
        .then((token) => {
          original.headers['Authorization'] = `Bearer ${token}`;
          return API(original);
        });
    }

    original._retry = true;
    refreshing = true;

    try {
      const { data } = await axios.post(`${BASE_URL}/api/auth/token/refresh/`, { refresh });

      storage.saveTokens(data.access, data.refresh ?? refresh);
      API.defaults.headers.common['Authorization'] = `Bearer ${data.access}`;
      processQueue(null, data.access);
      original.headers['Authorization'] = `Bearer ${data.access}`;
      return API(original);
    } catch (refreshError) {
      processQueue(refreshError, null);
      redirectToLogin();
      return Promise.reject(refreshError);
    } finally {
      refreshing = false;
    }
  }
);

export default API;
