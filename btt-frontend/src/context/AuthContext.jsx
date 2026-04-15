import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { login as apiLogin, logout as apiLogout } from '../api/authApi';
import { storage, decodeJWT } from '../utils/jwt';
import { ROLE_HOME } from '../utils/constants';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(() => storage.getUser());
  const [token,   setToken]   = useState(() => storage.getAccess());
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  // Hydrate user from JWT if localStorage already has tokens (page refresh)
  useEffect(() => {
    const t = storage.getAccess();
    if (t && !user) {
      const payload = decodeJWT(t);
      if (payload) {
        const u = storage.getUser() || {
          email:     payload.email    ?? '',
          role:      payload.role     ?? 'owner',
          full_name: payload.name     ?? payload.email ?? '',
          id:        payload.user_id  ?? null,
        };
        setUser(u);
      }
    }
  }, []);

  const login = useCallback(async (email, password) => {
    setLoading(true);
    setError('');
    try {
      const { data } = await apiLogin({ email, password });
      const payload  = decodeJWT(data.access);

      const u = data.user ?? {
        email,
        role:      payload?.role     ?? 'owner',
        full_name: payload?.name     ?? email,
        id:        payload?.user_id  ?? null,
      };

      storage.saveTokens(data.access, data.refresh);
      storage.saveUser(u);
      setToken(data.access);
      setUser(u);
      return u;
    } catch (err) {
      const msg = err.response?.data?.detail
               ?? err.response?.data?.error
               ?? 'Login failed. Check your credentials.';
      setError(msg);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try { await apiLogout(storage.getRefresh()); } catch { /* ignore */ }
    storage.clear();
    setUser(null);
    setToken('');
  }, []);

  const clearError = useCallback(() => setError(''), []);

  const value = {
    user,
    token,
    loading,
    error,
    isAuthenticated: !!token && !!user,
    role: user?.role ?? null,
    homeRoute: user ? (ROLE_HOME[user.role] ?? '/login') : '/login',
    login,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Convenience hook
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
