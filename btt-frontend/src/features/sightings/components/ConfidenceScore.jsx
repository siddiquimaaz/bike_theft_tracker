import { matchConfidence, confidenceColor } from '../lib/confidence';

/**
 * Renders a fuzzy-match confidence band, optionally with its percentage.
 *
 * Pass `score` to derive the band, or `confidence` when the API already
 * returned one (fuzzy search and the sightings feed both do).
 */
export default function ConfidenceScore({ score, confidence, scoreFormat = 'paren', className = '' }) {
  const band = confidence ?? matchConfidence(score);

  if (!band) return <span className="mono text-xs text-muted">—</span>;

  const rounded = score == null ? null : Math.round(score);
  const suffix = rounded == null
    ? ''
    : scoreFormat === 'dash' ? ` — ${rounded}%` : ` (${rounded}%)`;

  return (
    <span className={`mono text-xs font-semibold ${confidenceColor(band)} ${className}`.trim()}>
      {band}{suffix}
    </span>
  );
}
