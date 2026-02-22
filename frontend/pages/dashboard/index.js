import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { PriceHistoryChart, CompetitorComparisonChart } from '../../components/Charts';
import { useToast } from '../../components/Toast';
import api from '../../lib/api';

const Ico = {
  box:      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" /></svg>,
  users:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>,
  dollar:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  chart:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  search:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>,
  external: <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>,
};

function StatCard({ label, value, sub, color, icon }) {
  const bg = { blue: 'bg-blue-50 text-blue-600', violet: 'bg-violet-50 text-violet-600', emerald: 'bg-emerald-50 text-emerald-600', amber: 'bg-amber-50 text-amber-600' }[color];
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${bg}`}>{icon}</div>
      <div className="min-w-0">
        <p className="text-2xl font-bold text-gray-900 leading-none">{value ?? '—'}</p>
        <p className="text-xs text-gray-500 mt-1 truncate">{label}</p>
        {sub && <p className="text-xs text-gray-400 truncate">{sub}</p>}
      </div>
    </div>
  );
}

function StockBadge({ status }) {
  if (status === 'In Stock')    return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">In Stock</span>;
  if (status === 'Out of Stock') return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">Out of Stock</span>;
  return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700">Low Stock</span>;
}

export default function ComparisonDashboard() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [matches, setMatches] = useState([]);
  const [priceHistory, setPriceHistory] = useState([]);
  const [stats, setStats] = useState({});
  const [search, setSearch] = useState('');
  const [showCrawler, setShowCrawler] = useState(false);
  const [crawlerUrl, setCrawlerUrl] = useState('');
  const [crawling, setCrawling] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => { loadDashboardData(); }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const data = await api.getProducts();
      setProducts(data);
      const total = data.length;
      const totalMatches = data.reduce((s, p) => s + (p.competitor_count || 0), 0);
      const withPrices = data.filter(p => p.lowest_price);
      const avgPrice = withPrices.length ? withPrices.reduce((s, p) => s + p.lowest_price, 0) / withPrices.length : 0;
      const covered = data.filter(p => (p.competitor_count || 0) > 0).length;
      setStats({ total, totalMatches, avgPrice: avgPrice.toFixed(2), coverage: total > 0 ? ((covered / total) * 100).toFixed(0) : 0 });
    } catch { addToast('Failed to load dashboard', 'error'); }
    finally { setLoading(false); }
  };

  const handleSelect = async (product) => {
    if (selectedProduct?.id === product.id) return;
    setSelectedProduct(product); setLoadingDetail(true);
    try {
      const [m, h] = await Promise.all([api.getProductMatches(product.id), api.getProductPriceHistory(product.id)]);
      setMatches(m); setPriceHistory(h);
    } catch { addToast('Failed to load product data', 'error'); }
    finally { setLoadingDetail(false); }
  };

  const handleCrawl = async () => {
    if (!crawlerUrl) { addToast('Please enter a URL', 'warning'); return; }
    setCrawling(true);
    try {
      const r = await api.startSiteCrawl(crawlerUrl, 50, 3, true, new URL(crawlerUrl).hostname);
      addToast(`Done — ${r.products_imported} products imported`, 'success');
      setShowCrawler(false); setCrawlerUrl(''); loadDashboardData();
    } catch (e) { addToast('Crawl failed: ' + e.message, 'error'); }
    finally { setCrawling(false); }
  };

  const filtered = products.filter(p => p.title.toLowerCase().includes(search.toLowerCase()));

  if (loading) return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 bg-white rounded-2xl border border-gray-100 animate-pulse" />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="h-80 bg-white rounded-2xl border border-gray-100 animate-pulse" />
          <div className="lg:col-span-2 h-80 bg-white rounded-2xl border border-gray-100 animate-pulse" />
        </div>
      </div>
    </Layout>
  );

  return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">

        {/* Header */}
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Price Comparison</h1>
            <p className="text-sm text-gray-500 mt-0.5">Select a product to compare competitor pricing</p>
          </div>
          <button
            onClick={() => setShowCrawler(true)}
            className="shrink-0 inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors"
          >
            {Ico.search}
            <span className="hidden sm:inline">Auto-Crawl Site</span>
            <span className="sm:hidden">Crawl</span>
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Products" value={stats.total} color="blue" icon={Ico.box} />
          <StatCard label="Total Matches" value={stats.totalMatches} color="violet" icon={Ico.users} />
          <StatCard label="Avg Lowest Price" value={stats.avgPrice ? `$${stats.avgPrice}` : '—'} color="emerald" icon={Ico.dollar} />
          <StatCard label="Coverage" value={`${stats.coverage}%`} sub="products with data" color="amber" icon={Ico.chart} />
        </div>

        {/* Main panel */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

          {/* Product list */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-gray-100 space-y-3">
              <p className="text-sm font-semibold text-gray-900">Your Products</p>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">{Ico.search}</span>
                <input
                  value={search} onChange={e => setSearch(e.target.value)}
                  placeholder="Search…"
                  className="w-full pl-9 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {filtered.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-sm text-gray-500">No products</p>
                <Link href="/products/add" className="text-sm text-blue-600 hover:underline mt-1 inline-block">Add a product</Link>
              </div>
            ) : (
              <div className="overflow-y-auto max-h-[500px] divide-y divide-gray-50">
                {filtered.map(p => (
                  <button
                    key={p.id} onClick={() => handleSelect(p)}
                    className={`w-full text-left px-4 py-3.5 transition-colors border-l-2 ${selectedProduct?.id === p.id ? 'bg-blue-50 border-blue-500' : 'hover:bg-gray-50 border-transparent'}`}
                  >
                    <p className="text-sm font-medium text-gray-900 truncate">{p.title}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-gray-400">{p.competitor_count || 0} competitors</span>
                      {p.lowest_price && <span className="text-xs font-medium text-emerald-600">${p.lowest_price.toFixed(2)}</span>}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Comparison panel */}
          <div className="lg:col-span-2 space-y-4">
            {!selectedProduct ? (
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-16 text-center">
                <div className="w-14 h-14 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-7 h-7 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                </div>
                <p className="text-sm font-medium text-gray-900">Select a product</p>
                <p className="text-xs text-gray-400 mt-1">Pick from the list to view comparison</p>
              </div>
            ) : loadingDetail ? (
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-16 flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <>
                {/* Product header */}
                <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="text-base font-semibold text-gray-900 truncate">{selectedProduct.title}</h2>
                    <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-gray-500">
                      {selectedProduct.brand && <span>{selectedProduct.brand}</span>}
                      {selectedProduct.sku && <span>SKU: {selectedProduct.sku}</span>}
                      <span className="text-gray-400">{matches.length} match{matches.length !== 1 ? 'es' : ''}</span>
                    </div>
                  </div>
                  <Link href={`/products/${selectedProduct.id}`} className="shrink-0 text-xs text-blue-600 hover:underline whitespace-nowrap">View detail →</Link>
                </div>

                {/* Charts */}
                {matches.length > 0 && (
                  <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
                    <p className="text-sm font-semibold text-gray-900 mb-4">Price Comparison</p>
                    <CompetitorComparisonChart data={matches.map(m => ({ competitor_name: m.competitor_name, latest_price: m.latest_price }))} />
                  </div>
                )}
                {priceHistory.length > 0 && (
                  <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
                    <p className="text-sm font-semibold text-gray-900 mb-4">Price History</p>
                    <PriceHistoryChart data={priceHistory} />
                  </div>
                )}

                {/* Matches table */}
                <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                  <div className="px-5 py-4 border-b border-gray-100">
                    <p className="text-sm font-semibold text-gray-900">Matches ({matches.length})</p>
                  </div>
                  {matches.length === 0 ? (
                    <div className="p-8 text-center">
                      <p className="text-sm text-gray-500 mb-1">No matches yet</p>
                      <Link href={`/products/${selectedProduct.id}`} className="text-sm text-blue-600 hover:underline">Scrape competitors</Link>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="min-w-full">
                        <thead className="bg-gray-50 border-b border-gray-100">
                          <tr>
                            {['Competitor', 'Price', 'Stock', 'Match %', 'Checked', ''].map(h => (
                              <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                          {matches.map(m => (
                            <tr key={m.id} className="hover:bg-gray-50 transition-colors">
                              <td className="px-4 py-3">
                                <p className="text-sm font-medium text-gray-900">{m.competitor_name}</p>
                                <p className="text-xs text-gray-400 truncate max-w-[160px]">{m.competitor_product_title}</p>
                              </td>
                              <td className="px-4 py-3 text-sm font-bold text-blue-600">${m.latest_price?.toFixed(2) ?? '—'}</td>
                              <td className="px-4 py-3"><StockBadge status={m.stock_status} /></td>
                              <td className="px-4 py-3 text-sm text-gray-600">{m.match_score ? `${(m.match_score * 100).toFixed(0)}%` : '—'}</td>
                              <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">{new Date(m.last_checked).toLocaleDateString()}</td>
                              <td className="px-4 py-3">
                                <a href={m.competitor_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline">
                                  View {Ico.external}
                                </a>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Crawler modal */}
      {showCrawler && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40" onClick={() => setShowCrawler(false)} />
          <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">Auto-Crawl Competitor Site</h3>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Competitor URL</label>
            <input
              type="url" value={crawlerUrl} onChange={e => setCrawlerUrl(e.target.value)}
              placeholder="https://competitor-store.com"
              className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
            />
            <div className="bg-blue-50 rounded-xl p-4 mb-5 text-xs text-blue-800 space-y-1.5">
              {['Discovers all category pages', 'Finds all product pages', 'Extracts title, price & image', 'Auto-imports to your account'].map(s => (
                <div key={s} className="flex items-center gap-2">
                  <svg className="w-3.5 h-3.5 text-blue-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                  {s}
                </div>
              ))}
            </div>
            <div className="flex gap-3">
              <button onClick={() => setShowCrawler(false)} className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">Cancel</button>
              <button onClick={handleCrawl} disabled={crawling || !crawlerUrl} className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50">
                {crawling ? 'Crawling…' : 'Start Crawl'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
