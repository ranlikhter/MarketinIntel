import '../styles/globals.css';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import * as Sentry from '@sentry/nextjs';
import { ToastProvider } from '../components/Toast';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { PwaProvider } from '../context/PwaContext';
import SentryErrorBoundary from '../components/SentryErrorBoundary';
import OnboardingWizard, { shouldShowOnboarding } from '../components/OnboardingWizard';

const ONBOARDING_SKIP_PATHS = ['/auth/', '/pricing', '/offline'];

function OnboardingGate() {
  const { user } = useAuth();
  const router = useRouter();
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!user) return;
    if (ONBOARDING_SKIP_PATHS.some(p => router.pathname.startsWith(p))) return;
    if (shouldShowOnboarding()) setShow(true);
  }, [user, router.pathname]);

  if (!show) return null;
  return <OnboardingWizard onDismiss={() => setShow(false)} />;
}

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
            <OnboardingGate />
            <Component {...pageProps} />
          </PwaProvider>
        </ToastProvider>
      </AuthProvider>
    </SentryErrorBoundary>
  );
}

export default MyApp;
