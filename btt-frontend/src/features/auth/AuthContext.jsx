import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { login as apiLogin, logout as apiLogout } from './api';
import { storage, decodeJWT } from '@/shared/lib/jwt';
import { ROLE_HOME } from '@/shared/lib/constants';
import { apiErrorMessage } from '@/shared/lib/http';

const AuthContext = createContext(null);

/** Build the user record we keep in state from a JWT payload. */
function userFromToken(token, fallbackEmail = '') {
  const payload = decodeJWT(token);
  if (!payload) return null;
  return {
    email:     payload.email   ?? fallbackEmail,
    role:      payload.role    ?? 'owner',
    full_name: payload.name    ?? payload.email ?? fallbackEmail,
    id:        payload.user_id ?? null,
  };
}

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(() => storage.getUser());
  const [token,   setToken]   = useState(() => storage.getAccess());
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  // Hydrate user from JWT if localStorage already has tokens (page refresh)
  useEffect(() => {
    const t = storage.getAccess();
    if (!t || user) return;
    const hydrated = storage.getUser() ?? userFromToken(t);
    if (hydrated) setUser(hydrated);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const login = useCallback(async (email, password) => {
    setLoading(true);
    setError('');
    try {
      const { data } = await apiLogin({ email, password });
      const u = data.user ?? userFromToken(data.access, email) ?? { email, role: 'owner', full_name: email, id: null };

      storage.saveTokens(data.access, data.refresh);
      storage.saveUser(u);
      setToken(data.access);
      setUser(u);
      return u;
    } catch (err) {
      const msg = apiErrorMessage(err, 'Login failed. Check your credentials.');
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

  const value = useMemo(() => ({
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
  }), [user, token, loading, error, login, logout, clearError]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
