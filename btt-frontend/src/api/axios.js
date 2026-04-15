import axios from 'axios';
import { storage, isTokenExpiring } from '../utils/jwt';

const API = axios.create({
  // In dev, Vite proxies /api → http://localhost:8000 (see vite.config.js).
  // In prod, set VITE_API_BASE_URL in your .env.
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
});

// ── Request interceptor: attach Bearer token ──────────────────────
API.interceptors.request.use(
  (config) => {
    const token = storage.getAccess();
    if (token) config.headers['Authorization'] = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor: silent token refresh on 401 ────────────
let refreshing = false;
let queue = [];

function processQueue(error, token = null) {
  queue.forEach(({ resolve, reject }) => error ? reject(error) : resolve(token));
  queue = [];
}

API.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;

    // Only attempt refresh once per request and only on 401
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    if (refreshing) {
      return new Promise((resolve, reject) => {
        queue.push({ resolve, reject });
      }).then((token) => {
        original.headers['Authorization'] = `Bearer ${token}`;
        return API(original);
      });
    }

    original._retry = true;
    refreshing = true;

    try {
      const refresh = storage.getRefresh();
      if (!refresh) throw new Error('No refresh token');

      const { data } = await axios.post(
        `${import.meta.env.VITE_API_BASE_URL ?? ''}/api/auth/token/refresh/`,
        { refresh }
      );

      storage.saveTokens(data.access, data.refresh ?? refresh);
      API.defaults.headers.common['Authorization'] = `Bearer ${data.access}`;
      processQueue(null, data.access);
      original.headers['Authorization'] = `Bearer ${data.access}`;
      return API(original);
    } catch (refreshError) {
      processQueue(refreshError, null);
      storage.clear();
      window.location.href = '/login';
      return Promise.reject(refreshError);
    } finally {
      refreshing = false;
    }
  }
);

export default API;
