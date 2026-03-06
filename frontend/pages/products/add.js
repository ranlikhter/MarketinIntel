import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import api from '../../lib/api';

export default function AddProductPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    title: '', brand: '', sku: '', image_url: '',
    my_price: '', cost_price: '', mpn: '', upc_ean: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => setFormData(f => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = { ...formData };
      // Convert numeric strings to numbers
      if (payload.my_price) payload.my_price = parseFloat(payload.my_price);
      if (payload.cost_price) payload.cost_price = parseFloat(payload.cost_price);
      // Remove empty strings
      Object.keys(payload).forEach((k) => { if (payload[k] === '') delete payload[k]; });
      const product = await api.createProduct(payload);
      router.push(`/products/${product.id}`);
    } catch (err) {
      setError(err.message || 'Failed to create product');
      setLoading(false);
    }
  };

  const inputCls = 'glass-input w-full px-3.5 py-2.5 rounded-xl text-sm text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/50 transition-shadow';

  return (
    <Layout>
      <div className="p-4 lg:p-6 max-w-2xl mx-auto">

        {/* Back link */}
        <Link href="/products" className="inline-flex items-center gap-1.5 text-sm hover:text-white/70 mb-5 transition-colors" style={{ color: 'var(--text-muted)' }}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back to Products
        </Link>

        {/* Main card */}
        <div className="rounded-2xl shadow-sm" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <h1 className="text-lg font-bold text-white">Add New Product</h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>Add a product to start tracking competitor prices</p>
          </div>

          <div className="p-5">
            {error && (
              <div className="mb-5 bg-red-500/10 border border-red-500/20 rounded-xl p-3.5 flex items-start gap-3">
                <svg className="w-4 h-4 text-red-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">
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
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>The product name used to search for competitor listings</p>
              </div>

              {/* Brand + SKU */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">Brand</label>
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
                  <label className="block text-sm font-medium text-white/70 mb-1.5">SKU / Code</label>
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
                <label className="block text-sm font-medium text-white/70 mb-1.5">Image URL</label>
                <input
                  type="url"
                  name="image_url"
                  value={formData.image_url}
                  onChange={handleChange}
                  placeholder="https://example.com/product-image.jpg"
                  className={inputCls}
                />
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Optional — used for the product card thumbnail</p>
              </div>

              {/* Pricing section */}
              <div className="pt-1">
                <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>Pricing & Margin</p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-1.5">My Selling Price</label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm" style={{ color: 'var(--text-muted)' }}>$</span>
                      <input
                        type="number"
                        name="my_price"
                        value={formData.my_price}
                        onChange={handleChange}
                        placeholder="0.00"
                        step="0.01"
                        min="0"
                        className={`${inputCls} pl-7`}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-1.5">
                      Cost / COGS{' '}
                      <span className="text-xs font-normal" style={{ color: 'var(--text-muted)' }}>(enables margin view)</span>
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm" style={{ color: 'var(--text-muted)' }}>$</span>
                      <input
                        type="number"
                        name="cost_price"
                        value={formData.cost_price}
                        onChange={handleChange}
                        placeholder="0.00"
                        step="0.01"
                        min="0"
                        className={`${inputCls} pl-7`}
                      />
                    </div>
                    <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Landed cost — used to calculate margin vs competitors</p>
                  </div>
                </div>
              </div>

              {/* Product identifiers */}
              <div className="pt-1">
                <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
                  Product Identifiers{' '}
                  <span className="text-xs text-amber-400 font-normal normal-case">(improves match accuracy)</span>
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-1.5">MPN</label>
                    <input
                      type="text"
                      name="mpn"
                      value={formData.mpn}
                      onChange={handleChange}
                      placeholder="e.g. WH1000XM5/B"
                      className={inputCls}
                    />
                    <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Manufacturer Part Number</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-1.5">UPC / EAN</label>
                    <input
                      type="text"
                      name="upc_ean"
                      value={formData.upc_ean}
                      onChange={handleChange}
                      placeholder="e.g. 027242920958"
                      className={inputCls}
                    />
                    <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Barcode — exact match guarantee</p>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between pt-2 mt-2" style={{ borderTop: '1px solid var(--border)' }}>
                <Link
                  href="/products"
                  className="px-4 py-2.5 text-sm font-medium hover:text-white/70 transition-colors"
                  style={{ color: 'var(--text-muted)' }}
                >
                  Cancel
                </Link>
                <button
                  type="submit"
                  disabled={loading || !formData.title.trim()}
                  className="inline-flex items-center gap-2 px-5 py-2.5 gradient-brand text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
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
        <div className="mt-4 rounded-2xl p-5" style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.18)' }}>
          <h3 className="text-sm font-semibold text-amber-400 mb-3">What happens next?</h3>
          <ul className="space-y-2.5">
            {[
              'Product is added to your monitoring catalogue',
              'Search Amazon or any competitor website for matching listings',
              'Price changes are tracked automatically on a schedule',
              'Set up alerts for price drops, out-of-stock events, and more',
            ].map((step, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-white/70">
                <div className="w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5" style={{ background: 'rgba(245,158,11,0.15)' }}>
                  <span className="text-[10px] font-bold text-amber-400">{i + 1}</span>
                </div>
                {step}
              </li>
            ))}
          </ul>
        </div>

        {/* Import alternative */}
        <p className="text-center text-xs mt-4" style={{ color: 'var(--text-muted)' }}>
          Have many products?{' '}
          <Link href="/integrations" className="text-amber-400 hover:text-amber-300 font-medium">
            Import from XML, WooCommerce, or Shopify →
          </Link>
        </p>

      </div>
    </Layout>
  );
}
