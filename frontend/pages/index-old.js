import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import api from '../lib/api';

export default function Home() {
  const [stats, setStats] = useState({
    products: 0,
    competitors: 0,
    matches: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const [products, competitors] = await Promise.all([
        api.getProducts(),
        api.getCompetitors(),
      ]);

      // Calculate total matches
      const totalMatches = products.reduce((sum, p) => sum + (p.competitor_count || 0), 0);

      setStats({
        products: products.length,
        competitors: competitors.length,
        matches: totalMatches,
      });
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      {/* Hero Section */}
      <div className="bg-white shadow rounded-lg p-8 mb-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Welcome to MarketIntel
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Monitor competitor pricing across ANY website - automatically
          </p>
          <div className="flex justify-center space-x-4">
            <Link
              href="/products/add"
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700"
            >
              Add Your First Product
            </Link>
            <Link
              href="/competitors"
              className="inline-flex items-center px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              Manage Competitors
            </Link>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3 mb-8">
        <StatCard
          title="Products Monitored"
          value={stats.products}
          loading={loading}
          icon="📦"
          color="blue"
        />
        <StatCard
          title="Competitor Matches"
          value={stats.matches}
          loading={loading}
          icon="🎯"
          color="green"
        />
        <StatCard
          title="Competitors Tracked"
          value={stats.competitors}
          loading={loading}
          icon="🏪"
          color="purple"
        />
      </div>

      {/* Features Grid */}
      <div className="bg-white shadow rounded-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">
          Key Features
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FeatureCard
            icon="🔍"
            title="Smart Product Matching"
            description="Automatically find your products on competitor websites using AI-powered matching"
          />
          <FeatureCard
            icon="📊"
            title="Price History Tracking"
            description="Track price changes over time with beautiful charts and historical data"
          />
          <FeatureCard
            icon="🌐"
            title="Custom Competitors"
            description="Monitor ANY website - not just marketplaces. Add private competitors with custom CSS selectors"
          />
          <FeatureCard
            icon="⚡"
            title="Real-time Scraping"
            description="Get up-to-date pricing data with our powerful scraping engine that bypasses anti-bot protection"
          />
        </div>
      </div>

      {/* Getting Started */}
      <div className="bg-primary-50 border border-primary-200 rounded-lg p-6 mt-8">
        <h3 className="text-lg font-semibold text-primary-900 mb-3">
          Getting Started
        </h3>
        <ol className="list-decimal list-inside space-y-2 text-primary-800">
          <li>Add a product you want to monitor</li>
          <li>Search for it on Amazon or add a specific competitor URL</li>
          <li>View competitor prices and price history</li>
          <li>Get alerts when competitor prices drop (coming soon!)</li>
        </ol>
      </div>
    </Layout>
  );
}

function StatCard({ title, value, loading, icon, color }) {
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    purple: 'bg-purple-500',
  };

  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-5">
        <div className="flex items-center">
          <div className={`flex-shrink-0 ${colorClasses[color]} rounded-md p-3`}>
            <span className="text-2xl">{icon}</span>
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">
                {title}
              </dt>
              <dd className="text-3xl font-semibold text-gray-900">
                {loading ? (
                  <span className="animate-pulse">...</span>
                ) : (
                  value
                )}
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}

function FeatureCard({ icon, title, description }) {
  return (
    <div className="flex">
      <div className="flex-shrink-0">
        <span className="text-3xl">{icon}</span>
      </div>
      <div className="ml-4">
        <h4 className="text-lg font-medium text-gray-900">{title}</h4>
        <p className="mt-2 text-base text-gray-500">{description}</p>
      </div>
    </div>
  );
}
