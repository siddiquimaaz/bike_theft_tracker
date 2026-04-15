export default function EmptyState({ icon = '📋', title = 'Nothing here yet', subtitle = '' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-4xl opacity-30 mb-3">{icon}</div>
      <p className="text-sm text-muted font-medium">{title}</p>
      {subtitle && <p className="text-xs text-faint mt-1">{subtitle}</p>}
    </div>
  );
}
