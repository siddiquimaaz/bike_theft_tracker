import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import TopBar  from '../components/TopBar';

export default function DashboardLayout() {
  return (
    <div className="flex min-h-screen bg-btt-900">
      <Sidebar />
      <div className="flex-1 flex flex-col" style={{ marginLeft: 220 }}>
        <TopBar />
        <main className="flex-1 p-7">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
