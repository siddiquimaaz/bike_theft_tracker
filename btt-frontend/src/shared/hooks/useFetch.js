import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { apiErrorMessage, unwrapList } from '@/shared/lib/http';

/**
 * Generic data-fetching hook.
 *
 * apiFn: () => Promise<AxiosResponse>
 * deps:  dependency array that triggers a re-fetch
 *
 * `apiFn` is held in a ref, so passing an inline arrow (the usual way to close
 * over a query param) does not need to be memoised by the caller — only `deps`
 * decides when to re-run.  Responses carry a sequence number so a slow reply
 * from a superseded request can never overwrite a newer one.
 */
export function useFetch(apiFn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: '' });

  const apiRef = useRef(apiFn);
  apiRef.current = apiFn;

  const requestId = useRef(0);

  const refetch = useCallback(async () => {
    const id = ++requestId.current;
    setState((s) => ({ ...s, loading: true, error: '' }));
    try {
      const res = await apiRef.current();
      if (id !== requestId.current) return;
      setState({ data: res?.data ?? res, loading: false, error: '' });
    } catch (err) {
      if (id !== requestId.current) return;
      // Keep whatever data we already had — a failed refresh should not blank
      // out a table that is currently on screen.
      setState((s) => ({
        data: s.data,
        loading: false,
        error: apiErrorMessage(err, 'Failed to load data.'),
      }));
    }
  }, []);

  useEffect(() => { refetch(); }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  return { ...state, refetch };
}

/**
 * useFetch for endpoints that return a collection.
 *
 * Saves every list page from repeating `data?.results ?? data ?? []`, which
 * returned a non-array (and then threw on `.map`) for wrapped paginated
 * payloads.
 */
export function useList(apiFn, deps = []) {
  const { data, loading, error, refetch } = useFetch(apiFn, deps);
  const items = useMemo(() => unwrapList(data), [data]);
  return { items, data, loading, error, refetch };
}
