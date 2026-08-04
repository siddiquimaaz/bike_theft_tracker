const SIZES = { sm: 'w-4 h-4', md: 'w-5 h-5', lg: 'w-8 h-8' };

export default function Spinner({ fullscreen = false, size = 'md' }) {
  const inner = (
    <div className="flex items-center justify-center gap-3 text-muted text-sm">
      <span className={`spinner ${SIZES[size] ?? SIZES.md}`} />
      Loading…
    </div>
  );

  if (fullscreen) {
    return (
      <div className="fixed inset-0 bg-btt-900 flex items-center justify-center z-50">
        {inner}
      </div>
    );
  }
  return <div className="flex items-center justify-center py-12">{inner}</div>;
}
