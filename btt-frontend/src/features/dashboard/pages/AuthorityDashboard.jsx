import { useMemo } from 'react';
import { useAuth } from '@/features/auth/AuthContext';
import { useList, useFetch } from '@/shared/hooks/useFetch';
import { getReports } from '@/features/reports/api';
import { getSightings } from '@/features/sightings/api';
import { getRecoveryRadius, getCorridors } from '@/features/ml/api';
import CompassArrow from '@/features/ml/components/CompassArrow';
import InsightCard from '@/features/ml/components/InsightCard';
import ConfidenceScore from '@/features/sightings/components/ConfidenceScore';
import PageHeader from '@/shared/components/layout/PageHeader';
import { Badge, StatCard, Spinner } from '@/shared/components/ui';
import { countByStatus, isAwaitingTriage, isInvestigating, statusColor, statusLabel } from '@/shared/lib/reportStatus';
import { formatDate } from '@/shared/lib/formatters';

const PREVIEW_LIMIT = 5;

export default function AuthorityDashboard() {
  const { user } = useAuth();
  const city = user?.city || undefined;

  const { items: reports,   loading: loadingReports }   = useList(getReports, []);
  const { items: sightings, loading: loadingSightings } = useList(getSightings, []);
  // Pass city via arrow-function closure so useFetch actually forwards it
  const { data: rrData }  = useFetch(() => getRecoveryRadius(city), [city]);
  const { data: corData } = useFetch(() => getCorridors(city),      [city]);

  const stats = useMemo(() => ({
    awaiting: countByStatus(reports, isAwaitingTriage),
    ongoing:  countByStatus(reports, isInvestigating),
  }), [reports]);

  const unverified = useMemo(() => sightings.filter((s) => !s.is_verified), [sightings]);

  // ML: null when cache is pending (backend returns { data: null })
  const radius       = rrData?.data ?? null;
  const corResult    = corData?.data ?? null;
  const dominant     = corResult?.corridors?.[0] ?? null;
  const overallStats = corResult?.overall_stats ?? null;

  return (
    <div>
      <PageHeader
        title="Authority Dashboard"
        subtitle={`${city ? `${city} — ` : ''}Case management overview`}
      />

      {!city && (
        <div className="alert alert-error mb-5">
          ⚠️ Your account has no city assigned. All case data is city-scoped — contact an Admin to set your city before you can view reports.
        </div>
      )}

      {loadingReports || loadingSightings ? <Spinner /> : (
        <>
          {/* Case KPIs */}
          <div className="grid grid-cols-4 gap-3 mb-4">
            <StatCard label="Total Cases"         value={reports.length}    icon="📋" />
            <StatCard label="Awaiting Action"     value={stats.awaiting}    icon="🚨" color="text-red-400" />
            <StatCard label="Under Investigation" value={stats.ongoing}     icon="🔍" color="text-amber-400" />
            <StatCard label="Pending Sightings"   value={unverified.length} icon="👁" color="text-blue-400" />
          </div>

          {/* ML Intelligence cards */}
          <div className="grid grid-cols-3 gap-3 mb-6">
            <InsightCard icon="📍" label="Avg Recovery Distance" ready={!!radius}>
              <div className="text-2xl font-bold text-primary font-mono">{radius?.mean_km} km</div>
              <div className="text-xs text-faint">
                Median {radius?.median_km} km · Range {radius?.min_km}–{radius?.max_km} km
              </div>
              <div className="text-[10px] text-muted mt-1">
                Based on {radius?.record_count} recovered cases{city ? ` in ${city}` : ''}
              </div>
            </InsightCard>

            <InsightCard icon="🧭" label="Dominant Movement" ready={!!dominant || !!overallStats}>
              {dominant ? (
                <>
                  <div className="flex items-center gap-2">
                    <CompassArrow bearing={dominant.bearing_deg} />
                    <span className="text-2xl font-bold text-primary font-mono">{dominant.bearing_label}</span>
                  </div>
                  <div className="text-xs text-faint">~{dominant.mean_distance_km} km · {dominant.report_count} cases</div>
                  <div className="text-[10px] text-muted mt-1">
                    Most common theft→recovery direction{city ? ` in ${city}` : ''}
                  </div>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <CompassArrow bearing={overallStats?.dominant_bearing_deg} />
                    <span className="text-2xl font-bold text-primary font-mono">{overallStats?.dominant_bearing_label}</span>
                  </div>
                  <div className="text-xs text-faint">~{overallStats?.mean_distance_km} km overall</div>
                  <div className="text-[10px] text-muted mt-1">No dominant cluster — showing mean direction</div>
                </>
              )}
            </InsightCard>

            <InsightCard icon="🔀" label="Movement Corridors" ready={!!corResult} pendingText="Pending ML cache">
              <div className="text-2xl font-bold text-primary font-mono">{corResult?.corridors?.length ?? 0}</div>
              <div className="text-xs text-faint">{corResult?.noise_points ?? 0} unclustered cases</div>
              {corResult?.corridors?.slice(0, 3).map((c) => (
                <div key={c.corridor_id} className="text-[10px] text-muted">
                  {c.bearing_label} ~{c.mean_distance_km} km ({c.report_count} cases)
                </div>
              ))}
            </InsightCard>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Recent reports */}
            <div className="card p-0 overflow-hidden">
              <div className="px-5 py-3 border-b border-white/[.06]">
                <h2 className="font-heading font-semibold text-sm text-gray-100">Recent Reports</h2>
              </div>
              <table className="tbl">
                <thead className="bg-btt-700"><tr><th>ID</th><th>Status</th><th>Date</th></tr></thead>
                <tbody>
                  {reports.slice(0, PREVIEW_LIMIT).map((r) => (
                    <tr key={r.id}>
                      <td><span className="mono text-primary">#{r.id}</span></td>
                      <td><Badge variant={statusColor(r.status)}>{statusLabel(r.status)}</Badge></td>
                      <td className="text-faint text-xs">{formatDate(r.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Unverified sightings */}
            <div className="card p-0 overflow-hidden">
              <div className="px-5 py-3 border-b border-white/[.06]">
                <h2 className="font-heading font-semibold text-sm text-gray-100">Unverified Sightings</h2>
              </div>
              <table className="tbl">
                <thead className="bg-btt-700"><tr><th>ID</th><th>Confidence</th><th>City</th></tr></thead>
                <tbody>
                  {unverified.slice(0, PREVIEW_LIMIT).map((s) => (
                    <tr key={s.id}>
                      <td><span className="mono text-primary">#{s.id}</span></td>
                      <td><ConfidenceScore confidence={s.match_confidence} /></td>
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
