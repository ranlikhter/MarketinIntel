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
  const styles = {
    blue:    { bg: 'rgba(37,99,235,0.12)',  border: 'rgba(37,99,235,0.2)',   text: '#60a5fa' },
    emerald: { bg: 'rgba(5,150,105,0.12)',  border: 'rgba(5,150,105,0.2)',   text: '#34d399' },
    amber:   { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.2)',  text: '#fbbf24' },
    violet:  { bg: 'rgba(124,58,237,0.12)', border: 'rgba(124,58,237,0.2)',  text: '#a78bfa' },
  }[color] || { bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.1)', text: '#9ca3af' };
  return (
    <div className="rounded-2xl p-5 flex items-center gap-4"
      style={{ background: styles.bg, border: `1px solid ${styles.border}` }}>
      <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'rgba(0,0,0,0.2)', color: styles.text }}>{icon}</div>
      <div className="min-w-0">
        <p className="text-2xl font-bold text-white leading-none">{value ?? '—'}</p>
        <p className="text-xs mt-1 truncate" style={{ color: 'rgba(255,255,255,0.5)' }}>{label}</p>
        {sub && <p className="text-xs truncate" style={{ color: 'rgba(255,255,255,0.3)' }}>{sub}</p>}
      </div>
    </div>
  );
}

