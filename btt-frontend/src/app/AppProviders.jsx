import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '@/features/auth/AuthContext';
import { RoleProvider } from '@/features/auth/RoleContext';

/**
 * Single place the app's global providers are composed, so main.jsx stays a
 * three-line mount and tests can wrap components with the same stack.
 */
export default function AppProviders({ children }) {
  return (
    <BrowserRouter>
      <AuthProvider>
        <RoleProvider>
          {children}
        </RoleProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
