import { useAuth } from '../../context/AuthContext';
import { useFetch } from '../../hooks/useFetch';
import { getBikes }   from '../../api/bikeApi';
import { getReports } from '../../api/reportApi';
import { StatCard, Spinner } from '../../components/UI';
import Badge from '../../components/UI/Badge';
import { STATUS_COLORS, STATUS_LABELS } from '../../utils/constants';
import { formatDate } from '../../utils/formatters';

export default function OwnerDashboard() {
  const { user } = useAuth();
  const { data: bikesData,   loading: lb } = useFetch(getBikes,   []);
  const { data: reportsData, loading: lr } = useFetch(getReports, []);

  const bikes   = bikesData?.results   ?? bikesData   ?? [];
  const reports = reportsData?.results ?? reportsData ?? [];

  const active    = reports.filter((r) => ['stolen', 'under_investigation'].includes(r.status)).length;
  const recovered = reports.filter((r) => r.status === 'recovered').length;

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  return (
    <div>
      <h1 className="page-title">{greeting}, {user?.full_name?.split(' ')[0] ?? 'there'} 👋</h1>
      <p className="page-sub">Here's the status of your registered vehicles.</p>

      {lb || lr ? <Spinner /> : (
        <>
          <div className="grid grid-cols-4 gap-3 mb-6">
            <StatCard label="My Bikes"    value={bikes.length}    icon="🏍"  />
            <StatCard label="Total Cases" value={reports.length}  icon="📋" color="text-primary" />
            <StatCard label="Active"      value={active}          icon="🚨" color="text-red-400" />
            <StatCard label="Recovered"   value={recovered}       icon="✅" color="text-emerald-400" />
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
                  {reports.slice(0, 6).map((r) => (
                    <tr key={r.id}>
                      <td className="mono text-gray-300">{r.bike_info?.engine_number ?? '—'}</td>
                      <td><Badge variant={STATUS_COLORS[r.status] ?? 'gray'}>{STATUS_LABELS[r.status] ?? r.status}</Badge></td>
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
