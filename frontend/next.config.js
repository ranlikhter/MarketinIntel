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
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
