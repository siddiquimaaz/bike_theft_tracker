import { useState } from 'react';
import { ownerConfirmSighting } from '../api';
import { apiErrorMessage } from '@/shared/lib/http';
import { formatDate } from '@/shared/lib/formatters';
import { Alert } from '@/shared/components/ui';

const RESPONSES = [
  { value: 'yes',      label: "✅ That's my bike", className: 'bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/40 border-emerald-600/30' },
  { value: 'no',       label: '❌ Not my bike',    className: 'bg-red-600/20 text-red-400 hover:bg-red-600/40 border-red-600/30' },
  { value: 'not_sure', label: '🤷 Not sure',       className: 'bg-gray-600/20 text-gray-400 hover:bg-gray-600/40 border-gray-600/30' },
];

const PANEL_BORDER = { border: '1px solid rgba(251,191,36,.3)' };

/**
 * The owner-side handshake: sightings matched to one of my bikes that still
 * need a yes / no / not-sure answer before the authority can act.
 */
export default function OwnerSightingPrompts({ sightings, onResponded }) {
  const [respondingId, setRespondingId] = useState(null);
  const [error, setError] = useState('');

  if (!sightings.length) return null;

  async function respond(sightingId, response) {
    setRespondingId(sightingId);
    setError('');
    try {
      await ownerConfirmSighting(sightingId, response);
      onResponded?.();
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to submit response.'));
    } finally {
      setRespondingId(null);
    }
  }

  return (
    <div className="card mb-6" style={PANEL_BORDER}>
      <h2 className="font-heading font-semibold text-sm text-amber-300 mb-4">
        🔔 Sightings Awaiting Your Response ({sightings.length})
      </h2>

      <Alert type="error" message={error} onClose={() => setError('')} />

      <div className="flex flex-col gap-3">
        {sightings.map((s) => (
          <div key={s.id} className="rounded-lg p-4 flex items-start justify-between gap-4 bg-white/[.04]">
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-gray-100">
                {s.top_match_info?.make} {s.top_match_info?.model} spotted in {s.sighting_city}
              </div>
              <div className="text-xs text-muted mt-1">
                {formatDate(s.sighting_date)}
                {s.raw_engine_number && <> · Reported engine: <span className="mono">{s.raw_engine_number}</span></>}
                {s.fuzzy_match_score != null && <> · Match score: <span className="mono">{Number(s.fuzzy_match_score).toFixed(1)}</span></>}
              </div>
              {s.sighting_description && (
                <div className="text-xs text-faint mt-1 line-clamp-2">{s.sighting_description}</div>
              )}
              {s.owner_response_deadline && (
                <div className="text-xs text-amber-400/70 mt-1">
                  ⏱ Respond by {formatDate(s.owner_response_deadline)} — authority will act on your answer
                </div>
              )}
            </div>

            <div className="flex gap-2 flex-shrink-0 flex-wrap justify-end">
              {RESPONSES.map(({ value, label, className }) => (
                <button
                  key={value}
                  disabled={respondingId === s.id}
                  className={`px-3 py-1.5 rounded text-xs font-semibold border disabled:opacity-50 ${className}`}
                  onClick={() => respond(s.id, value)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
