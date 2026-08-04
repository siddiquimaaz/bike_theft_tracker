/**
 * Normalising helpers for the shapes DRF hands back.
 *
 * The API returns list payloads three different ways depending on whether the
 * viewset is paginated and whether it wraps its results, so every caller used
 * to repeat `data?.results ?? data ?? []`.  That fallback silently yields a
 * non-array when the payload is a wrapped page, which then blows up on `.map`.
 */
export function unwrapList(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.results)) return payload.results;
  if (Array.isArray(payload?.results?.results)) return payload.results.results;
  return [];
}

/**
 * Best-effort human-readable message from an Axios error.
 *
 * DRF reports failures as `{ detail }`, `{ error }`, a bare string, or a
 * field-keyed map of message arrays (`{ email: ['already taken'] }`), and the
 * old call sites each handled a different subset.
 */
export function apiErrorMessage(err, fallback = 'Something went wrong.') {
  const data = err?.response?.data;

  if (typeof data === 'string' && data.trim()) return data;

  if (data && typeof data === 'object') {
    if (typeof data.detail === 'string') return data.detail;
    if (typeof data.error === 'string') return data.error;

    const fieldErrors = Object.values(data)
      .flat()
      .filter((v) => typeof v === 'string' && v.trim());
    if (fieldErrors.length) return fieldErrors.join(' ');
  }

  return err?.message || fallback;
}
