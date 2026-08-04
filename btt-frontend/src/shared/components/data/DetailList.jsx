/**
 * Key/value read-out used inside detail modals.
 *
 * rows: [[label, value], ...] — entries with an empty value are dropped, which
 * is what each detail modal used to do inline with its own `.filter`.
 */
export default function DetailList({ rows, className = '', labelWidth = 'w-28', valueClassName = '' }) {
  const visible = rows.filter(([, value]) => value !== null && value !== undefined && value !== '');
  if (!visible.length) return null;

  return (
    <table className={`tbl ${className}`.trim()}>
      <tbody>
        {visible.map(([label, value]) => (
          <tr key={label}>
            <td className={`text-faint text-xs ${labelWidth} border-none py-1`}>{label}</td>
            <td className={`text-sm text-gray-100 border-none py-1 ${valueClassName}`.trim()}>{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
