import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { PriceHistoryChart, CompetitorComparisonChart } from '../../components/Charts';
import { useToast } from '../../components/Toast';
import { LoadingSpinner, SkeletonStats, SkeletonChart } from '../../components/LoadingStates';
import Modal from '../../components/Modal';
import api from '../../lib/api';

export default function ComparisonDashboard() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [matches, setMatches] = useState([]);
  const [priceHistory, setPriceHistory] = useState([]);
  const [stats, setStats] = useState({});
  const [showCrawler, setShowCrawler] = useState(false);
  const [crawlerUrl, setCrawlerUrl] = useState('');
  const [crawling, setCrawling] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const productsData = await api.getProducts();
      setProducts(productsData);

      // Calculate stats
      const totalProducts = productsData.length;
      const productsWithMatches = productsData.filter(p => p.competitor_count > 0).length;
      const totalMatches = productsData.reduce((sum, p) => sum + (p.competitor_count || 0), 0);

      // Get all matches to calculate price stats
      const allMatches = [];
      for (const product of productsData.slice(0, 10)) { // Sample first 10
        try {
          const productMatches = await api.getProductMatches(product.id);
          allMatches.push(...productMatches);
        } catch (e) {}
      }

      const avgPrice = allMatches.length > 0
        ? allMatches.reduce((sum, m) => sum + (m.latest_price || 0), 0) / allMatches.length
        : 0;

      const lowestPrice = allMatches.length > 0
        ? Math.min(...allMatches.map(m => m.latest_price || Infinity))
        : 0;

      setStats({
        totalProducts,
        productsWithMatches,
        totalMatches,
        avgPrice: avgPrice.toFixed(2),
        lowestPrice: lowestPrice !== Infinity ? lowestPrice.toFixed(2) : '0.00',
        coverageRate: totalProducts > 0 ? ((productsWithMatches / totalProducts) * 100).toFixed(1) : '0'
      });

    } catch (error) {
      addToast('Failed to load dashboard data', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleProductSelect = async (product) => {
    setSelectedProduct(product);

    try {
      const [matchesData, historyData] = await Promise.all([
        api.getProductMatches(product.id),
        api.getProductPriceHistory(product.id)
      ]);

      setMatches(matchesData);
      setPriceHistory(historyData);
    } catch (error) {
      addToast('Failed to load product data', 'error');
    }
  };

  const handleStartCrawl = async () => {
    if (!crawlerUrl) {
      addToast('Please enter a competitor URL', 'warning');
      return;
    }

    setCrawling(true);
    addToast('Starting site crawl...', 'info');

    try {
      const result = await api.startSiteCrawl(
        crawlerUrl,
        50,  // max products
        3,   // max depth
        true, // auto import
        new URL(crawlerUrl).hostname // competitor name
      );

      addToast(`Crawl complete! Found ${result.products_found} products, imported ${result.products_imported}`, 'success');
      setShowCrawler(false);
      setCrawlerUrl('');
      loadDashboardData();
    } catch (error) {
      addToast('Crawl failed: ' + error.message, 'error');
    } finally {
      setCrawling(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="space-y-6">
          <SkeletonStats />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SkeletonChart />
            <SkeletonChart />
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Comparison Dashboard</h1>
            <p className="mt-2 text-gray-600">Compare your products against competitor pricing</p>
          </div>
          <button
            onClick={() => setShowCrawler(true)}
            className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-lg font-medium hover:shadow-lg transition-all hover:scale-105"
          >
            <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Auto-Crawl Competitor Site
          </button>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Total Products"
            value={stats.totalProducts}
            icon={
              <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
            }
            color="blue"
          />
          <StatCard
            title="Competitor Matches"
            value={stats.totalMatches}
            icon={
              <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
            color="green"
          />
          <StatCard
            title="Avg Price"
            value={`$${stats.avgPrice}`}
            icon={
              <svg className="w-8 h-8 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
            color="purple"
          />
          <StatCard
            title="Coverage Rate"
            value={`${stats.coverageRate}%`}
            icon={
              <svg className="w-8 h-8 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            }
            color="orange"
          />
        </div>

        {/* Product Selection & Comparison */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Product List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <svg className="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
                Your Products
              </h2>

              {products.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>No products yet</p>
                  <Link href="/products/add" className="text-primary-600 hover:text-primary-700 mt-2 inline-block">
                    Add your first product
                  </Link>
                </div>
              ) : (
                <div className="space-y-2 max-h-[600px] overflow-y-auto">
                  {products.map(product => (
                    <button
                      key={product.id}
                      onClick={() => handleProductSelect(product)}
                      className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
                        selectedProduct?.id === product.id
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <div className="font-medium text-gray-900 truncate">{product.title}</div>
                      <div className="text-sm text-gray-500 mt-1">
                        {product.competitor_count || 0} matches
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Comparison View */}
          <div className="lg:col-span-2">
            {!selectedProduct ? (
              <div className="bg-white rounded-lg shadow-lg p-12 text-center">
                <svg className="w-24 h-24 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">No Product Selected</h3>
                <p className="text-gray-600">Select a product from the list to view comparison data</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Selected Product Header */}
                <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-lg shadow-lg p-6 text-white">
                  <h2 className="text-2xl font-bold mb-2">{selectedProduct.title}</h2>
                  <div className="flex items-center gap-4 text-primary-100">
                    {selectedProduct.brand && <span>Brand: {selectedProduct.brand}</span>}
                    {selectedProduct.sku && <span>SKU: {selectedProduct.sku}</span>}
                    <span className="inline-flex items-center gap-1">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {matches.length} Competitors
                    </span>
                  </div>
                </div>

                {/* Price Comparison Chart */}
                {matches.length > 0 && (
                  <div className="bg-white rounded-lg shadow-lg p-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-4">Price Comparison</h3>
                    <CompetitorComparisonChart
                      data={matches.map(m => ({
                        competitor_name: m.competitor_name,
                        latest_price: m.latest_price
                      }))}
                    />
                  </div>
                )}

                {/* Price History */}
                {priceHistory.length > 0 && (
                  <div className="bg-white rounded-lg shadow-lg p-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-4">Price History</h3>
                    <PriceHistoryChart data={priceHistory} />
                  </div>
                )}

                {/* Competitor Matches Table */}
                <div className="bg-white rounded-lg shadow-lg overflow-hidden">
                  <div className="p-6 border-b border-gray-200">
                    <h3 className="text-lg font-bold text-gray-900">Competitor Matches</h3>
                  </div>
                  {matches.length === 0 ? (
                    <div className="p-12 text-center text-gray-500">
                      <p>No competitor matches found</p>
                      <Link
                        href={`/products/${selectedProduct.id}`}
                        className="text-primary-600 hover:text-primary-700 mt-2 inline-block"
                      >
                        Scrape competitors
                      </Link>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Competitor</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stock</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Score</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Checked</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {matches.map(match => (
                            <tr key={match.id} className="hover:bg-gray-50">
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div className="font-medium text-gray-900">{match.competitor_name}</div>
                                <div className="text-sm text-gray-500 truncate max-w-xs">
                                  {match.competitor_product_title}
                                </div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-lg font-bold text-primary-600">
                                  ${match.latest_price?.toFixed(2) || 'N/A'}
                                </div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                  match.stock_status === 'In Stock'
                                    ? 'bg-green-100 text-green-800'
                                    : 'bg-red-100 text-red-800'
                                }`}>
                                  {match.stock_status || 'Unknown'}
                                </span>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {match.match_score ? `${(match.match_score * 100).toFixed(0)}%` : 'N/A'}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {new Date(match.last_checked).toLocaleString()}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm">
                                <a
                                  href={match.competitor_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-primary-600 hover:text-primary-900 font-medium"
                                >
                                  View
                                </a>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Site Crawler Modal */}
      <Modal
        isOpen={showCrawler}
        onClose={() => setShowCrawler(false)}
        title="Auto-Crawl Competitor Site"
        size="md"
      >
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Competitor Website URL
            </label>
            <input
              type="url"
              value={crawlerUrl}
              onChange={(e) => setCrawlerUrl(e.target.value)}
              placeholder="https://competitor-store.com"
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            />
            <p className="mt-2 text-sm text-gray-500">
              The crawler will automatically discover and import all products from this website
            </p>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-900 mb-2">What happens:</h4>
            <ul className="text-xs text-blue-800 space-y-1 list-disc list-inside">
              <li>Discovers all category pages</li>
              <li>Finds all product pages</li>
              <li>Extracts product data (title, price, images)</li>
              <li>Automatically imports products</li>
              <li>Creates competitor matches</li>
            </ul>
          </div>

          <button
            onClick={handleStartCrawl}
            disabled={crawling || !crawlerUrl}
            className="w-full inline-flex items-center justify-center px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {crawling ? (
              <>
                <LoadingSpinner size="sm" color="white" />
                <span className="ml-2">Crawling...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Start Auto-Crawl
              </>
            )}
          </button>
        </div>
      </Modal>
    </Layout>
  );
}

function StatCard({ title, value, icon, color }) {
  const colorClasses = {
    blue: 'border-blue-500',
    green: 'border-green-500',
    purple: 'border-purple-500',
    orange: 'border-orange-500'
  };

  return (
    <div className={`bg-white rounded-lg shadow-lg p-6 border-l-4 ${colorClasses[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <div>{icon}</div>
      </div>
      <div className="text-3xl font-bold text-gray-900 mb-1">{value}</div>
      <div className="text-sm text-gray-600">{title}</div>
    </div>
  );
}
