// This file configures the Sentry SDK on the CLIENT (browser) side.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Capture 10% of transactions for performance monitoring in production,
  // 100% in development so you can see every trace locally.
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

  // Capture 10% of sessions for session replay (records what the user did before an error).
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0, // always record on error

  // Show the Sentry dialog asking users to describe what they were doing before the error.
  // Only in production — avoids noise during dev.
  beforeSend(event) {
    if (process.env.NODE_ENV === 'development') {
      // Print errors to console in dev so we can see them without Sentry noise
      console.error('[Sentry] Event captured:', event);
    }
    return event;
  },

  integrations: [
    Sentry.replayIntegration({
      // Mask all text and block all media by default (GDPR-safe)
      maskAllText: true,
      blockAllMedia: true,
    }),
    Sentry.browserTracingIntegration(),
  ],

  environment: process.env.NODE_ENV || 'development',
  release: process.env.NEXT_PUBLIC_APP_VERSION || 'unknown',

  // Don't send errors from localhost in production builds
  enabled: process.env.NODE_ENV !== 'test',
});
