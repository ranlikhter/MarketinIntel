// This file configures the Sentry SDK on the SERVER (Node.js) side.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.SENTRY_DSN,

  // Capture all server-side transactions (lower cost than client)
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.2 : 1.0,

  environment: process.env.NODE_ENV || 'development',
  release: process.env.NEXT_PUBLIC_APP_VERSION || 'unknown',

  enabled: process.env.NODE_ENV !== 'test',

  beforeSend(event) {
    // Strip sensitive headers from server-side events
    if (event.request?.headers) {
      delete event.request.headers['authorization'];
      delete event.request.headers['cookie'];
      delete event.request.headers['x-api-key'];
    }
    return event;
  },
});
