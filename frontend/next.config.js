const backendBase = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Allow images from external domains (for product images)
  images: {
    domains: ['m.media-amazon.com', 'i5.walmartimages.com'],
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

module.exports = nextConfig;
