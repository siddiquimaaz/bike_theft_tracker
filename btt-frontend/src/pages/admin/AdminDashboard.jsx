import { useFetch } from '../../hooks/useFetch';
import { getAnalytics } from '../../api/adminApi';
import { triggerReanalysis } from '../../api/mlApi';
import { StatCard, Spinner, Button } from '../../components/UI';
import { useState } from 'react';

export default function AdminDashboard() {
  const { data, loading, refetch } = useFetch(getAnalytics, []);
  const [triggering, setTriggering] = useState(false);

  async function handleReanalysis() {
    setTriggering(true);
    try { await triggerReanalysis(); alert('ML reanalysis triggered successfully.'); }
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
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Bike Owners"   value={usr.owners}      icon="🏍" />
        <StatCard label="Authorities"   value={usr.authorities}  icon="🚔" color="text-blue-400" />
        <StatCard label="Community"     value={usr.community}    icon="👥" color="text-emerald-400" />
      </div>
    </div>
  );
}
