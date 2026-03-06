import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import PriceChart from '../../components/PriceChart';
import api from '../../lib/api';

export default function ProductDetailPage() {
  const router = useRouter();
  const { id } = router.query;

  const [product, setProduct] = useState(null);
  const [matches, setMatches] = useState([]);
  const [priceHistory, setPriceHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);

  useEffect(() => {
    if (id) {
      loadProduct();
    }
  }, [id]);

  const loadProduct = async () => {
    try {
      setLoading(true);
      const [productData, matchesData, historyData] = await Promise.all([
        api.getProduct(id),
        api.getProductMatches(id),
        api.getPriceHistory(id),
      ]);

      setProduct(productData);
      setMatches(matchesData);
      setPriceHistory(historyData);
    } catch (error) {
      console.error('Failed to load product:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleScrape = async () => {
    setScraping(true);
    try {
      await api.scrapeProduct(id, 'amazon.com', 5);
      alert('Scrape complete! Reloading data...');
      await loadProduct();
    } catch (error) {
      alert('Scrape failed: ' + error.message);
    } finally {
      setScraping(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading product...</p>
        </div>
      </Layout>
    );
  }

  if (!product) {
    return (
      <Layout>
        <div className="text-center py-12">
          <p className="text-gray-600">Product not found</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="px-4 sm:px-6 lg:px-8">
        {/* Product Header */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {product.title}
              </h1>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                {product.brand && (
                  <span>Brand: <span className="font-medium">{product.brand}</span></span>
                )}
                {product.sku && (
                  <span>SKU: <span className="font-medium">{product.sku}</span></span>
                )}
                <span>Added: {new Date(product.created_at).toLocaleDateString()}</span>
              </div>
            </div>
            <button
              onClick={handleScrape}
              disabled={scraping}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50"
            >
              {scraping ? 'Scraping...' : 'Scrape Amazon'}
            </button>
          </div>
        </div>

        {/* Competitor Matches */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Competitor Matches ({matches.length})
          </h2>

          {matches.length === 0 ? (
            <div className="text-center py-8 bg-gray-50 rounded-lg">
              <p className="text-gray-600 mb-4">No competitor matches yet</p>
              <button
                onClick={handleScrape}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
              >
                Search Amazon
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {matches.map((match) => (
                <div key={match.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-lg transition-shadow">
                  <div className="flex items-start justify-between mb-2">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {match.competitor_name}
                    </span>
                    <span className="text-sm text-gray-500">
                      {match.match_score}% match
                    </span>
                  </div>

                  {match.competitor_image_url && (
                    <img
                      src={match.competitor_image_url}
                      alt={match.competitor_title}
                      className="w-full h-32 object-contain mb-3"
                    />
                  )}

                  <h3 className="font-medium text-gray-900 text-sm mb-2 line-clamp-2">
                    {match.competitor_title}
                  </h3>

                  <div className="flex items-center justify-between">
                    <div>
                      {match.latest_price ? (
                        <p className="text-2xl font-bold text-gray-900">
                          ${match.latest_price}
                        </p>
                      ) : (
                        <p className="text-sm text-gray-500">No price data</p>
                      )}
                      <p className={`text-xs ${match.in_stock ? 'text-green-600' : 'text-red-600'}`}>
                        {match.in_stock ? 'In Stock' : 'Out of Stock'}
                      </p>
                    </div>
                    <a
                      href={match.competitor_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:text-primary-900 text-sm font-medium"
                    >
                      View →
                    </a>
                  </div>

                  <p className="text-xs text-gray-500 mt-2">
                    Last checked: {new Date(match.last_crawled_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Price History Chart */}
        {priceHistory.length > 0 && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              Price History
            </h2>
            <PriceChart data={priceHistory} />
          </div>
        )}
      </div>
    </Layout>
  );
}
