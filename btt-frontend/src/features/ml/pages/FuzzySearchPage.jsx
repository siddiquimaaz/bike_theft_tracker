import { useState } from 'react';
import { fuzzyMatchEngine, fuzzyMatchChassis } from '../api';
import { confidenceColor, confidenceBar } from '@/features/sightings/lib/confidence';
import PageHeader from '@/shared/components/layout/PageHeader';
import { Alert, Button, Spinner, EmptyState } from '@/shared/components/ui';
import { unwrapList, apiErrorMessage } from '@/shared/lib/http';

const SEARCH_TYPES = [
  { value: 'engine',  label: '⚙️ Engine Number',  placeholder: 'Enter partial engine number…', fn: fuzzyMatchEngine },
  { value: 'chassis', label: '🔩 Chassis Number', placeholder: 'Enter partial chassis number…', fn: fuzzyMatchChassis },
];

export default function FuzzySearchPage() {
  const [type,    setType]    = useState('engine');
  const [query,   setQuery]   = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  const activeType = SEARCH_TYPES.find((t) => t.value === type) ?? SEARCH_TYPES[0];

  async function search(e) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const { data } = await activeType.fn(query);
      setResults(unwrapList(data));
    } catch (err) {
      setError(apiErrorMessage(err, 'Search failed.'));
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Fuzzy Number Search"
        subtitle="Find stolen bikes from partial or damaged engine / chassis numbers using RapidFuzz WRatio scoring."
      />

      <div className="card mb-5" style={{ maxWidth: 560 }}>
        <form onSubmit={search}>
          <div className="tab-bar mb-4">
            {SEARCH_TYPES.map((t) => (
              <button
                key={t.value}
                type="button"
                className={`tab${type === t.value ? ' active' : ''}`}
                onClick={() => setType(t.value)}
              >
                {t.label}
              </button>
            ))}
          </div>

          <Alert type="error" message={error} onClose={() => setError('')} />

          <div className="flex gap-2">
            <input
              className="flex-1"
              placeholder={activeType.placeholder}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              required
            />
            <Button variant="primary" type="submit" loading={loading} disabled={!query}>
              Search
            </Button>
          </div>
        </form>
      </div>

      {loading ? <Spinner /> : results !== null && (
        <div className="card p-0 overflow-hidden">
          {results.length === 0
            ? <EmptyState icon="🔍" title="No matches found" subtitle="Try a different partial number." />
            : (
              <table className="tbl">
                <thead className="bg-btt-700"><tr>
                  <th>Engine Number</th><th>Chassis Number</th><th>Make / Model</th><th>City</th><th>Confidence</th><th>Score</th>
                </tr></thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr key={r.bike_id ?? r.engine_number ?? i}>
                      <td className="mono">{r.engine_number ?? '—'}</td>
                      <td className="mono">{r.chassis_number ?? '—'}</td>
                      <td>{r.make ?? ''} {r.model ?? ''}</td>
                      <td className="text-muted">{r.city ?? '—'}</td>
                      <td><span className={`mono text-xs font-bold ${confidenceColor(r.confidence)}`}>{r.confidence ?? '—'}</span></td>
                      <td style={{ minWidth: 90 }}>
                        {r.score != null && (
                          <>
                            <div className={`mono text-xs ${confidenceColor(r.confidence)}`}>{Math.round(r.score)}%</div>
                            <div className="progress mt-1">
                              <div className={`progress-bar ${confidenceBar(r.confidence)}`} style={{ width: `${r.score}%` }} />
                            </div>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>
      )}
    </div>
  );
}
