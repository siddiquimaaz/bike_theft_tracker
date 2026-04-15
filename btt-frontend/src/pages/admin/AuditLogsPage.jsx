import { useFetch } from '../../hooks/useFetch';
import { getAuditLogs } from '../../api/adminApi';
import { Spinner, Badge, EmptyState } from '../../components/UI';
import { STATUS_COLORS, STATUS_LABELS } from '../../utils/constants';
import { formatDateTime } from '../../utils/formatters';

export default function AuditLogsPage() {
  const { data, loading } = useFetch(getAuditLogs, []);
  const logs = data?.results ?? data ?? [];

  return (
    <div>
      <h1 className="page-title">Audit Logs</h1>
      <p className="page-sub">Immutable record of every case status change — no entry is ever deleted.</p>

      {loading ? <Spinner /> : (
        <div className="card p-0 overflow-hidden">
          {logs.length === 0
            ? <EmptyState icon="📜" title="No audit entries yet" />
            : (
              <table className="tbl">
                <thead className="bg-btt-700"><tr>
                  <th>Timestamp</th><th>Report</th><th>Action</th><th>Changed By</th><th>Transition</th>
                </tr></thead>
                <tbody>
                  {logs.map((l) => (
                    <tr key={l.id}>
                      <td className="mono text-xs text-faint">{formatDateTime(l.timestamp)}</td>
                      <td><span className="mono text-primary">#{l.report ?? l.report_id ?? '—'}</span></td>
                      <td><Badge variant="blue">{l.action ?? 'status_change'}</Badge></td>
                      <td className="text-muted text-xs">{l.changed_by_email ?? l.user ?? '—'}</td>
                      <td>
                        {l.old_status && l.new_status && (
                          <div className="flex items-center gap-2">
                            <Badge variant={STATUS_COLORS[l.old_status] ?? 'gray'}>{STATUS_LABELS[l.old_status] ?? l.old_status}</Badge>
                            <span className="text-faint text-xs">→</span>
                            <Badge variant={STATUS_COLORS[l.new_status] ?? 'gray'}>{STATUS_LABELS[l.new_status] ?? l.new_status}</Badge>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>
      )}
    </div>
  );
}
