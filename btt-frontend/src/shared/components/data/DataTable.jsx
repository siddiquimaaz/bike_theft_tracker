import EmptyState from '@/shared/components/ui/EmptyState';
import Spinner from '@/shared/components/ui/Spinner';

/**
 * Generic table.
 * columns: [{ key, label, render?(val, row) => ReactNode, className?, tdClass? }]
 * rows:    array of objects
 */
export default function DataTable({
  columns,
  rows = [],
  loading,
  emptyIcon,
  emptyTitle,
  emptySubtitle,
  onRowClick,
}) {
  if (loading) return <Spinner />;

  return (
    <div className="card p-0 overflow-hidden">
      {rows.length === 0 ? (
        <EmptyState icon={emptyIcon} title={emptyTitle} subtitle={emptySubtitle} />
      ) : (
        <table className="tbl">
          <thead className="bg-btt-700">
            <tr>
              {columns.map((col) => (
                <th key={col.key} className={col.className}>{col.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={row.id ?? i}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={onRowClick ? 'cursor-pointer' : ''}
              >
                {columns.map((col) => (
                  <td key={col.key} className={col.tdClass}>
                    {col.render ? col.render(row[col.key], row) : (row[col.key] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
