const { withSentryConfig } = require('@sentry/nextjs');

const backendBase = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Allow images from external domains (for product images)
  images: {
    domains: ['m.media-amazon.com', 'i5.walmartimages.com'],
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'Referrer-Policy', value: 'no-referrer-when-downgrade' },
          { key: 'Cross-Origin-Opener-Policy', value: 'same-origin-allow-popups' },
        ],
      },
    ];
  },
  // API proxy to avoid CORS issues during development
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendBase}/:path*`,
      },
    ];
  },
};

module.exports = withSentryConfig(nextConfig, {
  // Sentry webpack plugin options
  org: process.env.SENTRY_ORG || 'marketintel',
  project: process.env.SENTRY_PROJECT || 'marketintel-frontend',

  // Upload source maps to Sentry for readable stack traces in production
  silent: true, // suppress noisy output during builds

  // Automatically tree-shake Sentry logger statements to reduce bundle size
  disableLogger: true,

  // Tunnels Sentry requests through your own domain to avoid ad-blockers
  // tunnelRoute: '/monitoring',

  // Hides Sentry source map upload logs during CI builds
  hideSourceMaps: true,

  // Automatically instrument Next.js data fetching methods
  autoInstrumentServerFunctions: true,
  autoInstrumentMiddleware: true,
  autoInstrumentAppDirectory: false, // Using pages router, not app router
});
