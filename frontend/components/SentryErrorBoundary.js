/**
 * SentryErrorBoundary
 *
 * Wraps the entire app to catch unhandled React render errors and report them
 * to Sentry. Shows a friendly fallback UI instead of a blank white screen.
 */

import * as Sentry from '@sentry/nextjs';
import Link from 'next/link';

export default function SentryErrorBoundary({ children }) {
  return (
    <Sentry.ErrorBoundary
      fallback={({ error, resetError }) => <ErrorFallback error={error} resetError={resetError} />}
      showDialog={false}
    >
      {children}
    </Sentry.ErrorBoundary>
  );
}

function ErrorFallback({ error, resetError }) {
  return (
    <div
      style={{ background: '#0f1117', minHeight: '100vh' }}
      className="flex items-center justify-center p-6"
    >
      <div
        className="w-full max-w-md rounded-2xl p-8 text-center shadow-xl"
        style={{
          background: '#1a1d27',
          border: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        {/* Error icon */}
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5"
          style={{ background: 'rgba(239,68,68,0.12)' }}
        >
          <svg className="w-9 h-9 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>

        <h1 className="text-xl font-bold text-white mb-2">Something went wrong</h1>
        <p className="text-sm mb-1" style={{ color: 'rgba(255,255,255,0.5)' }}>
          An unexpected error occurred. Our team has been notified automatically.
        </p>

        {process.env.NODE_ENV === 'development' && error?.message && (
          <pre
            className="text-xs text-left rounded-lg p-3 mt-4 mb-4 overflow-auto"
            style={{ background: 'rgba(239,68,68,0.08)', color: '#f87171', maxHeight: 160 }}
          >
            {error.message}
          </pre>
        )}

        <div className="flex flex-col gap-3 mt-6">
          <button
            onClick={resetError}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-white text-sm font-semibold rounded-xl transition-opacity hover:opacity-90"
            style={{ background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' }}
          >
            Try Again
          </button>
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-medium rounded-xl transition-colors hover:bg-white/10"
            style={{ color: 'rgba(255,255,255,0.6)', border: '1px solid rgba(255,255,255,0.1)' }}
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
