import { useState, useEffect, useCallback } from 'react';

/**
 * Generic data-fetching hook.
 * apiFn: () => Promise<AxiosResponse>
 * deps:  dependency array that triggers re-fetch
 *
 * Returns { data, loading, error, refetch }
 */
export function useFetch(apiFn, deps = []) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');

  const fetch = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await apiFn();
      setData(res.data ?? res);
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message ?? 'Failed to load data.');
    } finally {
      setLoading(false);
    }
  }, deps); // eslint-disable-line

  useEffect(() => { fetch(); }, [fetch]);

  return { data, loading, error, refetch: fetch };
}
