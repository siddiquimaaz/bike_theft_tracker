import Spinner from './Spinner';

const VARIANTS = {
  primary: 'btn-primary',
  ghost:   'btn-ghost',
  danger:  'btn-danger',
  blue:    'btn-blue',
  green:   'btn-green',
  warning: 'btn-warning',
};

const SIZES = { sm: 'btn-sm', md: '', lg: 'btn-lg' };

export default function Button({
  children, variant = 'ghost', size = 'md',
  loading = false, disabled = false,
  className = '', ...props
}) {
  const classes = ['btn', VARIANTS[variant] ?? VARIANTS.ghost, SIZES[size] ?? '', className]
    .filter(Boolean)
    .join(' ');

  return (
    <button className={classes} disabled={disabled || loading} {...props}>
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  );
}
