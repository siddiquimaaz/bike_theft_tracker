/**
 * Decode a JWT without verifying it (signature is verified server-side).
 * Returns the payload object, or null on any error.
 */
export function decodeJWT(token) {
  try {
    const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(
      atob(b64).split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join('')
    );
    return JSON.parse(json);
  } catch {
    return null;
  }
}

const KEYS = { access: 'btt_access', refresh: 'btt_refresh', user: 'btt_user' };

export const storage = {
  saveTokens: (access, refresh) => {
    localStorage.setItem(KEYS.access, access);
    localStorage.setItem(KEYS.refresh, refresh);
  },
  saveUser: (user) => localStorage.setItem(KEYS.user, JSON.stringify(user)),
  getAccess:  () => localStorage.getItem(KEYS.access) || '',
  getRefresh: () => localStorage.getItem(KEYS.refresh) || '',
  getUser:    () => { try { return JSON.parse(localStorage.getItem(KEYS.user)); } catch { return null; } },
  clear:      () => Object.values(KEYS).forEach(k => localStorage.removeItem(k)),
};
