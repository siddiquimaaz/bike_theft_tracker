import { useLocation } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import { initials } from '@/shared/lib/formatters';

function breadcrumb(pathname) {
  return pathname
    .split('/')
    .filter(Boolean)
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(' / ');
}

export default function TopBar() {
  const { user } = useAuth();
  const { pathname } = useLocation();

  return (
    <header className="flex items-center justify-between px-7 py-4 border-b border-white/[.06] bg-btt-800/60 backdrop-blur-sm sticky top-0 z-30">
      <div className="text-sm text-faint">
        <span className="text-primary font-semibold">BTT</span>
        {' / '}
        <span className="text-muted">{breadcrumb(pathname)}</span>
      </div>

      <div className="flex items-center gap-2 px-3 py-1.5 bg-btt-700 rounded-btt border border-white/[.06]">
        <div className="avatar">{initials(user?.full_name ?? user?.email)}</div>
        <div>
          <div className="text-xs font-medium text-gray-100">{user?.full_name ?? user?.email}</div>
          <div className="text-[11px] text-faint capitalize">{user?.role}</div>
        </div>
      </div>
    </header>
  );
}
