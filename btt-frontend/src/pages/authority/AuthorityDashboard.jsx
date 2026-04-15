import { useAuth } from '../../context/AuthContext';
import { useFetch } from '../../hooks/useFetch';
import { getReports }   from '../../api/reportApi';
import { getSightings } from '../../api/sightingApi';
import { StatCard, Spinner } from '../../components/UI';
import Badge from '../../components/UI/Badge';
import { STATUS_COLORS, STATUS_LABELS } from '../../utils/constants';
import { formatDate } from '../../utils/formatters';

export default function AuthorityDashboard() {
  const { user } = useAuth();
  const { data: rd, loading: lr } = useFetch(getReports,   []);
  const { data: sd, loading: ls } = useFetch(getSightings, []);

  const reports  = rd?.results ?? rd ?? [];
  const sightings = sd?.results ?? sd ?? [];

  const stolen    = reports.filter((r) => r.status === 'stolen').length;
  const ongoing   = reports.filter((r) => r.status === 'under_investigation').length;
  const pending   = sightings.filter((s) => !s.is_verified).length;

  return (
    <div>
      <h1 className="page-title">Authority Dashboard</h1>
      <p className="page-sub">{user?.city ? `${user.city} — ` : ''}Case management overview</p>

      {lr || ls ? <Spinner /> : (
        <>
          <div className="grid grid-cols-4 gap-3 mb-6">
            <StatCard label="Total Cases"        value={reports.length}  icon="📋" />
            <StatCard label="Awaiting Action"    value={stolen}          icon="🚨" color="text-red-400" />
            <StatCard label="Under Investigation" value={ongoing}         icon="🔍" color="text-amber-400" />
            <StatCard label="Pending Sightings"  value={pending}         icon="👁"  color="text-blue-400" />
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
                      <td className="text-faint text-xs">{formatDate(r.reported_at)}</td>
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
