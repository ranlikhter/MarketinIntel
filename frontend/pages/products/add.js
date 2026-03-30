import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import api from '../../lib/api';

const NUMERIC_FIELDS = [
  'my_price', 'cost_price', 'map_price', 'rrp_msrp', 'compare_at_price',
  'min_price', 'max_price', 'target_margin_pct',
  'weight', 'length', 'width', 'height', 'match_threshold',
];

const BOOL_FIELDS = ['is_bundle', 'track_all_variants'];

function Section({ title, badge, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left transition-colors hover:bg-white/5"
        style={{ background: 'var(--bg-surface-2, rgba(255,255,255,0.04))' }}
      >
        <span className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white/80">{title}</span>
          {badge && (
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md text-amber-400 bg-amber-500/10">
              {badge}
            </span>
          )}
        </span>
        <svg
          className="w-4 h-4 transition-transform"
          style={{ color: 'var(--text-muted)', transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-3 space-y-4">
          {children}
        </div>
      )}
    </div>
  );
}

function Field({ label, hint, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-white/70 mb-1.5">{label}</label>
      {children}
      {hint && <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{hint}</p>}
    </div>
  );
}

export default function AddProductPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    // Basics
    title: '', brand: '', sku: '', image_url: '', product_url: '', category: '',
    // Pricing
    my_price: '', cost_price: '', map_price: '', rrp_msrp: '', compare_at_price: '',
    min_price: '', max_price: '', target_margin_pct: '', currency: 'USD',
    // Identifiers
    mpn: '', upc_ean: '', asin: '', model_number: '', keywords: '',
    // Dimensions
    weight: '', weight_unit: 'kg', length: '', width: '', height: '', dimension_unit: 'cm',
    // Catalog
    status: 'active', tags: '', notes: '', is_bundle: false, bundle_skus: '',
    // Variants
    parent_sku: '', variant_attributes: '',
    // Scraping
    scrape_frequency: 'daily', scrape_priority: 'medium',
    track_all_variants: false, match_threshold: '60',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = { ...formData };

      // Coerce numerics
      for (const f of NUMERIC_FIELDS) {
        if (payload[f] !== '' && payload[f] !== null && payload[f] !== undefined) {
          const n = parseFloat(payload[f]);
          payload[f] = isNaN(n) ? null : n;
        } else {
          delete payload[f];
        }
      }

      // Booleans are already correct type
      for (const f of BOOL_FIELDS) {
        payload[f] = Boolean(payload[f]);
      }

      // Tags: comma-separated string → array
      if (payload.tags && typeof payload.tags === 'string') {
        payload.tags = payload.tags.split(',').map(t => t.trim()).filter(Boolean);
      } else {
        delete payload.tags;
      }

      // bundle_skus: comma-separated → array
      if (payload.bundle_skus && typeof payload.bundle_skus === 'string') {
        payload.bundle_skus = payload.bundle_skus.split(',').map(s => s.trim()).filter(Boolean);
      } else {
        delete payload.bundle_skus;
      }

      // variant_attributes: JSON string → object
      if (payload.variant_attributes && typeof payload.variant_attributes === 'string') {
        try {
          payload.variant_attributes = JSON.parse(payload.variant_attributes);
        } catch {
          payload.variant_attributes = null;
        }
      } else {
        delete payload.variant_attributes;
      }

      // Remove empty strings
      Object.keys(payload).forEach(k => {
        if (payload[k] === '') delete payload[k];
      });

      const product = await api.createProduct(payload);
      router.push(`/products/${product.id}`);
    } catch (err) {
      setError(err.message || 'Failed to create product');
      setLoading(false);
    }
  };

  const inp = 'glass-input w-full px-3.5 py-2.5 rounded-xl text-sm text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/50 transition-shadow';
  const sel = `${inp} appearance-none cursor-pointer`;
  const priceInp = `${inp} pl-7`;

  const PriceInput = ({ name, placeholder }) => (
    <div className="relative">
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm" style={{ color: 'var(--text-muted)' }}>
        {formData.currency === 'GBP' ? '£' : formData.currency === 'EUR' ? '€' : '$'}
      </span>
      <input type="number" name={name} value={formData[name]} onChange={handleChange}
        placeholder={placeholder || '0.00'} step="0.01" min="0" className={priceInp} />
    </div>
  );

  return (
    <Layout>
      <div className="p-4 lg:p-6 max-w-2xl mx-auto">

        <Link href="/products" className="inline-flex items-center gap-1.5 text-sm hover:text-white/70 mb-5 transition-colors" style={{ color: 'var(--text-muted)' }}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back to Products
        </Link>

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

            <form onSubmit={handleSubmit} className="space-y-3">

              {/* ── Basics ── */}
              <Section title="Basics" badge="Required" defaultOpen>
                <Field label={<>Product Title <span className="text-red-400">*</span></>}
                  hint="The product name used to search for competitor listings">
                  <input type="text" name="title" required autoFocus value={formData.title}
                    onChange={handleChange} placeholder="e.g. Sony WH-1000XM5 Wireless Headphones" className={inp} />
                </Field>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Brand">
                    <input type="text" name="brand" value={formData.brand} onChange={handleChange}
                      placeholder="e.g. Sony" className={inp} />
                  </Field>
                  <Field label="SKU / Code">
                    <input type="text" name="sku" value={formData.sku} onChange={handleChange}
                      placeholder="e.g. WH1000XM5-B" className={inp} />
                  </Field>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Category">
                    <input type="text" name="category" value={formData.category} onChange={handleChange}
                      placeholder="e.g. Electronics" className={inp} />
                  </Field>
                  <Field label="Status">
                    <select name="status" value={formData.status} onChange={handleChange} className={sel}>
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                      <option value="discontinued">Discontinued</option>
                      <option value="draft">Draft</option>
                    </select>
                  </Field>
                </div>

                <Field label="Image URL" hint="Optional — used for the product card thumbnail">
                  <input type="url" name="image_url" value={formData.image_url} onChange={handleChange}
                    placeholder="https://example.com/image.jpg" className={inp} />
                </Field>

                <Field label="Product URL" hint="Link to your own store listing">
                  <input type="url" name="product_url" value={formData.product_url} onChange={handleChange}
                    placeholder="https://mystore.com/products/..." className={inp} />
                </Field>
              </Section>

              {/* ── Pricing & Margin ── */}
              <Section title="Pricing & Margin" defaultOpen>
                <div className="grid grid-cols-3 gap-3 items-end">
                  <div className="col-span-2">
                    <Field label="Currency">
                      <select name="currency" value={formData.currency} onChange={handleChange} className={sel}>
                        <option value="USD">USD — US Dollar</option>
                        <option value="EUR">EUR — Euro</option>
                        <option value="GBP">GBP — British Pound</option>
                        <option value="AUD">AUD — Australian Dollar</option>
                        <option value="CAD">CAD — Canadian Dollar</option>
                      </select>
                    </Field>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="My Selling Price">
                    <PriceInput name="my_price" />
                  </Field>
                  <Field label="Cost / COGS" hint="Landed cost — used to calculate margin">
                    <PriceInput name="cost_price" />
                  </Field>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="MAP Price" hint="Minimum Advertised Price">
                    <PriceInput name="map_price" />
                  </Field>
                  <Field label="RRP / MSRP" hint="Recommended retail price">
                    <PriceInput name="rrp_msrp" />
                  </Field>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Compare-at Price" hint="Original / crossed-out price">
                    <PriceInput name="compare_at_price" />
                  </Field>
                  <Field label="Target Margin %">
                    <div className="relative">
                      <input type="number" name="target_margin_pct" value={formData.target_margin_pct}
                        onChange={handleChange} placeholder="e.g. 30" step="0.1" min="0" max="100" className={`${inp} pr-7`} />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm" style={{ color: 'var(--text-muted)' }}>%</span>
                    </div>
                  </Field>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Min Price Floor" hint="Never reprice below this">
                    <PriceInput name="min_price" />
                  </Field>
                  <Field label="Max Price Ceiling" hint="Never reprice above this">
                    <PriceInput name="max_price" />
                  </Field>
                </div>
              </Section>

              {/* ── Product Identifiers ── */}
              <Section title="Product Identifiers" badge="Improves match accuracy">
                <div className="grid grid-cols-2 gap-4">
                  <Field label="MPN" hint="Manufacturer Part Number">
                    <input type="text" name="mpn" value={formData.mpn} onChange={handleChange}
                      placeholder="e.g. WH1000XM5/B" className={inp} />
                  </Field>
                  <Field label="UPC / EAN" hint="Barcode — exact match guarantee">
                    <input type="text" name="upc_ean" value={formData.upc_ean} onChange={handleChange}
                      placeholder="e.g. 027242920958" className={inp} />
                  </Field>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="ASIN" hint="Amazon Standard Identification Number">
                    <input type="text" name="asin" value={formData.asin} onChange={handleChange}
                      placeholder="e.g. B09XS7JWHH" className={inp} />
                  </Field>
                  <Field label="Model Number">
                    <input type="text" name="model_number" value={formData.model_number} onChange={handleChange}
                      placeholder="e.g. WH-1000XM5" className={inp} />
                  </Field>
                </div>

                <Field label="Search Keywords" hint="Extra terms used when searching for competitor matches">
                  <input type="text" name="keywords" value={formData.keywords} onChange={handleChange}
                    placeholder="e.g. noise cancelling headphones, WH1000" className={inp} />
                </Field>
              </Section>

              {/* ── Dimensions & Weight ── */}
              <Section title="Dimensions & Weight">
                <div className="grid grid-cols-3 gap-3">
                  <Field label="Weight">
                    <input type="number" name="weight" value={formData.weight} onChange={handleChange}
                      placeholder="0.00" step="0.01" min="0" className={inp} />
                  </Field>
                  <div className="col-span-2">
                    <Field label="Weight Unit">
                      <select name="weight_unit" value={formData.weight_unit} onChange={handleChange} className={sel}>
                        <option value="kg">kg</option>
                        <option value="g">g</option>
                        <option value="lb">lb</option>
                        <option value="oz">oz</option>
                      </select>
                    </Field>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-3">
                  <Field label="Length">
                    <input type="number" name="length" value={formData.length} onChange={handleChange}
                      placeholder="0" step="0.1" min="0" className={inp} />
                  </Field>
                  <Field label="Width">
                    <input type="number" name="width" value={formData.width} onChange={handleChange}
                      placeholder="0" step="0.1" min="0" className={inp} />
                  </Field>
                  <Field label="Height">
                    <input type="number" name="height" value={formData.height} onChange={handleChange}
                      placeholder="0" step="0.1" min="0" className={inp} />
                  </Field>
                  <Field label="Unit">
                    <select name="dimension_unit" value={formData.dimension_unit} onChange={handleChange} className={sel}>
                      <option value="cm">cm</option>
                      <option value="mm">mm</option>
                      <option value="in">in</option>
                    </select>
                  </Field>
                </div>
              </Section>

              {/* ── Catalog & Notes ── */}
              <Section title="Catalog & Notes">
                <Field label="Tags" hint="Comma-separated — e.g. wireless, audio, premium">
                  <input type="text" name="tags" value={formData.tags} onChange={handleChange}
                    placeholder="e.g. wireless, audio, noise-cancelling" className={inp} />
                </Field>

                <Field label="Internal Notes">
                  <textarea name="notes" value={formData.notes} onChange={handleChange}
                    placeholder="Any internal notes about this product..." rows={3}
                    className={`${inp} resize-none`} />
                </Field>

                <div className="flex items-center gap-3">
                  <input type="checkbox" id="is_bundle" name="is_bundle" checked={formData.is_bundle}
                    onChange={handleChange} className="w-4 h-4 rounded accent-amber-500 cursor-pointer" />
                  <label htmlFor="is_bundle" className="text-sm text-white/70 cursor-pointer">This product is a bundle</label>
                </div>

                {formData.is_bundle && (
                  <Field label="Bundle Component SKUs" hint="Comma-separated SKUs of the items in this bundle">
                    <input type="text" name="bundle_skus" value={formData.bundle_skus} onChange={handleChange}
                      placeholder="e.g. SKU-001, SKU-002, SKU-003" className={inp} />
                  </Field>
                )}
              </Section>

              {/* ── Variants ── */}
              <Section title="Variants">
                <Field label="Parent SKU" hint="If this is a variant, enter the parent product SKU">
                  <input type="text" name="parent_sku" value={formData.parent_sku} onChange={handleChange}
                    placeholder="e.g. WH1000XM5" className={inp} />
                </Field>

                <Field label="Variant Attributes" hint='JSON — e.g. {"color":"Black","size":"One Size"}'>
                  <textarea name="variant_attributes" value={formData.variant_attributes} onChange={handleChange}
                    placeholder='{"color": "Black", "size": "One Size"}' rows={3}
                    className={`${inp} resize-none font-mono text-xs`} />
                </Field>
              </Section>

              {/* ── Scraping Control ── */}
              <Section title="Scraping Control">
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Scrape Frequency">
                    <select name="scrape_frequency" value={formData.scrape_frequency} onChange={handleChange} className={sel}>
                      <option value="realtime">Real-time</option>
                      <option value="hourly">Hourly</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="manual">Manual only</option>
                    </select>
                  </Field>
                  <Field label="Priority">
                    <select name="scrape_priority" value={formData.scrape_priority} onChange={handleChange} className={sel}>
                      <option value="critical">Critical</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                  </Field>
                </div>

                <Field label="Match Threshold %" hint="Minimum similarity score (0–100) for a competitor match to be accepted">
                  <div className="relative">
                    <input type="number" name="match_threshold" value={formData.match_threshold}
                      onChange={handleChange} placeholder="60" step="1" min="0" max="100" className={`${inp} pr-7`} />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm" style={{ color: 'var(--text-muted)' }}>%</span>
                  </div>
                </Field>

                <div className="flex items-center gap-3">
                  <input type="checkbox" id="track_all_variants" name="track_all_variants"
                    checked={formData.track_all_variants} onChange={handleChange}
                    className="w-4 h-4 rounded accent-amber-500 cursor-pointer" />
                  <label htmlFor="track_all_variants" className="text-sm text-white/70 cursor-pointer">
                    Track all variants (not just exact SKU match)
                  </label>
                </div>
              </Section>

              {/* ── Actions ── */}
              <div className="flex items-center justify-between pt-2 mt-2" style={{ borderTop: '1px solid var(--border)' }}>
                <Link href="/products" className="px-4 py-2.5 text-sm font-medium hover:text-white/70 transition-colors"
                  style={{ color: 'var(--text-muted)' }}>
                  Cancel
                </Link>
                <button type="submit" disabled={loading || !formData.title.trim()}
                  className="inline-flex items-center gap-2 px-5 py-2.5 gradient-brand text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm">
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
