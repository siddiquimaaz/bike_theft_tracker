export default function StatCard({ label, value, sub, color = 'text-gray-100', icon }) {
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between">
        <div>
          <p className="stat-label">{label}</p>
          <p className={`stat-value ${color}`}>{value ?? '—'}</p>
          {sub && <p className="text-[11px] text-muted mt-1">{sub}</p>}
        </div>
        {icon && <span className="text-2xl opacity-40">{icon}</span>}
      </div>
    </div>
  );
}
