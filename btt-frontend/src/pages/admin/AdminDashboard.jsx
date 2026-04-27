import { useFetch } from '../../hooks/useFetch';
import { getAnalytics } from '../../api/adminApi';
import { triggerReanalysis, getRecoveryRadius, getCorridors } from '../../api/mlApi';
import { StatCard, Spinner, Button } from '../../components/UI';
import { useState } from 'react';

export default function AdminDashboard() {
  const { data, loading, refetch } = useFetch(getAnalytics, []);
  const { data: rrData,  refetch: refetchRR  } = useFetch(getRecoveryRadius, []);  // national
  const { data: corData, refetch: refetchCor } = useFetch(getCorridors, []);       // national
  const [triggering, setTriggering] = useState(false);

  async function handleReanalysis() {
    setTriggering(true);
    try {
      await triggerReanalysis();
      // Analysis is now synchronous — refetch immediately so the cards update
      await Promise.all([refetchRR(), refetchCor()]);
      alert('ML reanalysis complete. Dashboard updated.');
    }
    catch (err) { alert(err.response?.data?.detail ?? err.message); }
    finally { setTriggering(false); }
  }

  if (loading) return <Spinner />;

  // API shape: { reports: {total, stolen, under_investigation, recovered, closed, recovery_rate_pct},
  //              city_breakdown: [{theft_city, count}],
  //              users: {total_users, owners, authorities, community},
  //              unverified_sightings }
  const rep = data?.reports ?? {};
  const usr = data?.users   ?? {};
  const cityBreakdown = data?.city_breakdown ?? [];
  const totalCities   = cityBreakdown.reduce((s, c) => s + (c.count ?? 0), 0);

  const activeCount = (rep.stolen ?? 0) + (rep.under_investigation ?? 0);

  // ML insight strips — null when cache is pending (backend returns { data: null })
  const radius    = rrData?.data ?? null;
  const corResult = corData?.data ?? null;
  const dominant   = corResult?.corridors?.[0] ?? null;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="page-title">Admin Dashboard</h1>
          <p className="page-sub m-0">Full-system KPI overview</p>
        </div>
        <Button variant="blue" loading={triggering} onClick={handleReanalysis}>⚡ Trigger ML Reanalysis</Button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Total Reports"    value={rep.total}                    icon="📋" />
        <StatCard label="Active Cases"     value={activeCount}                  icon="🚨" color="text-red-400" />
        <StatCard label="Recovery Rate"    value={rep.recovery_rate_pct != null ? `${Math.round(rep.recovery_rate_pct)}%` : '—'} icon="✅" color="text-emerald-400" />
        <StatCard label="Registered Users" value={usr.total_users}              icon="👥" color="text-blue-400" />
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <StatCard label="Stolen"             value={rep.stolen}             icon="🚨" color="text-red-400" />
        <StatCard label="Under Investigation" value={rep.under_investigation} icon="🔍" color="text-amber-400" />
        <StatCard label="Unverified Sightings" value={data?.unverified_sightings} icon="👁" color="text-purple-400" />
      </div>

      {/* City breakdown */}
      {cityBreakdown.length > 0 && (
        <div className="card mb-5">
          <h2 className="font-heading font-semibold text-sm text-gray-100 mb-4">Reports by City</h2>
          {cityBreakdown.map(({ theft_city, count }) => {
            const pct = totalCities ? Math.round(count / totalCities * 100) : 0;
            return (
              <div key={theft_city} className="flex items-center gap-3 mb-2">
                <div className="w-24 text-sm text-muted flex-shrink-0">{theft_city}</div>
                <div className="flex-1 progress"><div className="progress-bar" style={{ width: `${pct}%` }} /></div>
                <div className="w-20 text-right text-xs text-faint font-mono">{count} <span className="text-faint">({pct}%)</span></div>
              </div>
            );
          })}
        </div>
      )}

      {/* User breakdown */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <StatCard label="Bike Owners"   value={usr.owners}      icon="🏍" />
        <StatCard label="Authorities"   value={usr.authorities}  icon="🚔" color="text-blue-400" />
        <StatCard label="Community"     value={usr.community}    icon="👥" color="text-emerald-400" />
      </div>

      {/* ML Intelligence strip */}
      <div className="card">
        <h2 className="font-heading font-semibold text-sm text-gray-100 mb-4">🤖 ML Intelligence — National</h2>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-xs text-muted uppercase tracking-wider mb-1">Avg Recovery Distance</div>
            {radius
              ? <><span className="text-xl font-bold font-mono text-primary">{radius.mean_km} km</span>
                  <div className="text-xs text-faint mt-0.5">median {radius.median_km} km · {radius.record_count} cases</div></>
              : <span className="text-sm text-muted italic">Cache pending</span>}
          </div>
          <div>
            <div className="text-xs text-muted uppercase tracking-wider mb-1">Dominant Movement</div>
            {dominant
              ? <><span className="text-xl font-bold font-mono text-primary">{dominant.bearing_label}</span>
                  <span className="text-xs text-faint ml-2">~{dominant.mean_distance_km} km</span>
                  <div className="text-xs text-faint mt-0.5">{dominant.report_count} cases in this corridor</div></>
              : <span className="text-sm text-muted italic">Cache pending</span>}
          </div>
          <div>
            <div className="text-xs text-muted uppercase tracking-wider mb-1">Corridors Detected</div>
            {corResult
              ? <><span className="text-xl font-bold font-mono text-primary">{corResult.corridors?.length ?? 0}</span>
                  <div className="text-xs text-faint mt-0.5">{corResult.noise_points ?? 0} unclustered cases</div></>
              : <span className="text-sm text-muted italic">Cache pending</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
