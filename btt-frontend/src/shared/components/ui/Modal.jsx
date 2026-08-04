import { useEffect, useRef } from 'react';

export default function Modal({ title, onClose, children, size = 'md' }) {
  // Held in a ref so an inline `onClose={() => ...}` (which every caller uses)
  // does not tear down and re-register the key listener on every render.
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') closeRef.current?.(); };
    document.addEventListener('keydown', handler);

    // Stop the page behind the overlay from scrolling with the modal open.
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handler);
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label={typeof title === 'string' ? title : undefined}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className={`modal ${size === 'lg' ? 'modal-lg' : ''}`.trim()}>
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-heading font-semibold text-base text-gray-100">{title}</h3>
          <button className="btn btn-ghost btn-sm" aria-label="Close" onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}
