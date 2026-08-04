const DEFAULT_PENDING = 'Pending ML cache — trigger reanalysis';

/**
 * One ML insight tile.  Both dashboards render the same three (recovery
 * radius, dominant corridor, corridor count) and both need the identical
 * "cache not computed yet" fallback, which the backend signals with
 * `{ data: null }`.
 *
 * `variant="card"` is the standalone tile used on the authority dashboard;
 * `variant="plain"` is the flat column used inside the admin dashboard's
 * single ML strip, which is already a card.
 */
export default function InsightCard({
  icon,
  label,
  ready,
  children,
  variant = 'card',
  pendingText = DEFAULT_PENDING,
}) {
  const isCard = variant === 'card';

  const pending = isCard
    ? <div className="text-sm text-muted italic">{pendingText}</div>
    : <span className="text-sm text-muted italic">{pendingText}</span>;

  return (
    <div className={isCard ? 'card flex flex-col gap-1' : undefined}>
      <div className={isCard ? 'flex items-center gap-2 mb-1' : 'text-xs text-muted uppercase tracking-wider mb-1'}>
        {icon && <span className="text-lg">{icon}</span>}
        {isCard
          ? <span className="text-xs font-semibold text-muted uppercase tracking-wider">{label}</span>
          : label}
      </div>
      {ready ? children : pending}
    </div>
  );
}
