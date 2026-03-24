import '../styles/globals.css';
import { useEffect } from 'react';
import * as Sentry from '@sentry/nextjs';
import { ToastProvider } from '../components/Toast';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { PwaProvider } from '../context/PwaContext';
import SentryErrorBoundary from '../components/SentryErrorBoundary';

// Inner component so it can access the AuthContext
function SentryUserSync() {
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      // Attach user identity to every Sentry event — makes debugging much easier
      Sentry.setUser({
        id: String(user.id),
        email: user.email,
        username: user.full_name || user.email,
      });
    } else {
      // Clear user context on logout
      Sentry.setUser(null);
    }
  }, [user]);

  return null;
}

function MyApp({ Component, pageProps }) {
  return (
    <SentryErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <PwaProvider>
            <SentryUserSync />
            <Component {...pageProps} />
          </PwaProvider>
        </ToastProvider>
      </AuthProvider>
    </SentryErrorBoundary>
  );
}

export default MyApp;