function StockBadge({ status }) {
  if (status === 'In Stock')    return <span className="px-2 py-0.5 rounded-full text-xs font-medium text-emerald-400" style={{ background: 'rgba(5,150,105,0.12)', border: '1px solid rgba(5,150,105,0.2)' }}>In Stock</span>;
  if (status === 'Out of Stock') return <span className="px-2 py-0.5 rounded-full text-xs font-medium text-white/40" style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.08)' }}>Out of Stock</span>;
  return <span className="px-2 py-0.5 rounded-full text-xs font-medium text-amber-400" style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.2)' }}>Low Stock</span>;
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
  const [quickWins, setQuickWins] = useState(null);
  const [priceWars, setPriceWars] = useState([]);
  const [marginHealth, setMarginHealth] = useState(null);
  const [stockOpps, setStockOpps] = useState(null);

  useEffect(() => { loadDashboardData(); }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [data, wins, wars, health, opps] = await Promise.all([
        api.getProducts(),
        api.getQuickWins().catch(() => null),
        api.getPriceWars(7).catch(() => null),
        api.getMarginHealth().catch(() => null),
        api.getStockOpportunitySummary().catch(() => null),
      ]);
      setProducts(data);
      if (wins) setQuickWins(wins);
      if (wars?.price_wars?.length) setPriceWars(wars.price_wars);
      if (health) setMarginHealth(health);
      if (opps) setStockOpps(opps);
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
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }} />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="h-80 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }} />
          <div className="lg:col-span-2 h-80 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }} />
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
            <h1 className="text-xl font-bold text-white">Price Comparison</h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>Select a product to compare competitor pricing</p>
          </div>
          <button
            onClick={() => setShowCrawler(true)}
            className="shrink-0 inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90 shadow-gradient"
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

        {/* Quick Wins */}
        {quickWins && (
          quickWins.all_competitive ? (
            <div className="rounded-2xl px-5 py-4 flex items-center gap-3"
              style={{ background: 'rgba(16,185,129,0.07)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'rgba(16,185,129,0.15)' }}>
                <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              </div>
              <p className="text-sm text-emerald-400 font-medium">All prices competitive — nice work</p>
            </div>
          ) : (
            <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <div className="px-5 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
                <p className="text-sm font-semibold text-white">Quick Wins</p>
              </div>
              <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
                {quickWins.wins.map((w, i) => {
                  const colors = {
                    high:   { bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.25)',   dot: '#ef4444' },
                    medium: { bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.25)',  dot: '#f59e0b' },
                    low:    { bg: 'rgba(59,130,246,0.08)',  border: 'rgba(59,130,246,0.2)',   dot: '#3b82f6' },
                  }[w.severity] || {};
                  return (
                    <div key={i} className="flex items-center gap-4 px-5 py-3.5">
                      <div className="w-2 h-2 rounded-full shrink-0" style={{ background: colors.dot }} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white">{w.message}</p>
                        <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-muted)' }}>{w.detail}</p>
                      </div>
                      <Link href={w.link}
                        className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                        style={{ background: colors.bg, border: `1px solid ${colors.border}`, color: colors.dot }}>
                        {w.cta}
                      </Link>
                    </div>
                  );
                })}
              </div>
            </div>
          )
        )}

        {/* Price Wars */}
        {priceWars.length > 0 && (
          <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid rgba(239,68,68,0.3)' }}>
            <div className="px-5 py-3 flex items-center gap-2" style={{ borderBottom: '1px solid rgba(239,68,68,0.15)', background: 'rgba(239,68,68,0.06)' }}>
              <span className="text-red-400">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
              </span>
              <p className="text-sm font-semibold text-red-400">Price Wars Detected</p>
              <span className="ml-auto text-xs px-2 py-0.5 rounded-full font-medium" style={{ background: 'rgba(239,68,68,0.15)', color: '#ef4444' }}>{priceWars.length} active</span>
            </div>
            <div className="divide-y" style={{ borderColor: 'rgba(239,68,68,0.1)' }}>
              {priceWars.slice(0, 4).map((w) => {
                const ago = w.detected_at ? Math.round((Date.now() - new Date(w.detected_at)) / 60000) : null;
                const agoStr = ago == null ? '' : ago < 60 ? `${ago}m ago` : `${Math.round(ago / 60)}h ago`;
                return (
                  <div key={w.id} className="flex items-center gap-4 px-5 py-3.5">
                    <div className="shrink-0 w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'rgba(239,68,68,0.12)' }}>
                      <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0" /></svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">{w.product_title || `Product #${w.product_id}`}</p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                        {w.competitor_count} competitors dropped avg {w.avg_drop_pct}% &bull; {agoStr}
                      </p>
                    </div>
                    <Link href={`/products/${w.product_id}`}
                      className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                      style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', color: '#ef4444' }}>
                      View
                    </Link>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Margin Health */}
        {marginHealth && (
          <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid rgba(245,158,11,0.25)' }}>
            <div className="px-5 py-3 flex items-center gap-2" style={{ borderBottom: '1px solid rgba(245,158,11,0.12)', background: 'rgba(245,158,11,0.05)' }}>
              <svg className="w-4 h-4 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <p className="text-sm font-semibold text-amber-400">Margin Health</p>
              {marginHealth.avg_margin_pct != null && (
                <span className="ml-auto text-xs px-2 py-0.5 rounded-full font-medium" style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}>
                  Avg {marginHealth.avg_margin_pct}%
                </span>
              )}
            </div>
            <div className="divide-y" style={{ borderColor: 'rgba(245,158,11,0.1)' }}>
              {marginHealth.floor_enforcements_today > 0 && (
                <div className="flex items-center gap-4 px-5 py-3">
                  <span className="text-base shrink-0">🛡️</span>
                  <p className="text-sm flex-1" style={{ color: 'var(--text-muted)' }}>
                    <span className="text-white font-medium">{marginHealth.floor_enforcements_today}</span> below-cost suggestion{marginHealth.floor_enforcements_today !== 1 ? 's' : ''} blocked today
                  </p>
                </div>
              )}
              {marginHealth.autopilot_changes_today > 0 && (
                <div className="flex items-center gap-4 px-5 py-3">
                  <span className="text-base shrink-0">⚡</span>
                  <p className="text-sm flex-1" style={{ color: 'var(--text-muted)' }}>
                    <span className="text-white font-medium">{marginHealth.autopilot_changes_today}</span> price{marginHealth.autopilot_changes_today !== 1 ? 's' : ''} auto-updated by Autopilot
                  </p>
                </div>
              )}
              {marginHealth.pending_floor_breaches > 0 && (
                <div className="flex items-center gap-4 px-5 py-3">
                  <span className="text-base shrink-0">⚠️</span>
                  <p className="text-sm flex-1 text-amber-400">
                    {marginHealth.pending_floor_breaches} floor breach{marginHealth.pending_floor_breaches !== 1 ? 'es' : ''} awaiting approval
                  </p>
                  <Link href="/repricing?tab=pending"
                    className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium"
                    style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.25)', color: '#f59e0b' }}>
                    Review →
                  </Link>
                </div>
              )}
              {marginHealth.products_below_floor > 0 && (
                <div className="flex items-center gap-4 px-5 py-3">
                  <span className="text-base shrink-0">📉</span>
                  <p className="text-sm flex-1" style={{ color: 'var(--text-muted)' }}>
                    <span className="text-white font-medium">{marginHealth.products_below_floor}</span> product{marginHealth.products_below_floor !== 1 ? 's' : ''} currently priced below floor
                  </p>
                </div>
              )}
              {marginHealth.products_no_cost > 0 && (
                <div className="flex items-center gap-4 px-5 py-3">
                  <span className="text-base shrink-0">○</span>
                  <p className="text-sm flex-1" style={{ color: 'var(--text-muted)' }}>
                    <span className="text-white font-medium">{marginHealth.products_no_cost}</span> product{marginHealth.products_no_cost !== 1 ? 's' : ''} missing cost data
                  </p>
                  <Link href="/products"
                    className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium"
                    style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                    Fill in →
                  </Link>
                </div>
              )}
              {marginHealth.floor_enforcements_today === 0 && marginHealth.autopilot_changes_today === 0 &&
               marginHealth.pending_floor_breaches === 0 && marginHealth.products_below_floor === 0 &&
               marginHealth.products_no_cost === 0 && (
                <div className="px-5 py-4 text-sm text-center" style={{ color: 'var(--text-muted)' }}>
                  Add cost data to your products to enable margin tracking.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Stock Opportunities panel */}
        {stockOpps && (stockOpps.open_count > 0 || stockOpps.applied_today > 0) && (
          <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid rgba(16,185,129,0.3)' }}>
            <div className="flex items-center justify-between px-5 py-3" style={{ borderBottom: '1px solid var(--border)', background: 'rgba(16,185,129,0.06)' }}>
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
                <p className="text-sm font-semibold text-white">Stock Opportunities</p>
              </div>
              {stockOpps.open_count > 0 && (
                <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981' }}>
                  {stockOpps.open_count} open
                </span>
              )}
            </div>
            {stockOpps.open_count > 0 && (
              <div className="flex items-center gap-4 px-5 py-3">
                <span className="text-base shrink-0">📦</span>
                <p className="text-sm flex-1" style={{ color: 'var(--text-muted)' }}>
                  <span className="text-white font-medium">{stockOpps.open_count}</span> competitor{stockOpps.open_count !== 1 ? 's are' : ' is'} out of stock — raise prices to capture demand
                </p>
                <Link href="/opportunities"
                  className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold"
                  style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.3)', color: '#10b981' }}>
                  Review →
                </Link>
              </div>
            )}
            {stockOpps.applied_today > 0 && (
              <div className="flex items-center gap-4 px-5 py-3">
                <span className="text-base shrink-0">⚡</span>
                <p className="text-sm flex-1" style={{ color: 'var(--text-muted)' }}>
                  <span className="text-white font-medium">{stockOpps.applied_today}</span> price raise{stockOpps.applied_today !== 1 ? 's' : ''} auto-applied today
                  {stockOpps.total_revenue_estimate > 0 && (
                    <span className="text-emerald-400"> (+${stockOpps.total_revenue_estimate.toFixed(2)}/unit potential)</span>
                  )}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Main panel */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

          {/* Product list */}
          <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <div className="p-4 space-y-3" style={{ borderBottom: '1px solid var(--border)' }}>
              <p className="text-sm font-semibold text-white">Your Products</p>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }}>{Ico.search}</span>
                <input
                  value={search} onChange={e => setSearch(e.target.value)}
                  placeholder="Search…"
                  className="w-full pl-9 pr-3 py-2 glass-input rounded-xl text-sm focus:outline-none"
                />
              </div>
            </div>

            {filtered.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No products</p>
                <Link href="/products/add" className="text-sm text-amber-400 hover:text-amber-300 mt-1 inline-block">Add a product</Link>
              </div>
            ) : (
              <div className="overflow-y-auto max-h-[500px]">
                {filtered.map(p => (
                  <button
                    key={p.id} onClick={() => handleSelect(p)}
                    className={`w-full text-left px-4 py-3.5 transition-colors border-l-2 ${selectedProduct?.id === p.id ? 'border-amber-500' : 'border-transparent hover:bg-white/5'}`}
                    style={{ borderBottom: '1px solid var(--border)' }}
                  >
                    <p className="text-sm font-medium text-white truncate">{p.title}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{p.competitor_count || 0} competitors</span>
                      {p.lowest_price && <span className="text-xs font-medium text-amber-400">${p.lowest_price.toFixed(2)}</span>}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Comparison panel */}
          <div className="lg:col-span-2 space-y-4">
            {!selectedProduct ? (
              <div className="rounded-2xl p-16 text-center" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                </div>
                <p className="text-sm font-medium text-white">Select a product</p>
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Pick from the list to view comparison</p>
              </div>
            ) : loadingDetail ? (
              <div className="rounded-2xl p-16 flex items-center justify-center" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <>
                {/* Product header */}
                <div className="rounded-2xl p-5 flex items-start justify-between gap-3" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                  <div className="min-w-0">
                    <h2 className="text-base font-semibold text-white truncate">{selectedProduct.title}</h2>
                    <div className="flex flex-wrap items-center gap-3 mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                      {selectedProduct.brand && <span>{selectedProduct.brand}</span>}
                      {selectedProduct.sku && <span>SKU: {selectedProduct.sku}</span>}
                      <span>{matches.length} match{matches.length !== 1 ? 'es' : ''}</span>
                    </div>
                  </div>
                  <Link href={`/products/${selectedProduct.id}`} className="shrink-0 text-xs text-amber-400 hover:text-amber-300 whitespace-nowrap">View detail →</Link>
                </div>

                {/* Charts */}
                {matches.length > 0 && (
                  <div className="rounded-2xl p-5" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                    <p className="text-sm font-semibold text-white mb-4">Price Comparison</p>
                    <CompetitorComparisonChart data={matches.map(m => ({ competitor_name: m.competitor_name, latest_price: m.latest_price }))} />
                  </div>
                )}
                {priceHistory.length > 0 && (
                  <div className="rounded-2xl p-5" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                    <p className="text-sm font-semibold text-white mb-4">Price History</p>
                    <PriceHistoryChart data={priceHistory} />
                  </div>
                )}

                {/* Matches table */}
                <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                  <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                    <p className="text-sm font-semibold text-white">Matches ({matches.length})</p>
                  </div>
                  {matches.length === 0 ? (
                    <div className="p-8 text-center">
                      <p className="text-sm mb-1" style={{ color: 'var(--text-muted)' }}>No matches yet</p>
                      <Link href={`/products/${selectedProduct.id}`} className="text-sm text-amber-400 hover:text-amber-300">Scrape competitors</Link>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="min-w-full dark-table">
                        <thead>
                          <tr>
                            {['Competitor', 'Price', 'Stock', 'Match %', 'Checked', ''].map(h => (
                              <th key={h} className="text-left">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {matches.map(m => (
                            <tr key={m.id}>
                              <td>
                                <p className="text-sm font-medium text-white">{m.competitor_name}</p>
                                <p className="text-xs truncate max-w-[160px]" style={{ color: 'var(--text-muted)' }}>{m.competitor_product_title}</p>
                              </td>
                              <td className="text-sm font-bold text-amber-400">${m.latest_price?.toFixed(2) ?? '—'}</td>
                              <td><StockBadge status={m.stock_status} /></td>
                              <td className="text-sm text-white/60">{m.match_score ? `${(m.match_score * 100).toFixed(0)}%` : '—'}</td>
                              <td className="text-xs whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>{new Date(m.last_checked).toLocaleDateString()}</td>
                              <td>
                                <a href={m.competitor_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300">
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
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowCrawler(false)} />
          <div className="relative rounded-2xl shadow-glass-lg w-full max-w-md p-6"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-md)' }}>
            <h3 className="text-base font-semibold text-white mb-4">Auto-Crawl Competitor Site</h3>
            <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>Competitor URL</label>
            <input
              type="url" value={crawlerUrl} onChange={e => setCrawlerUrl(e.target.value)}
              placeholder="https://competitor-store.com"
              className="w-full px-3 py-2.5 glass-input rounded-xl text-sm focus:outline-none mb-4"
            />
            <div className="rounded-xl p-4 mb-5 text-xs space-y-1.5 text-amber-300"
              style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)' }}>
              {['Discovers all category pages', 'Finds all product pages', 'Extracts title, price & image', 'Auto-imports to your account'].map(s => (
                <div key={s} className="flex items-center gap-2">
                  <svg className="w-3.5 h-3.5 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                  {s}
                </div>
              ))}
            </div>
            <div className="flex gap-3">
              <button onClick={() => setShowCrawler(false)}
                className="flex-1 py-2.5 rounded-xl text-sm font-medium text-white/60 hover:text-white hover:bg-white/5 transition-colors"
                style={{ border: '1px solid var(--border)' }}>Cancel</button>
              <button onClick={handleCrawl} disabled={crawling || !crawlerUrl} className="flex-1 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90 shadow-gradient disabled:opacity-50">
                {crawling ? 'Crawling…' : 'Start Crawl'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
