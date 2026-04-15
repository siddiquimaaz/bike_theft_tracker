import { useState, useEffect } from 'react';
import { getHotspots } from '../../api/mlApi';
import { Spinner } from '../../components/UI';

export default function HotspotPage() {
  const [city,    setCity]    = useState('Karachi');
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  async function load() {
    setLoading(true); setError('');
    try { const { data: d } = await getHotspots(city); setData(d); }
    catch (err) { setError(err.response?.data?.detail ?? err.message); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [city]);

  const clusters = data?.clusters ?? data?.results ?? data ?? [];

  return (
    <div>
      <h1 className="page-title">Theft Hotspot Map</h1>
      <p className="page-sub">DBSCAN-clustered high-crime zones. Larger clusters = more thefts in that area.</p>

      <div className="flex items-center gap-3 mb-5">
        <label className="m-0 text-sm text-muted">City:</label>
        <select className="w-48" value={city} onChange={(e) => setCity(e.target.value)}>
          {['Karachi', 'Lahore', 'Islamabad', 'Rawalpindi', 'Faisalabad', 'Multan', 'Peshawar'].map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {loading ? <Spinner /> : error ? (
        <div className="alert alert-error">{error}</div>
      ) : clusters.length === 0 ? (
        <div className="card text-center py-12 text-muted">No hotspot data available for {city}. Run <code className="mono">python manage.py run_hotspot_analysis --city {city}</code></div>
      ) : (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-3 gap-3 mb-5">
            <div className="stat-card">
              <div className="stat-label">Clusters Identified</div>
              <div className="stat-value text-primary">{clusters.length}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total Thefts Mapped</div>
              <div className="stat-value">{clusters.reduce((sum, c) => sum + (c.count ?? c.size ?? 0), 0)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Highest Risk Cluster</div>
              <div className="stat-value text-red-400">{Math.max(...clusters.map((c) => c.count ?? c.size ?? 0))}</div>
            </div>
          </div>

          {/* Cluster table */}
          <div className="card p-0 overflow-hidden">
            <div className="px-5 py-3 border-b border-white/[.06] bg-btt-700">
              <h2 className="font-heading font-semibold text-sm text-gray-100">Cluster Details</h2>
            </div>
            <table className="tbl">
              <thead className="bg-btt-700"><tr>
                <th>#</th><th>Centre Latitude</th><th>Centre Longitude</th><th>Thefts</th><th>Radius (km)</th>
              </tr></thead>
              <tbody>
                {clusters.map((c, i) => (
                  <tr key={i}>
                    <td className="mono text-primary">{i + 1}</td>
                    <td className="mono">{c.center_lat ?? c.latitude  ?? '—'}</td>
                    <td className="mono">{c.center_lng ?? c.longitude ?? '—'}</td>
                    <td className="font-semibold text-amber-400">{c.count ?? c.size ?? '—'}</td>
                    <td className="text-muted">{c.radius_km ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 alert alert-info">
            💡 To visualise these coordinates on an interactive map, integrate <strong>React Leaflet</strong> (Phase 4). Pass <code className="mono">center_lat / center_lng</code> from each cluster as markers.
          </div>
        </>
      )}
    </div>
  );
}
