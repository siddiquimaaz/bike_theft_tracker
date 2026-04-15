import { useState } from 'react';
import { fuzzyMatchEngine, fuzzyMatchChassis } from '../../api/mlApi';
import { Button, Spinner, EmptyState } from '../../components/UI';

const CONF_COLOR = { HIGH: 'text-emerald-400', MEDIUM: 'text-amber-400', LOW: 'text-red-400' };
const CONF_BAR   = { HIGH: 'bg-emerald-500',   MEDIUM: 'bg-amber-500',   LOW: 'bg-red-500'  };

export default function FuzzySearchPage() {
  const [type,    setType]    = useState('engine');
  const [query,   setQuery]   = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  async function search(e) {
    e.preventDefault(); setLoading(true); setError('');
    try {
      const fn   = type === 'engine' ? fuzzyMatchEngine : fuzzyMatchChassis;
      const { data } = await fn(query);
      setResults(data?.results ?? data ?? []);
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message ?? 'Search failed.');
      setResults([]);
    } finally { setLoading(false); }
  }

  return (
    <div>
      <h1 className="page-title">Fuzzy Number Search</h1>
      <p className="page-sub">Find stolen bikes from partial or damaged engine / chassis numbers using RapidFuzz WRatio scoring.</p>

      <div className="card mb-5" style={{ maxWidth: 560 }}>
        <form onSubmit={search}>
          <div className="tab-bar mb-4">
            {['engine', 'chassis'].map((t) => (
              <button key={t} type="button" className={`tab${type === t ? ' active' : ''}`} onClick={() => setType(t)}>
                {t === 'engine' ? '⚙️ Engine Number' : '🔩 Chassis Number'}
              </button>
            ))}
          </div>

          {error && <div className="alert alert-error mb-3">{error}</div>}

          <div className="flex gap-2">
            <input
              className="flex-1"
              placeholder={type === 'engine' ? 'Enter partial engine number…' : 'Enter partial chassis number…'}
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
                    <tr key={i}>
                      <td className="mono">{r.engine_number ?? '—'}</td>
                      <td className="mono">{r.chassis_number ?? '—'}</td>
                      <td>{r.make ?? ''} {r.model ?? ''}</td>
                      <td className="text-muted">{r.city ?? '—'}</td>
                      <td><span className={`mono text-xs font-bold ${CONF_COLOR[r.confidence] ?? 'text-muted'}`}>{r.confidence ?? '—'}</span></td>
                      <td style={{ minWidth: 90 }}>
                        {r.score != null && (
                          <>
                            <div className={`mono text-xs ${CONF_COLOR[r.confidence] ?? 'text-muted'}`}>{Math.round(r.score)}%</div>
                            <div className="progress mt-1"><div className={`progress-bar ${CONF_BAR[r.confidence] ?? 'bg-primary'}`} style={{ width: `${r.score}%` }} /></div>
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
