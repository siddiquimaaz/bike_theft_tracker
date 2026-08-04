import { useState } from 'react';
import { useFetch } from '@/shared/hooks/useFetch';
import { getAnalytics } from '../api';
import { triggerReanalysis, getRecoveryRadius, getCorridors } from '@/features/ml/api';
import InsightCard from '@/features/ml/components/InsightCard';
import PageHeader from '@/shared/components/layout/PageHeader';
import { Alert, Button, StatCard, Spinner } from '@/shared/components/ui';
import { apiErrorMessage } from '@/shared/lib/http';

const pct = (value) => (value != null ? `${Math.round(value)}%` : '—');

export default function AdminDashboard() {
  const { data, loading } = useFetch(getAnalytics, []);
  const { data: rrData,  refetch: refetchRR  } = useFetch(getRecoveryRadius, []);  // national
  const { data: corData, refetch: refetchCor } = useFetch(getCorridors, []);       // national

  const [triggering, setTriggering] = useState(false);
  const [notice,     setNotice]     = useState('');
  const [error,      setError]      = useState('');

  async function handleReanalysis() {
    setTriggering(true);
    setError('');
    setNotice('');
    try {
      await triggerReanalysis();
      // Analysis is now synchronous — refetch immediately so the cards update
      await Promise.all([refetchRR(), refetchCor()]);
      setNotice('ML reanalysis complete. Dashboard updated.');
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to trigger reanalysis.'));
    } finally {
      setTriggering(false);
    }
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

  // Derived from the terminal states rather than by adding up the two legacy
  // statuses, which missed every case filed through the current seven-step flow.
  const activeCount = Math.max(0, (rep.total ?? 0) - (rep.recovered ?? 0) - (rep.closed ?? 0));

  // ML insight strips — null when cache is pending (backend returns { data: null })
  const radius    = rrData?.data ?? null;
  const corResult = corData?.data ?? null;
  const dominant  = corResult?.corridors?.[0] ?? null;

  return (
    <div>
      <PageHeader
        title="Admin Dashboard"
        subtitle="Full-system KPI overview"
        action={
          <Button variant="blue" loading={triggering} onClick={handleReanalysis}>
            ⚡ Trigger ML Reanalysis
          </Button>
        }
      />

      <Alert type="success" message={notice} onClose={() => setNotice('')} />
      <Alert type="error"   message={error}  onClose={() => setError('')} />

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Total Reports"    value={rep.total}                 icon="📋" />
        <StatCard label="Active Cases"     value={activeCount}               icon="🚨" color="text-red-400" />
        <StatCard label="Recovery Rate"    value={pct(rep.recovery_rate_pct)} icon="✅" color="text-emerald-400" />
        <StatCard label="Registered Users" value={usr.total_users}           icon="👥" color="text-blue-400" />
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <StatCard label="Stolen"               value={rep.stolen}              icon="🚨" color="text-red-400" />
        <StatCard label="Under Investigation"  value={rep.under_investigation} icon="🔍" color="text-amber-400" />
        <StatCard label="Unverified Sightings" value={data?.unverified_sightings} icon="👁" color="text-purple-400" />
      </div>

      {/* City breakdown */}
      {cityBreakdown.length > 0 && (
        <div className="card mb-5">
          <h2 className="font-heading font-semibold text-sm text-gray-100 mb-4">Reports by City</h2>
          {cityBreakdown.map(({ theft_city, count }) => {
            const share = totalCities ? Math.round((count / totalCities) * 100) : 0;
            return (
              <div key={theft_city} className="flex items-center gap-3 mb-2">
                <div className="w-24 text-sm text-muted flex-shrink-0">{theft_city}</div>
                <div className="flex-1 progress"><div className="progress-bar" style={{ width: `${share}%` }} /></div>
                <div className="w-20 text-right text-xs text-faint font-mono">{count} <span className="text-faint">({share}%)</span></div>
              </div>
            );
          })}
        </div>
      )}

      {/* User breakdown */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <StatCard label="Bike Owners" value={usr.owners}      icon="🏍" />
        <StatCard label="Authorities" value={usr.authorities} icon="🚔" color="text-blue-400" />
        <StatCard label="Community"   value={usr.community}   icon="👥" color="text-emerald-400" />
      </div>

      {/* ML Intelligence strip */}
      <div className="card">
        <h2 className="font-heading font-semibold text-sm text-gray-100 mb-4">🤖 ML Intelligence — National</h2>
        <div className="grid grid-cols-3 gap-4">
          <InsightCard label="Avg Recovery Distance" ready={!!radius} variant="plain" pendingText="Cache pending">
            <span className="text-xl font-bold font-mono text-primary">{radius?.mean_km} km</span>
            <div className="text-xs text-faint mt-0.5">median {radius?.median_km} km · {radius?.record_count} cases</div>
          </InsightCard>

          <InsightCard label="Dominant Movement" ready={!!dominant} variant="plain" pendingText="Cache pending">
            <span className="text-xl font-bold font-mono text-primary">{dominant?.bearing_label}</span>
            <span className="text-xs text-faint ml-2">~{dominant?.mean_distance_km} km</span>
            <div className="text-xs text-faint mt-0.5">{dominant?.report_count} cases in this corridor</div>
          </InsightCard>

          <InsightCard label="Corridors Detected" ready={!!corResult} variant="plain" pendingText="Cache pending">
            <span className="text-xl font-bold font-mono text-primary">{corResult?.corridors?.length ?? 0}</span>
            <div className="text-xs text-faint mt-0.5">{corResult?.noise_points ?? 0} unclustered cases</div>
          </InsightCard>
        </div>
      </div>
    </div>
  );
}
