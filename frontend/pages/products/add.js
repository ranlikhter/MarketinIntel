import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import api from '../../lib/api';

export default function AddProductPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({ title: '', brand: '', sku: '', image_url: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => setFormData(f => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const product = await api.createProduct(formData);
      router.push(`/products/${product.id}`);
    } catch (err) {
      setError(err.message || 'Failed to create product');
      setLoading(false);
    }
  };

  const inputCls = 'w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-shadow';

  return (
    <Layout>
      <div className="p-4 lg:p-6 max-w-2xl mx-auto">

        {/* Back link */}
        <Link href="/products" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-5 transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back to Products
        </Link>

        {/* Main card */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm">
          <div className="px-5 py-4 border-b border-gray-50">
            <h1 className="text-lg font-bold text-gray-900">Add New Product</h1>
            <p className="text-sm text-gray-500 mt-0.5">Add a product to start tracking competitor prices</p>
          </div>

          <div className="p-5">
            {error && (
              <div className="mb-5 bg-red-50 border border-red-100 rounded-xl p-3.5 flex items-start gap-3">
                <svg className="w-4 h-4 text-red-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Product Title <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  name="title"
                  required
                  autoFocus
                  value={formData.title}
                  onChange={handleChange}
                  placeholder="e.g. Sony WH-1000XM5 Wireless Headphones"
                  className={inputCls}
                />
                <p className="text-xs text-gray-400 mt-1">The product name used to search for competitor listings</p>
              </div>

              {/* Brand + SKU */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Brand</label>
                  <input
                    type="text"
                    name="brand"
                    value={formData.brand}
                    onChange={handleChange}
                    placeholder="e.g. Sony"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">SKU / Code</label>
                  <input
                    type="text"
                    name="sku"
                    value={formData.sku}
                    onChange={handleChange}
                    placeholder="e.g. WH1000XM5-B"
                    className={inputCls}
                  />
                </div>
              </div>

              {/* Image URL */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Image URL</label>
                <input
                  type="url"
                  name="image_url"
                  value={formData.image_url}
                  onChange={handleChange}
                  placeholder="https://example.com/product-image.jpg"
                  className={inputCls}
                />
                <p className="text-xs text-gray-400 mt-1">Optional — used for the product card thumbnail</p>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between pt-2 border-t border-gray-50 mt-2">
                <Link
                  href="/products"
                  className="px-4 py-2.5 text-sm font-medium text-gray-500 hover:text-gray-700 transition-colors"
                >
                  Cancel
                </Link>
                <button
                  type="submit"
                  disabled={loading || !formData.title.trim()}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                >
                  {loading ? (
                    <>
                      <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Creating…
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                      </svg>
                      Create Product
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* What happens next */}
        <div className="mt-4 bg-blue-50 border border-blue-100 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-blue-900 mb-3">What happens next?</h3>
          <ul className="space-y-2.5">
            {[
              'Product is added to your monitoring catalogue',
              'Search Amazon or any competitor website for matching listings',
              'Price changes are tracked automatically on a schedule',
              'Set up alerts for price drops, out-of-stock events, and more',
            ].map((step, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-blue-800">
                <div className="w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-[10px] font-bold text-blue-600">{i + 1}</span>
                </div>
                {step}
              </li>
            ))}
          </ul>
        </div>

        {/* Import alternative */}
        <p className="text-center text-xs text-gray-400 mt-4">
          Have many products?{' '}
          <Link href="/integrations" className="text-blue-600 hover:underline font-medium">
            Import from XML, WooCommerce, or Shopify →
          </Link>
        </p>

      </div>
    </Layout>
  );
}
