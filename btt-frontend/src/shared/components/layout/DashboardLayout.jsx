import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { NotificationsProvider } from '@/features/notifications/NotificationsContext';
import Spinner from '@/shared/components/ui/Spinner';
import Sidebar from './Sidebar';
import TopBar from './TopBar';

export default function DashboardLayout() {
  return (
    // Scoped to the authenticated area so the poll never runs on auth pages.
    <NotificationsProvider>
      <div className="flex min-h-screen bg-btt-900">
        <Sidebar />
        <div className="flex-1 flex flex-col" style={{ marginLeft: 220 }}>
          <TopBar />
          <main className="flex-1 p-7">
            <Suspense fallback={<Spinner />}>
              <Outlet />
            </Suspense>
          </main>
        </div>
      </div>
    </NotificationsProvider>
  );
}
