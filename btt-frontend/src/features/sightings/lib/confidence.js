import {
  MATCH_CONFIDENCE_THRESHOLDS,
  MATCH_CONFIDENCE_COLORS,
  MATCH_CONFIDENCE_BARS,
} from '@/shared/lib/constants';

/**
 * Band a fuzzy-match score into HIGH / MEDIUM / LOW.
 *
 * Four surfaces each carried their own copy of this ladder (two of them with
 * their own colour maps), so a threshold change had to be made in four places.
 */
export function matchConfidence(score) {
  if (score == null) return null;
  if (score >= MATCH_CONFIDENCE_THRESHOLDS.HIGH)   return 'HIGH';
  if (score >= MATCH_CONFIDENCE_THRESHOLDS.MEDIUM) return 'MEDIUM';
  return 'LOW';
}

export const confidenceColor = (confidence) => MATCH_CONFIDENCE_COLORS[confidence] ?? 'text-muted';
export const confidenceBar   = (confidence) => MATCH_CONFIDENCE_BARS[confidence] ?? 'bg-primary';
