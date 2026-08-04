const COLOR_MAP = {
  amber:  'badge-amber',
  blue:   'badge-blue',
  green:  'badge-green',
  red:    'badge-red',
  orange: 'badge-orange',
  purple: 'badge-purple',
  gray:   'badge-gray',
};

export default function Badge({ children, variant = 'gray', className = '' }) {
  return (
    <span className={`badge ${COLOR_MAP[variant] ?? COLOR_MAP.gray} ${className}`.trim()}>
      {children}
    </span>
  );
}
