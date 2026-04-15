import Spinner from './Spinner';

const VARIANTS = {
  primary: 'btn-primary',
  ghost:   'btn-ghost',
  danger:  'btn-danger',
  blue:    'btn-blue',
  green:   'btn-green',
};

export default function Button({
  children, variant = 'ghost', size = 'md',
  loading = false, disabled = false,
  className = '', ...props
}) {
  return (
    <button
      className={`btn ${VARIANTS[variant] ?? ''} ${size === 'sm' ? 'btn-sm' : size === 'lg' ? 'btn-lg' : ''} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  );
}
