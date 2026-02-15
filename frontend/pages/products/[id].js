import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { PriceHistoryChart, TrendIndicator } from '../../components/Charts';
import { useToast } from '../../components/Toast';
import { LoadingSpinner, SkeletonCard, SkeletonChart } from '../../components/LoadingStates';
import api from '../../lib/api';

export default function ProductDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const { addToast } = useToast();

  const [product, setProduct] = useState(null);
  const [matches, setMatches] = useState([]);
  const [priceHistory, setPriceHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);

  useEffect(() => {
    if (id) {
      loadProductData();
    }
  }, [id]);

  const loadProductData = async () => {
    try {
      setLoading(true);
      const [productData, matchesData, historyData] = await Promise.all([
        api.getProduct(id),
        api.getProductMatches(id),
        api.getProductPriceHistory(id)
      ]);

      setProduct(productData);
      setMatches(matchesData);
      setPriceHistory(historyData);
    } catch (error) {
      console.error('Failed to load product:', error);
      addToast('Failed to load product data', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleScrapeAmazon = async () => {
    setScraping(true);
    addToast('Starting Amazon scrape...', 'info');

    try {
      await api.scrapeProduct(id, 'amazon.com', 5);
      addToast('Amazon scrape completed!', 'success');
      await loadProductData();
    } catch (error) {
      console.error('Scrape failed:', error);
      addToast('Scrape failed. Please try again.', 'error');
    } finally {
      setScraping(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="space-y-6">
          <div className="h-32 bg-gray-200 rounded-lg animate-pulse" />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <SkeletonChart />
        </div>
      </Layout>
    );
  }

  if (!product) {
    return (
      <Layout>
        <div className="text-center py-12">
          <p className="text-gray-500">Product not found</p>
          <Link href="/products" className="text-primary-600 hover:text-primary-700 mt-4 inline-block">
            Back to Products
          </Link>
        </div>
      </Layout>
    );
  }

  const latestPrice = matches.length > 0 ? Math.min(...matches.map(m => m.latest_price)) : null;
  const avgPrice = matches.length > 0
    ? matches.reduce((sum, m) => sum + m.latest_price, 0) / matches.length
    : null;

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-2xl shadow-xl p-8 text-white">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <Link href="/products" className="text-primary-100 hover:text-white text-sm font-medium inline-flex items-center gap-1 mb-4">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back to Products
              </Link>
              <h1 className="text-3xl font-bold mb-2">{product.title}</h1>
              <div className="flex items-center gap-4 text-primary-100">
                {product.brand && <span>Brand: {product.brand}</span>}
                {product.sku && <span>SKU: {product.sku}</span>}
                <span className="inline-flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {new Date(product.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>

            {product.image_url && (
              <img
                src={product.image_url}
                alt={product.title}
                className="w-32 h-32 rounded-lg object-cover shadow-lg border-4 border-white/20"
                onError={(e) => e.target.style.display = 'none'}
              />
            )}
          </div>

          <div className="mt-6 flex gap-3">
            <button
              onClick={handleScrapeAmazon}
              disabled={scraping}
              className="inline-flex items-center px-6 py-3 bg-white text-primary-700 rounded-lg font-medium hover:bg-primary-50 transition-all hover:scale-105 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {scraping ? (
                <>
                  <LoadingSpinner size="sm" color="primary" />
                  <span className="ml-2">Scraping Amazon...</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  Scrape Amazon
                </>
              )}
            </button>

            <button
              className="inline-flex items-center px-6 py-3 bg-white/10 text-white rounded-lg font-medium hover:bg-white/20 transition-all backdrop-blur-sm"
              onClick={loadProductData}
            >
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh Data
            </button>
          </div>
        </div>

        {/* Price Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-white rounded-lg shadow-lg p-6 border-l-4 border-blue-500">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-gray-600">Competitors</p>
              <svg className="w-6 h-6 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <p className="text-3xl font-bold text-gray-900">{matches.length}</p>
            <p className="text-xs text-gray-500 mt-1">Total matches found</p>
          </div>

          <div className="bg-white rounded-lg shadow-lg p-6 border-l-4 border-green-500">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-gray-600">Lowest Price</p>
              <svg className="w-6 h-6 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              {latestPrice ? `$${latestPrice.toFixed(2)}` : 'N/A'}
            </p>
            <p className="text-xs text-gray-500 mt-1">Best deal available</p>
          </div>

          <div className="bg-white rounded-lg shadow-lg p-6 border-l-4 border-purple-500">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-gray-600">Average Price</p>
              <svg className="w-6 h-6 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              {avgPrice ? `$${avgPrice.toFixed(2)}` : 'N/A'}
            </p>
            <p className="text-xs text-gray-500 mt-1">Market average</p>
          </div>

          <div className="bg-white rounded-lg shadow-lg p-6 border-l-4 border-orange-500">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-gray-600">Price Range</p>
              <svg className="w-6 h-6 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              {matches.length > 0
                ? `$${(Math.max(...matches.map(m => m.latest_price)) - Math.min(...matches.map(m => m.latest_price))).toFixed(2)}`
                : 'N/A'
              }
            </p>
            <p className="text-xs text-gray-500 mt-1">High - Low spread</p>
          </div>
        </div>

        {/* Price History Chart */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
            <svg className="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
            </svg>
            Price History
          </h2>
          <PriceHistoryChart data={priceHistory} />
        </div>

        {/* Competitor Matches */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
            <svg className="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            Competitor Matches ({matches.length})
          </h2>

          {matches.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg">
              <svg className="mx-auto h-16 w-16 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <h3 className="mt-4 text-lg font-medium text-gray-900">No matches yet</h3>
              <p className="mt-2 text-gray-500">Click "Scrape Amazon" to find competitor products</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {matches.map((match) => (
                <div
                  key={match.id}
                  className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg p-6 border border-gray-200 hover:shadow-xl transition-all hover:scale-105"
                >
                  {match.image_url && (
                    <img
                      src={match.image_url}
                      alt={match.competitor_product_title}
                      className="w-full h-48 object-cover rounded-lg mb-4"
                      onError={(e) => e.target.style.display = 'none'}
                    />
                  )}

                  <div className="mb-4">
                    <p className="text-xs font-medium text-gray-500 mb-1">{match.competitor_name}</p>
                    <h3 className="font-semibold text-gray-900 line-clamp-2 mb-2">
                      {match.competitor_product_title}
                    </h3>
                  </div>

                  <div className="space-y-3 mb-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Price</span>
                      <span className="text-2xl font-bold text-primary-600">
                        ${match.latest_price.toFixed(2)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Stock</span>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        match.stock_status === 'In Stock'
                          ? 'bg-green-100 text-green-800'
                          : match.stock_status === 'Out of Stock'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {match.stock_status || 'Unknown'}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Match Score</span>
                      <span className="text-sm font-semibold text-gray-900">
                        {match.match_score ? `${(match.match_score * 100).toFixed(0)}%` : 'N/A'}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-4 border-t border-gray-200">
                    <a
                      href={match.competitor_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 inline-flex items-center justify-center px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
                    >
                      View Product
                      <svg className="w-4 h-4 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  </div>

                  <p className="text-xs text-gray-500 mt-3 text-center">
                    Last checked: {new Date(match.last_checked).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
