import { useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import api from '../../lib/api';

export default function AddCompetitorPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    name: '',
    base_url: '',
    website_type: 'custom',
    price_selector: '',
    title_selector: '',
    stock_selector: '',
    image_selector: '',
    notes: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      // Validate required fields
      if (!formData.name || !formData.base_url) {
        setError('Name and Base URL are required');
        setSubmitting(false);
        return;
      }

      // Create competitor
      const newCompetitor = await api.createCompetitor(formData);

      // Redirect to competitors list
      router.push('/competitors');
    } catch (err) {
      setError(err.message || 'Failed to create competitor');
      setSubmitting(false);
    }
  };

  return (
    <Layout>
      <div className="px-4 sm:px-6 lg:px-8 max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Add Competitor Website</h1>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
            Configure a custom competitor website with CSS selectors for scraping
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 rounded-lg p-4" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="rounded-lg shadow" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="p-6 space-y-6">
            {/* Basic Information */}
            <div className="pb-6" style={{ borderBottom: '1px solid var(--border)' }}>
              <h2 className="text-lg font-semibold text-white mb-4">Basic Information</h2>

              <div className="space-y-4">
                {/* Name */}
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-white/70">
                    Competitor Name <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    name="name"
                    id="name"
                    required
                    value={formData.name}
                    onChange={handleChange}
                    placeholder="e.g., CompetitorStore, Amazon"
                    className="glass-input mt-1 block w-full rounded-md sm:text-sm"
                  />
                  <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                    A friendly name to identify this competitor
                  </p>
                </div>

                {/* Base URL */}
                <div>
                  <label htmlFor="base_url" className="block text-sm font-medium text-white/70">
                    Base URL <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="url"
                    name="base_url"
                    id="base_url"
                    required
                    value={formData.base_url}
                    onChange={handleChange}
                    placeholder="https://www.competitor.com"
                    className="glass-input mt-1 block w-full rounded-md sm:text-sm"
                  />
                  <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                    The main website URL (must start with http:// or https://)
                  </p>
                </div>

                {/* Website Type */}
                <div>
                  <label htmlFor="website_type" className="block text-sm font-medium text-white/70">
                    Website Type
                  </label>
                  <select
                    name="website_type"
                    id="website_type"
                    value={formData.website_type}
                    onChange={handleChange}
                    className="glass-input mt-1 block w-full rounded-md sm:text-sm"
                  >
                    <option value="custom">Custom Website</option>
                    <option value="ecommerce">E-commerce Store</option>
                    <option value="marketplace">Marketplace</option>
                    <option value="retail">Retail Store</option>
                  </select>
                </div>
              </div>
            </div>

            {/* CSS Selectors */}
            <div className="pb-6" style={{ borderBottom: '1px solid var(--border)' }}>
              <h2 className="text-lg font-semibold text-white mb-2">CSS Selectors</h2>
              <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
                Configure CSS selectors to extract product data. Use browser DevTools to find the right selectors.
              </p>

              <div className="space-y-4">
                {/* Price Selector */}
                <div>
                  <label htmlFor="price_selector" className="block text-sm font-medium text-white/70">
                    Price Selector
                  </label>
                  <input
                    type="text"
                    name="price_selector"
                    id="price_selector"
                    value={formData.price_selector}
                    onChange={handleChange}
                    placeholder=".price, #product-price, .a-price-whole"
                    className="glass-input mt-1 block w-full rounded-md sm:text-sm font-mono text-xs"
                  />
                  <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                    Example: <code style={{ background: 'rgba(255,255,255,0.08)' }} className="px-1 rounded">.price</code> or <code style={{ background: 'rgba(255,255,255,0.08)' }} className="px-1 rounded">#product-price</code>
                  </p>
                </div>

                {/* Title Selector */}
                <div>
                  <label htmlFor="title_selector" className="block text-sm font-medium text-white/70">
                    Title Selector
                  </label>
                  <input
                    type="text"
                    name="title_selector"
                    id="title_selector"
                    value={formData.title_selector}
                    onChange={handleChange}
                    placeholder="h1.product-title, #productTitle"
                    className="glass-input mt-1 block w-full rounded-md sm:text-sm font-mono text-xs"
                  />
                  <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                    Example: <code style={{ background: 'rgba(255,255,255,0.08)' }} className="px-1 rounded">h1.product-title</code>
                  </p>
                </div>

                {/* Stock Selector */}
                <div>
                  <label htmlFor="stock_selector" className="block text-sm font-medium text-white/70">
                    Stock Status Selector
                  </label>
                  <input
                    type="text"
                    name="stock_selector"
                    id="stock_selector"
                    value={formData.stock_selector}
                    onChange={handleChange}
                    placeholder=".stock-status, #availability"
                    className="glass-input mt-1 block w-full rounded-md sm:text-sm font-mono text-xs"
                  />
                  <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                    Example: <code style={{ background: 'rgba(255,255,255,0.08)' }} className="px-1 rounded">.availability</code>
                  </p>
                </div>

                {/* Image Selector */}
                <div>
                  <label htmlFor="image_selector" className="block text-sm font-medium text-white/70">
                    Image Selector
                  </label>
                  <input
                    type="text"
                    name="image_selector"
                    id="image_selector"
                    value={formData.image_selector}
                    onChange={handleChange}
                    placeholder=".product-image, #landingImage"
                    className="glass-input mt-1 block w-full rounded-md sm:text-sm font-mono text-xs"
                  />
                  <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                    Example: <code style={{ background: 'rgba(255,255,255,0.08)' }} className="px-1 rounded">img.product-image</code>
                  </p>
                </div>
              </div>

              {/* Help Section */}
              <div className="mt-4 rounded-lg p-4" style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)' }}>
                <h3 className="text-sm font-medium text-amber-400 mb-2">How to Find CSS Selectors</h3>
                <ol className="text-xs space-y-1 list-decimal list-inside" style={{ color: 'rgba(245,158,11,0.8)' }}>
                  <li>Open the competitor's product page in Chrome</li>
                  <li>Right-click on the element (price, title, etc.) and select "Inspect"</li>
                  <li>In DevTools, right-click the highlighted HTML element</li>
                  <li>Select "Copy" → "Copy selector"</li>
                  <li>Paste the selector into the form above</li>
                </ol>
              </div>
            </div>

            {/* Notes */}
            <div>
              <label htmlFor="notes" className="block text-sm font-medium text-white/70">
                Notes (Optional)
              </label>
              <textarea
                name="notes"
                id="notes"
                rows={3}
                value={formData.notes}
                onChange={handleChange}
                placeholder="Any additional information about this competitor..."
                className="glass-input mt-1 block w-full rounded-md sm:text-sm"
              />
            </div>
          </div>

          {/* Form Actions */}
          <div className="px-6 py-4 flex items-center justify-between rounded-b-lg" style={{ background: 'var(--bg-elevated)', borderTop: '1px solid var(--border)' }}>
            <button
              type="button"
              onClick={() => router.push('/competitors')}
              className="text-sm font-medium hover:text-white transition-colors"
              style={{ color: 'var(--text-muted)' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md text-white gradient-brand hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            >
              {submitting ? 'Creating...' : 'Create Competitor'}
            </button>
          </div>
        </form>

        {/* Additional Help */}
        <div className="mt-6 rounded-lg p-4" style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)' }}>
          <h3 className="text-sm font-medium text-amber-400 mb-2">Testing Your Selectors</h3>
          <p className="text-xs mb-2" style={{ color: 'rgba(245,158,11,0.8)' }}>
            After creating the competitor, you can test if the selectors work correctly:
          </p>
          <ol className="text-xs space-y-1 list-decimal list-inside" style={{ color: 'rgba(245,158,11,0.8)' }}>
            <li>Go to a product detail page</li>
            <li>Click "Scrape URL" and paste a competitor product URL</li>
            <li>Select this competitor from the dropdown</li>
            <li>Check if the price, title, and other data are extracted correctly</li>
            <li>If not, edit the competitor and update the CSS selectors</li>
          </ol>
        </div>
      </div>
    </Layout>
  );
}
