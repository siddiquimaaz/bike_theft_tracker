import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useNotificationsCount } from '../hooks/useNotifications';
import { ROLE_LABELS, ROLE_COLORS } from '../utils/constants';
import Badge from './UI/Badge';
import { initials } from '../utils/formatters';

const NAV = {
  owner: [
    { to: '/owner/dashboard',      icon: '◈', label: 'Dashboard' },
    { to: '/owner/bikes',          icon: '🏍', label: 'My Bikes' },
    { to: '/owner/reports',        icon: '📋', label: 'My Reports' },
    { to: '/owner/notifications',  icon: '🔔', label: 'Notifications', notif: true },
  ],
  community: [
    { to: '/community/dashboard',  icon: '◈', label: 'Dashboard' },
    { to: '/community/sightings',  icon: '👁', label: 'Submit Sighting' },
    { to: '/community/notifications', icon: '🔔', label: 'Notifications', notif: true },
  ],
  authority: [
    { to: '/authority/dashboard',  icon: '◈', label: 'Dashboard' },
    { to: '/authority/reports',    icon: '📋', label: 'Case Reports' },
    { to: '/authority/sightings',  icon: '👁', label: 'Sightings' },
    { to: '/authority/fuzzy',      icon: '🔍', label: 'Fuzzy Search' },
    { to: '/authority/hotspots',   icon: '📍', label: 'Hotspot Map' },
    { to: '/authority/notifications', icon: '🔔', label: 'Notifications', notif: true },
  ],
  admin: [
    { to: '/admin/dashboard',      icon: '◈', label: 'Dashboard' },
    { to: '/admin/users',          icon: '👥', label: 'Users' },
    { to: '/admin/analytics',      icon: '📊', label: 'Analytics' },
    { to: '/admin/audit',          icon: '📜', label: 'Audit Logs' },
    { to: '/admin/notifications',  icon: '🔔', label: 'Notifications', notif: true },
  ],
};

export default function Sidebar() {
  const { user, role, logout } = useAuth();
  const { unread } = useNotificationsCount();
  const navigate   = useNavigate();
  const nav        = NAV[role] ?? [];

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-[220px] bg-btt-800 border-r border-white/[.06] flex flex-col z-40">
      {/* Logo */}
      <div className="px-4 pt-5 pb-4 border-b border-white/[.06]">
        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-lg mb-2.5">🏍️</div>
        <div className="font-heading font-bold text-sm text-gray-100">BTT System</div>
        <div className="text-[11px] text-faint">Bike Theft Tracker</div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-2">
        <p className="px-4 pt-3 pb-1.5 text-[10px] text-faint font-semibold uppercase tracking-widest">Navigation</p>
        {nav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              'nav-item' + (isActive ? ' active' : '')
            }
          >
            <span className="text-[15px] w-5 text-center flex-shrink-0">{item.icon}</span>
            <span className="flex-1">{item.label}</span>
            {item.notif && unread > 0 && (
              <span className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />
            )}
          </NavLink>
        ))}
      </nav>

      {/* User footer */}
      <div className="p-3 border-t border-white/[.06]">
        <div className="flex items-center gap-2 px-1 mb-2">
          <div className="avatar">{initials(user?.full_name ?? user?.email)}</div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-gray-100 truncate">{user?.full_name ?? user?.email}</div>
            <Badge variant={ROLE_COLORS[role]}>{ROLE_LABELS[role]}</Badge>
          </div>
        </div>
        <button className="btn btn-ghost btn-sm w-full justify-center" onClick={handleLogout}>
          Sign Out
        </button>
      </div>
    </aside>
  );
}
