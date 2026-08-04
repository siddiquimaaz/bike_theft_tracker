import { useList } from '@/shared/hooks/useFetch';
import { getAuditLogs } from '../api';
import PageHeader from '@/shared/components/layout/PageHeader';
import { Spinner, Badge, EmptyState } from '@/shared/components/ui';
import { statusColor, statusLabel } from '@/shared/lib/reportStatus';
import { formatDateTime } from '@/shared/lib/formatters';

export default function AuditLogsPage() {
  const { items: logs, loading } = useList(getAuditLogs, []);

  return (
    <div>
      <PageHeader
        title="Audit Logs"
        subtitle="Immutable record of every case status change — no entry is ever deleted."
      />

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
                            <Badge variant={statusColor(l.old_status)}>{statusLabel(l.old_status)}</Badge>
                            <span className="text-faint text-xs">→</span>
                            <Badge variant={statusColor(l.new_status)}>{statusLabel(l.new_status)}</Badge>
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
