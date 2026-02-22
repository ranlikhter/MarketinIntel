import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { PriceHistoryChart } from '../../components/Charts';
import { useToast } from '../../components/Toast';
import api from '../../lib/api';

// ─── INLINE ICONS ─────────────────────────────────────────────────────────────
const Ico = {
  back:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>,
  search:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>,
  refresh: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  users:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>,
  dollar:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  avg:     <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  range:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>,
  external:<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>,
  image:   <svg className="w-10 h-10 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>,
};

function StatCard({ label, sub, value, color, icon }) {
  const bg = { blue: 'bg-blue-50 text-blue-600', emerald: 'bg-emerald-50 text-emerald-600', violet: 'bg-violet-50 text-violet-600', amber: 'bg-amber-50 text-amber-600' }[color];
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${bg}`}>{icon}</div>
      <div>
        <p className="text-2xl font-bold text-gray-900 leading-none">{value}</p>
        <p className="text-xs text-gray-500 mt-1">{label}</p>
        {sub && <p className="text-xs text-gray-400">{sub}</p>}
      </div>
    </div>
  );
}

function StockBadge({ status }) {
  if (status === 'In Stock')    return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">In Stock</span>;
  if (status === 'Out of Stock') return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">Out of Stock</span>;
  return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700">Low Stock</span>;
}

function MatchCard({ match }) {
  const [imgErr, setImgErr] = useState(false);
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden flex flex-col">
      {/* Image */}
      <div className="h-40 bg-gray-50 flex items-center justify-center overflow-hidden">
        {!imgErr && match.image_url ? (
          <img src={match.image_url} alt={match.competitor_product_title} className="w-full h-full object-contain p-2" onError={() => setImgErr(true)} />
        ) : (
          <div className="text-gray-200">{Ico.image}</div>
        )}
      </div>

      {/* Body */}
      <div className="p-4 flex-1 flex flex-col">
        <p className="text-xs text-gray-400 font-medium mb-1 uppercase tracking-wide">{match.competitor_name}</p>
        <p className="text-sm font-medium text-gray-900 line-clamp-2 flex-1 mb-3">{match.competitor_product_title}</p>

        <div className="space-y-2 mb-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Price</span>
            <span className="text-base font-bold text-blue-600">${match.latest_price?.toFixed(2) ?? '—'}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Stock</span>
            <StockBadge status={match.stock_status} />
          </div>
          {match.match_score != null && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Match</span>
              <span className="text-xs font-semibold text-gray-700">{(match.match_score * 100).toFixed(0)}%</span>
            </div>
          )}
        </div>

        <a
          href={match.competitor_url} target="_blank" rel="noopener noreferrer"
          className="flex items-center justify-center gap-1.5 w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-medium transition-colors"
        >
          View Product {Ico.external}
        </a>
        <p className="text-center text-xs text-gray-400 mt-2">
          Updated {new Date(match.last_checked).toLocaleDateString()}
        </p>
      </div>
    </div>
  );
}

export default function ProductDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const { addToast } = useToast();

  const [product, setProduct] = useState(null);
  const [matches, setMatches] = useState([]);
  const [priceHistory, setPriceHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [editingPrice, setEditingPrice] = useState(false);
  const [priceInput, setPriceInput] = useState('');
  const [savingPrice, setSavingPrice] = useState(false);
  const [storeConn, setStoreConn] = useState(null);
  const [editingProduct, setEditingProduct] = useState(false);
  const [productInput, setProductInput] = useState({ title: '', brand: '', sku: '', image_url: '' });
  const [savingProduct, setSavingProduct] = useState(false);
  const [showSitePicker, setShowSitePicker] = useState(false);
  const [scrapeTarget, setScrapeTarget] = useState('amazon.com');
  const [customSite, setCustomSite] = useState('');

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('marketintel_store_connection') || 'null');
      if (stored) setStoreConn(stored);
    } catch {}
  }, []);

  const handleSavePrice = async () => {
    const parsed = parseFloat(priceInput);
    if (isNaN(parsed) || parsed < 0) { setEditingPrice(false); return; }
    setSavingPrice(true);
    try {
      const updated = await api.updateProduct(product.id, { my_price: parsed });
      setProduct(p => ({ ...p, my_price: parsed }));
      addToast('Price updated', 'success');

      // Push to connected store
      const conn = storeConn;
      if (conn) {
        try {
          if (conn.type === 'woocommerce') {
            await api.pushPriceToWooCommerce(conn.credentials.store_url, conn.credentials.consumer_key, conn.credentials.consumer_secret, product.sku || '', product.title, parsed);
          } else {
            await api.pushPriceToShopify(conn.credentials.shop_url, conn.credentials.access_token, product.sku || '', product.title, parsed);
          }
          addToast(`Synced to ${conn.type === 'woocommerce' ? 'WooCommerce' : 'Shopify'}`, 'success');
        } catch (e) {
          addToast(`Store sync failed: ${e.message}`, 'error');
        }
      }
    } catch {
      addToast('Failed to update price', 'error');
    } finally {
      setSavingPrice(false);
      setEditingPrice(false);
    }
  };

  const startEditProduct = () => {
    setProductInput({ title: product.title || '', brand: product.brand || '', sku: product.sku || '', image_url: product.image_url || '' });
    setEditingProduct(true);
  };

  const handleSaveProduct = async () => {
    if (!productInput.title.trim()) { addToast('Title is required', 'error'); return; }
    setSavingProduct(true);
    try {
      await api.updateProduct(product.id, { title: productInput.title.trim(), brand: productInput.brand.trim(), sku: productInput.sku.trim(), image_url: productInput.image_url.trim() });
      setProduct(p => ({ ...p, ...productInput }));
      setEditingProduct(false);
      addToast('Product updated', 'success');
    } catch {
      addToast('Failed to update product', 'error');
    } finally {
      setSavingProduct(false);
    }
  };

  useEffect(() => { if (id) loadData(); }, [id]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [p, m, h] = await Promise.all([api.getProduct(id), api.getProductMatches(id), api.getProductPriceHistory(id)]);
      setProduct(p); setMatches(m); setPriceHistory(h);
    } catch { addToast('Failed to load product', 'error'); }
    finally { setLoading(false); }
  };

  const PRESET_SITES = [
    { label: 'Amazon', value: 'amazon.com' },
    { label: 'eBay', value: 'ebay.com' },
    { label: 'Walmart', value: 'walmart.com' },
    { label: 'Target', value: 'target.com' },
  ];

  const handleScrape = async (site) => {
    const target = site || scrapeTarget;
    setScraping(true);
    setShowSitePicker(false);
    addToast(`Searching ${target}…`, 'info');
    try {
      await api.scrapeProduct(id, target, 5);
      addToast('Scrape complete!', 'success');
      loadData();
    } catch { addToast('Scrape failed. Try again.', 'error'); }
    finally { setScraping(false); }
  };

  if (loading) return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">
        <div className="h-36 bg-white rounded-2xl border border-gray-100 animate-pulse" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 bg-white rounded-2xl border border-gray-100 animate-pulse" />)}
        </div>
        <div className="h-56 bg-white rounded-2xl border border-gray-100 animate-pulse" />
      </div>
    </Layout>
  );

  if (!product) return (
    <Layout>
      <div className="p-4 lg:p-6">
        <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
          <p className="text-gray-500 mb-3">Product not found</p>
          <Link href="/products" className="text-sm text-blue-600 hover:underline">Back to Products</Link>
        </div>
      </div>
    </Layout>
  );

  const lowestPrice = matches.length ? Math.min(...matches.map(m => m.latest_price || Infinity)) : null;
  const avgPrice = matches.length ? matches.reduce((s, m) => s + (m.latest_price || 0), 0) / matches.length : null;
  const priceRange = matches.length > 1 ? (Math.max(...matches.map(m => m.latest_price || 0)) - (lowestPrice || 0)) : null;

  return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">

        {/* Back link */}
        <Link href="/products" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 transition-colors">
          {Ico.back} Back to Products
        </Link>

        {/* Product header card */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          {editingProduct ? (
            /* ── Edit mode ── */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-gray-900">Edit Product Info</p>
                <div className="flex gap-2">
                  <button onClick={() => setEditingProduct(false)} className="px-3 py-1.5 border border-gray-200 hover:bg-gray-50 text-gray-600 rounded-lg text-sm font-medium transition-colors">
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveProduct} disabled={savingProduct || !productInput.title.trim()}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    {savingProduct ? <><span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />Saving…</> : 'Save Changes'}
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Product Title <span className="text-red-400">*</span></label>
                  <input
                    type="text" value={productInput.title}
                    onChange={e => setProductInput(p => ({ ...p, title: e.target.value }))}
                    className="w-full text-sm rounded-xl border border-gray-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
                    placeholder="Product title"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Brand</label>
                  <input
                    type="text" value={productInput.brand}
                    onChange={e => setProductInput(p => ({ ...p, brand: e.target.value }))}
                    className="w-full text-sm rounded-xl border border-gray-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
                    placeholder="Brand name"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">SKU</label>
                  <input
                    type="text" value={productInput.sku}
                    onChange={e => setProductInput(p => ({ ...p, sku: e.target.value }))}
                    className="w-full text-sm font-mono rounded-xl border border-gray-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
                    placeholder="SKU-001"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Image URL</label>
                  <div className="flex gap-2">
                    <input
                      type="url" value={productInput.image_url}
                      onChange={e => setProductInput(p => ({ ...p, image_url: e.target.value }))}
                      className="flex-1 text-sm rounded-xl border border-gray-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
                      placeholder="https://example.com/image.jpg"
                    />
                    {productInput.image_url && (
                      <div className="w-10 h-10 shrink-0 rounded-xl bg-gray-50 border border-gray-100 overflow-hidden flex items-center justify-center">
                        <img src={productInput.image_url} alt="preview" className="w-full h-full object-contain" onError={e => e.target.style.display = 'none'} />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* ── View mode ── */
            <div className="flex items-start gap-5">
              {/* Image */}
              <div className="w-20 h-20 shrink-0 rounded-xl bg-gray-50 border border-gray-100 overflow-hidden flex items-center justify-center">
                {product.image_url ? (
                  <img src={product.image_url} alt={product.title} className="w-full h-full object-contain" onError={e => e.target.style.display = 'none'} />
                ) : (
                  <div className="text-gray-200">{Ico.image}</div>
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <h1 className="text-xl font-bold text-gray-900 leading-tight">{product.title}</h1>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-sm text-gray-500">
                  {product.brand && <span>{product.brand}</span>}
                  {product.sku && <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">SKU: {product.sku}</span>}
                  <span className="text-xs">{new Date(product.created_at).toLocaleDateString()}</span>
                </div>
                {/* My Price — inline editable */}
                <div className="mt-2 flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-gray-500">My Price:</span>
                  {editingPrice ? (
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm text-gray-400">$</span>
                      <input
                        autoFocus
                        type="number" step="0.01" min="0"
                        value={priceInput}
                        onChange={e => setPriceInput(e.target.value)}
                        onBlur={handleSavePrice}
                        onKeyDown={e => { if (e.key === 'Enter') handleSavePrice(); if (e.key === 'Escape') setEditingPrice(false); }}
                        className="w-24 text-sm font-semibold text-gray-900 border-b-2 border-blue-500 bg-transparent focus:outline-none"
                      />
                      {savingPrice && <span className="text-xs text-gray-400 animate-pulse">saving…</span>}
                    </div>
                  ) : (
                    <button
                      onClick={() => { setPriceInput(product.my_price ?? ''); setEditingPrice(true); }}
                      className="text-sm font-semibold text-gray-900 hover:text-blue-600 transition-colors"
                      title="Click to edit your price"
                    >
                      {product.my_price != null ? `$${product.my_price.toFixed(2)}` : (
                        <span className="text-gray-400 font-normal text-xs">Set price</span>
                      )}
                    </button>
                  )}
                  {storeConn && product.my_price != null && !editingPrice && (
                    <button
                      onClick={async () => {
                        try {
                          if (storeConn.type === 'woocommerce') {
                            await api.pushPriceToWooCommerce(storeConn.credentials.store_url, storeConn.credentials.consumer_key, storeConn.credentials.consumer_secret, product.sku || '', product.title, product.my_price);
                          } else {
                            await api.pushPriceToShopify(storeConn.credentials.shop_url, storeConn.credentials.access_token, product.sku || '', product.title, product.my_price);
                          }
                          addToast(`Price pushed to ${storeConn.type === 'woocommerce' ? 'WooCommerce' : 'Shopify'}`, 'success');
                        } catch (e) {
                          addToast(`Sync failed: ${e.message}`, 'error');
                        }
                      }}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 text-xs font-medium hover:bg-blue-100 transition-colors"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                      Push to {storeConn.type === 'woocommerce' ? 'WooCommerce' : 'Shopify'}
                    </button>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="shrink-0 flex flex-col sm:flex-row gap-2">
                {/* Scrape button with site picker */}
                <div className="relative">
                  <div className="flex rounded-xl overflow-hidden border border-blue-600">
                    <button
                      onClick={() => handleScrape()} disabled={scraping}
                      className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors disabled:opacity-50"
                    >
                      {scraping ? (
                        <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Scraping…</>
                      ) : (
                        <>{Ico.search} {PRESET_SITES.find(s => s.value === scrapeTarget)?.label || scrapeTarget}</>
                      )}
                    </button>
                    <button
                      type="button"
                      disabled={scraping}
                      onClick={() => setShowSitePicker(p => !p)}
                      className="px-2 py-2.5 bg-blue-600 hover:bg-blue-700 text-white border-l border-blue-500 transition-colors disabled:opacity-50"
                      title="Choose site to scrape"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>
                    </button>
                  </div>

                  {/* Site picker dropdown */}
                  {showSitePicker && (
                    <div className="absolute top-full left-0 mt-1 w-56 bg-white rounded-xl border border-gray-200 shadow-lg z-20 p-2">
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide px-2 mb-1">Quick pick</p>
                      {PRESET_SITES.map(site => (
                        <button
                          key={site.value}
                          onClick={() => { setScrapeTarget(site.value); setCustomSite(''); setShowSitePicker(false); handleScrape(site.value); }}
                          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${scrapeTarget === site.value ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700 hover:bg-gray-50'}`}
                        >
                          {site.label}
                          <span className="text-gray-400 font-normal ml-1 text-xs">{site.value}</span>
                        </button>
                      ))}
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide px-2 mb-1">Custom domain</p>
                        <div className="flex gap-1 px-1">
                          <input
                            type="text"
                            value={customSite}
                            onChange={e => setCustomSite(e.target.value)}
                            placeholder="example.com"
                            className="flex-1 text-sm rounded-lg border border-gray-200 px-2 py-1.5 focus:outline-none focus:border-blue-400"
                            onKeyDown={e => {
                              if (e.key === 'Enter' && customSite.trim()) {
                                setScrapeTarget(customSite.trim());
                                setShowSitePicker(false);
                                handleScrape(customSite.trim());
                              }
                            }}
                          />
                          <button
                            type="button"
                            disabled={!customSite.trim()}
                            onClick={() => { setScrapeTarget(customSite.trim()); setShowSitePicker(false); handleScrape(customSite.trim()); }}
                            className="px-2 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors disabled:opacity-40"
                          >
                            Go
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <button onClick={startEditProduct} className="inline-flex items-center gap-2 px-4 py-2.5 border border-gray-200 hover:bg-gray-50 text-gray-700 rounded-xl text-sm font-medium transition-colors">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                  Edit
                </button>
                <Link
                  href={`/products/${id}/report?print=1`}
                  target="_blank"
                  className="inline-flex items-center gap-2 px-4 py-2.5 border border-gray-200 hover:bg-gray-50 text-gray-700 rounded-xl text-sm font-medium transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                  <span className="hidden sm:inline">PDF</span>
                </Link>
                <button onClick={loadData} className="inline-flex items-center gap-2 px-4 py-2.5 border border-gray-200 hover:bg-gray-50 text-gray-700 rounded-xl text-sm font-medium transition-colors">
                  {Ico.refresh}
                  <span className="hidden sm:inline">Refresh</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Competitors" value={matches.length} color="blue" icon={Ico.users} />
          <StatCard label="Lowest Price" value={lowestPrice != null ? `$${lowestPrice.toFixed(2)}` : '—'} sub="best deal" color="emerald" icon={Ico.dollar} />
          <StatCard label="Average Price" value={avgPrice ? `$${avgPrice.toFixed(2)}` : '—'} sub="market avg" color="violet" icon={Ico.avg} />
          <StatCard label="Price Range" value={priceRange != null ? `$${priceRange.toFixed(2)}` : '—'} sub="high – low" color="amber" icon={Ico.range} />
        </div>

        {/* Price history */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold text-gray-900">Price History</p>
            <span className="text-xs text-gray-400">{priceHistory.length} data point{priceHistory.length !== 1 ? 's' : ''}</span>
          </div>
          {priceHistory.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <div className="w-12 h-12 bg-gray-100 rounded-2xl flex items-center justify-center mb-3">{Ico.avg}</div>
              <p className="text-sm text-gray-500">No price history yet</p>
              <p className="text-xs text-gray-400 mt-1">Scrape competitors to start tracking</p>
            </div>
          ) : (
            <PriceHistoryChart data={priceHistory} />
          )}
        </div>

        {/* Competitor matches */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <p className="text-sm font-semibold text-gray-900 mb-4">Competitor Matches ({matches.length})</p>

          {matches.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-14 h-14 bg-gray-100 rounded-2xl flex items-center justify-center mb-4">
                {Ico.search}
              </div>
              <p className="text-sm font-medium text-gray-900">No matches yet</p>
              <p className="text-sm text-gray-500 mt-1 mb-4">Use the Scrape button above to find competitor products</p>
              <button
                onClick={() => handleScrape()} disabled={scraping}
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
              >
                {Ico.search} Scrape {PRESET_SITES.find(s => s.value === scrapeTarget)?.label || scrapeTarget}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {matches.map(m => <MatchCard key={m.id} match={m} />)}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
