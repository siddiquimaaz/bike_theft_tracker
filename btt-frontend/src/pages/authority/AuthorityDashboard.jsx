import { useAuth } from '../../context/AuthContext';
import { useFetch } from '../../hooks/useFetch';
import { getReports }        from '../../api/reportApi';
import { getSightings }      from '../../api/sightingApi';
import { getRecoveryRadius, getCorridors } from '../../api/mlApi';
import { StatCard, Spinner } from '../../components/UI';
import Badge from '../../components/UI/Badge';
import { STATUS_COLORS, STATUS_LABELS } from '../../utils/constants';
import { formatDate } from '../../utils/formatters';

/** Compass rose arrow — rendered inline without any extra deps */
function CompassArrow({ bearing }) {
  return (
    <span
      style={{ display: 'inline-block', transform: `rotate(${bearing}deg)`, fontSize: '1.25rem', lineHeight: 1 }}
      title={`${bearing}°`}
    >
      ↑
    </span>
  );
}

export default function AuthorityDashboard() {
  const { user } = useAuth();
  const city = user?.city || undefined;

  const { data: rd, loading: lr } = useFetch(getReports,   []);
  const { data: sd, loading: ls } = useFetch(getSightings, []);
  // Pass city via arrow-function closure so useFetch actually forwards it
  const { data: rrData }  = useFetch(() => getRecoveryRadius(city), [city]);
  const { data: corData } = useFetch(() => getCorridors(city),      [city]);

  const reports   = rd?.results ?? rd ?? [];
  const sightings = sd?.results ?? sd ?? [];

  const stolen  = reports.filter((r) => r.status === 'stolen').length;
  const ongoing = reports.filter((r) => r.status === 'under_investigation').length;
  const pending = sightings.filter((s) => !s.is_verified).length;

  // ML: null when cache is pending (backend returns { data: null })
  const radius    = rrData?.data ?? null;
  const corResult = corData?.data ?? null;
  const dominant  = corResult?.corridors?.[0] ?? null;
  const overallStats = corResult?.overall_stats ?? null;

  return (
    <div>
      <h1 className="page-title">Authority Dashboard</h1>
      <p className="page-sub">{city ? `${city} — ` : ''}Case management overview</p>

      {!city && (
        <div className="alert alert-error mb-5">
          ⚠️ Your account has no city assigned. All case data is city-scoped — contact an Admin to set your city before you can view reports.
        </div>
      )}

      {lr || ls ? <Spinner /> : (
        <>
          {/* Case KPIs */}
          <div className="grid grid-cols-4 gap-3 mb-4">
            <StatCard label="Total Cases"         value={reports.length} icon="📋" />
            <StatCard label="Awaiting Action"     value={stolen}         icon="🚨" color="text-red-400" />
            <StatCard label="Under Investigation" value={ongoing}        icon="🔍" color="text-amber-400" />
            <StatCard label="Pending Sightings"   value={pending}        icon="👁"  color="text-blue-400" />
          </div>

          {/* ML Intelligence cards */}
          <div className="grid grid-cols-3 gap-3 mb-6">
            {/* Recovery radius */}
            <div className="card flex flex-col gap-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-lg">📍</span>
                <span className="text-xs font-semibold text-muted uppercase tracking-wider">Avg Recovery Distance</span>
              </div>
              {radius ? (
                <>
                  <div className="text-2xl font-bold text-primary font-mono">{radius.mean_km} km</div>
                  <div className="text-xs text-faint">
                    Median {radius.median_km} km · Range {radius.min_km}–{radius.max_km} km
                  </div>
                  <div className="text-[10px] text-muted mt-1">Based on {radius.record_count} recovered cases{city ? ` in ${city}` : ''}</div>
                </>
              ) : (
                <div className="text-sm text-muted italic">Pending ML cache — trigger reanalysis</div>
              )}
            </div>

            {/* Dominant corridor */}
            <div className="card flex flex-col gap-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-lg">🧭</span>
                <span className="text-xs font-semibold text-muted uppercase tracking-wider">Dominant Movement</span>
              </div>
              {dominant ? (
                <>
                  <div className="flex items-center gap-2">
                    <CompassArrow bearing={dominant.bearing_deg} />
                    <span className="text-2xl font-bold text-primary font-mono">{dominant.bearing_label}</span>
                  </div>
                  <div className="text-xs text-faint">~{dominant.mean_distance_km} km · {dominant.report_count} cases</div>
                  <div className="text-[10px] text-muted mt-1">Most common theft→recovery direction{city ? ` in ${city}` : ''}</div>
                </>
              ) : overallStats ? (
                <>
                  <div className="flex items-center gap-2">
                    <CompassArrow bearing={overallStats.dominant_bearing_deg} />
                    <span className="text-2xl font-bold text-primary font-mono">{overallStats.dominant_bearing_label}</span>
                  </div>
                  <div className="text-xs text-faint">~{overallStats.mean_distance_km} km overall</div>
                  <div className="text-[10px] text-muted mt-1">No dominant cluster — showing mean direction</div>
                </>
              ) : (
                <div className="text-sm text-muted italic">Pending ML cache — trigger reanalysis</div>
              )}
            </div>

            {/* Corridor count */}
            <div className="card flex flex-col gap-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-lg">🔀</span>
                <span className="text-xs font-semibold text-muted uppercase tracking-wider">Movement Corridors</span>
              </div>
              {corResult ? (
                <>
                  <div className="text-2xl font-bold text-primary font-mono">{corResult.corridors?.length ?? 0}</div>
                  <div className="text-xs text-faint">{corResult.noise_points ?? 0} unclustered cases</div>
                  {corResult.corridors?.slice(0, 3).map((c) => (
                    <div key={c.corridor_id} className="text-[10px] text-muted">
                      {c.bearing_label} ~{c.mean_distance_km} km ({c.report_count} cases)
                    </div>
                  ))}
                </>
              ) : (
                <div className="text-sm text-muted italic">Pending ML cache</div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Recent reports */}
            <div className="card p-0 overflow-hidden">
              <div className="px-5 py-3 border-b border-white/[.06]"><h2 className="font-heading font-semibold text-sm text-gray-100">Recent Reports</h2></div>
              <table className="tbl">
                <thead className="bg-btt-700"><tr><th>ID</th><th>Status</th><th>Date</th></tr></thead>
                <tbody>
                  {reports.slice(0, 5).map((r) => (
                    <tr key={r.id}>
                      <td><span className="mono text-primary">#{r.id}</span></td>
                      <td><Badge variant={STATUS_COLORS[r.status] ?? 'gray'}>{STATUS_LABELS[r.status] ?? r.status}</Badge></td>
                      <td className="text-faint text-xs">{formatDate(r.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Unverified sightings */}
            <div className="card p-0 overflow-hidden">
              <div className="px-5 py-3 border-b border-white/[.06]"><h2 className="font-heading font-semibold text-sm text-gray-100">Unverified Sightings</h2></div>
              <table className="tbl">
                <thead className="bg-btt-700"><tr><th>ID</th><th>Confidence</th><th>City</th></tr></thead>
                <tbody>
                  {sightings.filter((s) => !s.is_verified).slice(0, 5).map((s) => (
                    <tr key={s.id}>
                      <td><span className="mono text-primary">#{s.id}</span></td>
                      <td>
                        <span className={`mono text-xs font-semibold ${
                          s.match_confidence === 'HIGH' ? 'text-emerald-400'
                          : s.match_confidence === 'MEDIUM' ? 'text-amber-400'
                          : s.match_confidence === 'LOW' ? 'text-red-400'
                          : 'text-muted'
                        }`}>{s.match_confidence ?? '—'}</span>
                      </td>
                      <td className="text-muted">{s.city ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
