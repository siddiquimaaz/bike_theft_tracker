import { useState, useEffect } from 'react';
import { getHotspots, triggerReanalysis } from '../../api/mlApi';
import { Spinner } from '../../components/UI';

const CITIES = ['Karachi', 'Lahore', 'Islamabad', 'Rawalpindi', 'Faisalabad', 'Multan', 'Peshawar'];

export default function HotspotPage() {
  const [city,      setCity]      = useState('Karachi');
  const [clusters,  setClusters]  = useState([]);
  const [meta,      setMeta]      = useState(null);   // { computed_at, expires_at, record_count }
  const [notice,    setNotice]    = useState('');     // 202 message
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState('');
  const [triggering, setTriggering] = useState(false);
  const [triggered,  setTriggered]  = useState(false);

  async function load() {
    setLoading(true);
    setError('');
    setNotice('');
    setClusters([]);
    setMeta(null);
    try {
      const { data, status } = await getHotspots(city);

      // 202 = cache stale / not yet computed
      if (status === 202) {
        setNotice(data?.message ?? 'Hotspot analysis not yet computed.');
        return;
      }

      // 200 — parse result_data which may be nested
      const resultData = data?.data ?? data;
      // Backend returns: { clusters: [...], noise_points, record_count, skipped }
      const rawClusters = resultData?.clusters ?? [];

      // Normalise field names: backend uses centroid_lat/lng + report_count
      const normalised = rawClusters.map((c) => ({
        ...c,
        center_lat:  c.centroid_lat  ?? c.center_lat  ?? c.latitude,
        center_lng:  c.centroid_lng  ?? c.center_lng  ?? c.longitude,
        count:       c.report_count  ?? c.count       ?? c.size ?? 0,
      }));

      setClusters(normalised);
      setMeta({
        computed_at:  data?.computed_at,
        expires_at:   data?.expires_at,
        record_count: data?.record_count ?? resultData?.record_count,
      });
    } catch (err) {
      setError(err.response?.data?.detail ?? err.response?.data?.error ?? err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [city]);

  async function handleTrigger() {
    setTriggering(true);
    setTriggered(false);
    try {
      await triggerReanalysis();
      setTriggered(true);
      // Reload after a short delay to give the background job time to write the cache
      setTimeout(() => { load(); setTriggered(false); }, 5000);
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message);
    } finally {
      setTriggering(false);
    }
  }

  const totalThefts  = clusters.reduce((s, c) => s + c.count, 0);
  const highestRisk  = clusters.length ? Math.max(...clusters.map((c) => c.count)) : 0;

  return (
    <div>
      <h1 className="page-title">Theft Hotspot Map</h1>
      <p className="page-sub">DBSCAN-clustered high-crime zones. Larger clusters = more thefts in that area.</p>

      {/* Controls */}
      <div className="flex items-center gap-3 mb-5 flex-wrap">
        <label className="m-0 text-sm text-muted">City:</label>
        <select className="w-48" value={city} onChange={(e) => setCity(e.target.value)}>
          {CITIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <button className="btn btn-sm" onClick={load} disabled={loading}>↻ Refresh</button>
        <button
          className="btn btn-sm btn-secondary"
          onClick={handleTrigger}
          disabled={triggering || loading}
          title="Triggers hotspot reanalysis in the background (admin action)"
        >
          {triggering ? 'Triggering…' : '⚡ Run Analysis'}
        </button>
      </div>

      {triggered && (
        <div className="alert alert-info mb-4">
          ✅ Analysis triggered! Page will reload in 5 seconds…
        </div>
      )}

      {loading ? <Spinner /> : error ? (
        <div className="alert alert-error">{error}</div>
      ) : notice ? (
        <div className="card py-10 text-center">
          <p className="text-muted mb-3">⏳ {notice}</p>
          <p className="text-sm text-muted">
            Click <strong>⚡ Run Analysis</strong> above to compute it now, or run:<br />
            <code className="mono text-xs">python manage.py run_hotspot_analysis --city {city}</code>
          </p>
        </div>
      ) : clusters.length === 0 ? (
        <div className="card text-center py-12 text-muted">
          No hotspot clusters found for <strong>{city}</strong> in the last 6 months.
          <br /><span className="text-xs mt-2 block">There may be insufficient data (minimum records required for DBSCAN).</span>
        </div>
      ) : (
        <>
          {/* Meta info */}
          {meta?.computed_at && (
            <p className="text-xs text-muted mb-4">
              Computed: {new Date(meta.computed_at).toLocaleString()} · Records analysed: {meta.record_count ?? '—'}
            </p>
          )}

          {/* Summary cards */}
          <div className="grid grid-cols-3 gap-3 mb-5">
            <div className="stat-card">
              <div className="stat-label">Clusters Identified</div>
              <div className="stat-value text-primary">{clusters.length}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total Thefts Mapped</div>
              <div className="stat-value">{totalThefts}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Highest Risk Cluster</div>
              <div className="stat-value text-red-400">{highestRisk}</div>
            </div>
          </div>

          {/* Cluster table */}
          <div className="card p-0 overflow-hidden">
            <div className="px-5 py-3 border-b border-white/[.06] bg-btt-700">
              <h2 className="font-heading font-semibold text-sm text-gray-100">Cluster Details</h2>
            </div>
            <table className="tbl">
              <thead className="bg-btt-700">
                <tr>
                  <th>#</th>
                  <th>Centre Latitude</th>
                  <th>Centre Longitude</th>
                  <th>Thefts</th>
                  <th>Radius (km)</th>
                </tr>
              </thead>
              <tbody>
                {clusters.map((c, i) => (
                  <tr key={i}>
                    <td className="mono text-primary">{i + 1}</td>
                    <td className="mono">{c.center_lat?.toFixed(5) ?? '—'}</td>
                    <td className="mono">{c.center_lng?.toFixed(5) ?? '—'}</td>
                    <td className="font-semibold text-amber-400">{c.count}</td>
                    <td className="text-muted">{c.radius_km ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 alert alert-info">
            💡 To visualise these coordinates on an interactive map, integrate <strong>React Leaflet</strong> (Phase 4).
          </div>
        </>
      )}
    </div>
  );
}
