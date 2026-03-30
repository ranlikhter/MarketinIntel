const { withSentryConfig } = require('@sentry/nextjs');

const backendBase = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

/** @type {import('next').NextConfig} */
const isProd = process.env.NODE_ENV === 'production';

const nextConfig = {
  reactStrictMode: true,

  // Strip console.* calls in production builds (reduces bundle + leaks)
  compiler: {
    removeConsole: isProd ? { exclude: ['error', 'warn'] } : false,
  },

  // Optimise heavy packages so only used modules are bundled
  experimental: {
    optimizePackageImports: ['@sentry/nextjs'],
  },

  // Image optimisation — serve AVIF/WebP instead of raw JPEG/PNG
  images: {
    domains: ['m.media-amazon.com', 'i5.walmartimages.com'],
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    minimumCacheTTL: 86400, // 24h CDN cache for product images
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
