import { useMemo } from 'react';
import { useAuth } from '@/features/auth/AuthContext';
import { useList } from '@/shared/hooks/useFetch';
import { getBikes } from '@/features/bikes/api';
import { getReports } from '@/features/reports/api';
import PageHeader from '@/shared/components/layout/PageHeader';
import { Badge, StatCard, Spinner } from '@/shared/components/ui';
import { countByStatus, isActiveCase, isResolved, statusColor, statusLabel } from '@/shared/lib/reportStatus';
import { formatDate } from '@/shared/lib/formatters';

const RECENT_LIMIT = 6;

function greeting(hour = new Date().getHours()) {
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export default function OwnerDashboard() {
  const { user } = useAuth();
  const { items: bikes,   loading: loadingBikes }   = useList(getBikes, []);
  const { items: reports, loading: loadingReports } = useList(getReports, []);

  const { active, recovered } = useMemo(() => ({
    active:    countByStatus(reports, isActiveCase),
    recovered: countByStatus(reports, isResolved),
  }), [reports]);

  const firstName = user?.full_name?.split(' ')[0] ?? 'there';

  return (
    <div>
      <PageHeader
        title={`${greeting()}, ${firstName} 👋`}
        subtitle="Here's the status of your registered vehicles."
      />

      {loadingBikes || loadingReports ? <Spinner /> : (
        <>
          <div className="grid grid-cols-4 gap-3 mb-6">
            <StatCard label="My Bikes"    value={bikes.length}   icon="🏍" />
            <StatCard label="Total Cases" value={reports.length} icon="📋" color="text-primary" />
            <StatCard label="Active"      value={active}         icon="🚨" color="text-red-400" />
            <StatCard label="Recovered"   value={recovered}      icon="✅" color="text-emerald-400" />
          </div>

          {reports.length > 0 && (
            <div className="card p-0 overflow-hidden">
              <div className="px-5 py-3.5 border-b border-white/[.06]">
                <h2 className="font-heading font-semibold text-sm text-gray-100">Recent Reports</h2>
              </div>
              <table className="tbl">
                <thead className="bg-btt-700"><tr>
                  <th>Engine #</th><th>Status</th><th>City</th><th>Date</th>
                </tr></thead>
                <tbody>
                  {reports.slice(0, RECENT_LIMIT).map((r) => (
                    <tr key={r.id}>
                      <td className="mono text-gray-300">{r.bike_info?.engine_number ?? '—'}</td>
                      <td><Badge variant={statusColor(r.status)}>{statusLabel(r.status)}</Badge></td>
                      <td className="text-muted">{r.theft_city ?? '—'}</td>
                      <td className="text-faint text-xs">{formatDate(r.theft_date ?? r.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
