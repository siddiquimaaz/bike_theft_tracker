import { useFetch, useList } from '@/shared/hooks/useFetch';
import { getAnalytics } from '../api';
import { getTrends } from '@/features/ml/api';
import PageHeader from '@/shared/components/layout/PageHeader';
import { StatCard, Spinner } from '@/shared/components/ui';

const MAX_MONTHS = 12;

const pct = (value) => (value != null ? `${Math.round(value)}%` : '—');

export default function AnalyticsPage() {
  const { data: analytics, loading: loadingAnalytics } = useFetch(getAnalytics, []);
  const { items: trends,   loading: loadingTrends }    = useList(getTrends, []);

  if (loadingAnalytics || loadingTrends) return <Spinner />;

  const a = analytics ?? {};
  const rows = trends.slice(0, MAX_MONTHS);

  return (
    <div>
      <PageHeader title="Analytics" subtitle="Trend analysis and ML insights" />

      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Total Reports" value={a.total_reports} icon="📋" />
        <StatCard label="Active Cases"  value={a.active_cases}  icon="🚨" color="text-red-400" />
        <StatCard label="Recovery Rate" value={pct(a.recovery_rate)} icon="✅" color="text-emerald-400" />
        <StatCard label="Total Users"   value={a.total_users}   icon="👥" color="text-blue-400" />
      </div>

      {rows.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <div className="px-5 py-3 border-b border-white/[.06] bg-btt-700 flex items-center justify-between">
            <h2 className="font-heading font-semibold text-sm text-gray-100">Monthly Theft Trends</h2>
            <span className="text-xs text-faint">Showing {rows.length} months</span>
          </div>
          <table className="tbl">
            <thead className="bg-btt-700"><tr>
              <th>Period</th><th>City</th><th>Thefts</th><th>Recoveries</th><th>Rate</th>
            </tr></thead>
            <tbody>
              {rows.map((row, i) => {
                const thefts     = row.theft_count    ?? row.thefts     ?? 0;
                const recoveries = row.recovery_count ?? row.recoveries ?? 0;
                const rate       = thefts > 0 ? Math.round((recoveries / thefts) * 100) : 0;
                return (
                  <tr key={`${row.month ?? row.period ?? i}-${row.city ?? ''}`}>
                    <td className="mono text-xs">{row.month ?? row.period ?? '—'}</td>
                    <td className="text-muted">{row.city ?? '—'}</td>
                    <td className="text-red-400 font-semibold">{thefts}</td>
                    <td className="text-emerald-400 font-semibold">{recoveries}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-16 progress"><div className="progress-bar bg-emerald-500" style={{ width: `${rate}%` }} /></div>
                        <span className="text-xs text-faint">{rate}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
