import AppProviders from './AppProviders';
import AppRoutes from './router';

export default function App() {
  return (
    <AppProviders>
      <AppRoutes />
    </AppProviders>
  );
}
