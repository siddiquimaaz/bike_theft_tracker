export function normalizeNotificationList(data) {
  // Supports both shapes:
  // 1) { unread_count, results: [...] }
  // 2) { unread_count, results: { count, next, previous, results: [...] } }
  // and falls back safely for legacy payloads.
  const outer = data?.results ?? data?.notifications ?? data ?? [];
  if (Array.isArray(outer)) return outer;
  if (Array.isArray(outer?.results)) return outer.results;
  return [];
}
