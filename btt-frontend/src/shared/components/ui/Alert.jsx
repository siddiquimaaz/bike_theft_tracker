const TYPES = {
  error:   'alert-error',
  success: 'alert-success',
  info:    'alert-info',
  warn:    'alert-warn',
};

export default function Alert({ type = 'error', message, onClose, children }) {
  const body = message ?? children;
  if (!body) return null;

  return (
    <div className={`alert ${TYPES[type] ?? TYPES.info} flex items-start justify-between gap-2 mb-4`}>
      <span>{body}</span>
      {onClose && (
        <button onClick={onClose} className="text-current opacity-60 hover:opacity-100 ml-2 text-xs flex-shrink-0">✕</button>
      )}
    </div>
  );
}
