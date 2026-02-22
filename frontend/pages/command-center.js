/**
 * Command Center — Market Position Battle Station
 *
 * Shows every monitored product colored by competitive position:
 *   🔴 At Risk   — you're the most expensive
 *   🟡 Watching  — you're mid-range or slightly above average
 *   🟢 Winning   — you're at or below the cheapest competitor
 *   🔵 Opportunity — a competitor is out of stock (chance to raise price)
 *   ⚪ No Data   — not yet scraped
 *
 * Each card shows:
 *   • My Price vs Lowest Competitor (gap in $ and %)
 *   • Margin at my price (if cost_price is set)
 *   • Margin if I match the lowest (shows the trade-off)
 *   • Quick link to product detail
 *   • CSV download button
 */

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import api from '../lib/api';

// ─── Icons ────────────────────────────────────────────────────────────────────
const Ico = {
  download: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  ),
  arrow: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  ),
  refresh: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  search: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  ),
  sort: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 7h18M6 12h12M9 17h6" />
    </svg>
  ),
};

// ─── Position config ──────────────────────────────────────────────────────────
const POS = {
  at_risk: {
    label: 'At Risk',
    badge: 'bg-red-100 text-red-700 border border-red-200',
    bar: 'bg-red-500',
    ring: 'ring-red-200',
    dot: 'bg-red-500',
    desc: "You're most expensive — likely losing sales",
  },
  opportunity: {
    label: 'Opportunity',
    badge: 'bg-amber-100 text-amber-700 border border-amber-200',
    bar: 'bg-amber-400',
    ring: 'ring-amber-200',
    dot: 'bg-amber-400',
    desc: 'Competitor out of stock — consider raising price',
  },
  watching: {
    label: 'Watching',
    badge: 'bg-blue-100 text-blue-700 border border-blue-200',
    bar: 'bg-blue-400',
    ring: 'ring-blue-200',
    dot: 'bg-blue-400',
    desc: "You're mid-range — monitor closely",
  },
  winning: {
    label: 'Winning',
    badge: 'bg-emerald-100 text-emerald-700 border border-emerald-200',
    bar: 'bg-emerald-500',
    ring: 'ring-emerald-200',
    dot: 'bg-emerald-500',
    desc: "You're price-competitive",
  },
  no_data: {
    label: 'No Data',
    badge: 'bg-gray-100 text-gray-500 border border-gray-200',
    bar: 'bg-gray-300',
    ring: 'ring-gray-200',
    dot: 'bg-gray-300',
    desc: 'No competitor data yet — run a scrape',
  },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
function calcMargin(price, cost) {
  if (!price || !cost || price <= 0) return null;
  return ((price - cost) / price) * 100;
}

function classifyProduct(product, matches) {
  const myPrice = product.my_price;
  const costPrice = product.cost_price;

  if (!matches || matches.length === 0) {
    return { position: 'no_data', lowestCompetitor: null, avgCompetitor: null, oosCount: 0 };
  }

  const prices = matches
    .filter((m) => m.latest_price != null)
    .map((m) => m.latest_price);

  const oosCount = matches.filter(
    (m) => m.stock_status === 'Out of Stock' || m.in_stock === false
  ).length;

  const allOos = prices.length === 0 && oosCount > 0;
  const lowestCompetitor = prices.length > 0 ? Math.min(...prices) : null;
  const avgCompetitor =
    prices.length > 0 ? prices.reduce((a, b) => a + b, 0) / prices.length : null;

  // Opportunity: at least one competitor is out of stock AND has data
  if (oosCount > 0 && oosCount === matches.length) {
    return { position: 'opportunity', lowestCompetitor, avgCompetitor, oosCount };
  }

  if (!myPrice || lowestCompetitor == null) {
    return { position: 'no_data', lowestCompetitor, avgCompetitor, oosCount };
  }

  if (myPrice <= lowestCompetitor * 1.01) {
    return { position: 'winning', lowestCompetitor, avgCompetitor, oosCount };
  }
  if (avgCompetitor && myPrice > avgCompetitor * 1.05) {
    return { position: 'at_risk', lowestCompetitor, avgCompetitor, oosCount };
  }
  return { position: 'watching', lowestCompetitor, avgCompetitor, oosCount };
}

// ─── CSV Download ─────────────────────────────────────────────────────────────
async function downloadCSV(product) {
  try {
    const blob = await api.exportProductCSV(product.id);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `marketintel_${product.title.slice(0, 25).replace(/\s+/g, '_')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert('CSV export failed: ' + e.message);
  }
}

// ─── Product Card ─────────────────────────────────────────────────────────────
function ProductCard({ product, matches }) {
  const { position, lowestCompetitor, avgCompetitor, oosCount } = classifyProduct(
    product,
    matches
  );
  const pos = POS[position];
  const myPrice = product.my_price;
  const costPrice = product.cost_price;

  const gap = myPrice && lowestCompetitor ? myPrice - lowestCompetitor : null;
  const gapPct = gap && lowestCompetitor ? (gap / lowestCompetitor) * 100 : null;

  const myMargin = calcMargin(myPrice, costPrice);
  const matchMargin = calcMargin(lowestCompetitor, costPrice);

  return (
    <div
      className={`glass-card rounded-2xl overflow-hidden ring-1 ${pos.ring} hover:shadow-glass-lg transition-shadow`}
    >
      {/* Colour bar */}
      <div className={`h-1 w-full ${pos.bar}`} />

      <div className="p-4">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex-1 min-w-0">
            <Link
              href={`/products/${product.id}`}
              className="text-sm font-semibold text-slate-900 hover:text-blue-600 line-clamp-2 transition-colors"
            >
              {product.title}
            </Link>
            {product.brand && (
              <p className="text-xs text-slate-400 mt-0.5">{product.brand}</p>
            )}
          </div>
          <span
            className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${pos.badge}`}
          >
            {pos.label}
          </span>
        </div>

        {/* Price comparison */}
        <div className="bg-white/40 rounded-xl p-3 mb-3 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500">My price</span>
            <span className="font-semibold text-slate-900">
              {myPrice != null ? `$${myPrice.toFixed(2)}` : '—'}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500">Lowest competitor</span>
            <span className="font-semibold text-slate-900">
              {lowestCompetitor != null ? `$${lowestCompetitor.toFixed(2)}` : '—'}
            </span>
          </div>

          {gap != null && (
            <div className="flex items-center justify-between text-xs border-t border-white/40 pt-1.5 mt-1.5">
              <span className="text-slate-500">Gap</span>
              <span
                className={`font-bold ${
                  gap > 0 ? 'text-red-600' : 'text-emerald-600'
                }`}
              >
                {gap > 0 ? '+' : ''}${gap.toFixed(2)} ({gapPct > 0 ? '+' : ''}
                {gapPct?.toFixed(1)}%)
              </span>
            </div>
          )}
        </div>

        {/* Margin section (only when cost_price is set) */}
        {costPrice != null && (
          <div className="bg-violet-100/40 rounded-xl p-3 mb-3 space-y-1.5">
            <p className="text-xs font-semibold text-violet-700 mb-1">Margin Intelligence</p>
            {myMargin != null && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-violet-600">At my price</span>
                <span
                  className={`font-bold ${myMargin >= 20 ? 'text-emerald-600' : myMargin >= 0 ? 'text-amber-600' : 'text-red-600'}`}
                >
                  {myMargin.toFixed(1)}%
                </span>
              </div>
            )}
            {matchMargin != null && lowestCompetitor != null && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-violet-600">If I match ${lowestCompetitor.toFixed(2)}</span>
                <span
                  className={`font-bold ${matchMargin >= 20 ? 'text-emerald-600' : matchMargin >= 0 ? 'text-amber-600' : 'text-red-600'}`}
                >
                  {matchMargin.toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        )}

        {/* Stats row */}
        <div className="flex items-center gap-3 text-xs text-slate-400 mb-3">
          <span>{matches?.length ?? 0} competitors</span>
          {oosCount > 0 && (
            <span className="text-amber-600 font-medium">{oosCount} out of stock</span>
          )}
          {avgCompetitor && (
            <span>avg ${avgCompetitor.toFixed(2)}</span>
          )}
        </div>

        {/* Action row */}
        <div className="flex gap-2">
          <Link
            href={`/products/${product.id}`}
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 gradient-brand text-white text-xs font-semibold rounded-lg transition-opacity hover:opacity-90 shadow-gradient"
          >
            View Details {Ico.arrow}
          </Link>
          <button
            onClick={() => downloadCSV(product)}
            className="inline-flex items-center justify-center w-9 h-9 rounded-lg glass border border-white/60 hover:bg-white/40 text-slate-500 hover:text-slate-700 transition-colors"
            title="Download CSV"
          >
            {Ico.download}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Summary bar card ─────────────────────────────────────────────────────────
function SummaryCard({ label, count, total, color, dotColor, onClick, active }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <button
      onClick={onClick}
      className={`text-left glass-card rounded-2xl shadow-glass p-5 flex items-center gap-4 w-full transition-all hover:shadow-glass-lg ${
        active ? 'ring-2 ring-blue-300/60' : ''
      }`}
    >
      <div className={`w-3 h-3 rounded-full shrink-0 ${dotColor}`} />
      <div className="flex-1 min-w-0">
        <p className="text-2xl font-bold text-slate-900 leading-none">{count}</p>
        <p className="text-xs text-slate-500 mt-1">{label}</p>
      </div>
      <div className="text-right">
        <p className="text-sm font-semibold text-slate-400">{pct}%</p>
      </div>
    </button>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function CommandCenter() {
  const [products, setProducts] = useState([]);
  const [matchMap, setMatchMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('risk_first'); // risk_first | az | price_gap

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const prods = await api.getProducts();
      setProducts(prods || []);

      // Fetch matches for all products in parallel
      const entries = await Promise.all(
        (prods || []).map(async (p) => {
          try {
            const matches = await api.getProductMatches(p.id);
            return [p.id, matches || []];
          } catch {
            return [p.id, []];
          }
        })
      );
      setMatchMap(Object.fromEntries(entries));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  // Classify all products
  const classified = useMemo(() => {
    return products.map((p) => ({
      product: p,
      matches: matchMap[p.id] || [],
      ...classifyProduct(p, matchMap[p.id] || []),
    }));
  }, [products, matchMap]);

  // Summary counts
  const counts = useMemo(() => {
    const c = { at_risk: 0, opportunity: 0, watching: 0, winning: 0, no_data: 0 };
    classified.forEach(({ position }) => c[position]++);
    return c;
  }, [classified]);

  // Filter + search + sort
  const visible = useMemo(() => {
    let items = classified;
    if (filter !== 'all') items = items.filter((i) => i.position === filter);
    if (search.trim()) {
      const q = search.toLowerCase();
      items = items.filter(
        (i) =>
          i.product.title.toLowerCase().includes(q) ||
          (i.product.brand || '').toLowerCase().includes(q)
      );
    }
    if (sort === 'risk_first') {
      const ORDER = { at_risk: 0, opportunity: 1, watching: 2, winning: 3, no_data: 4 };
      items = [...items].sort((a, b) => (ORDER[a.position] ?? 5) - (ORDER[b.position] ?? 5));
    } else if (sort === 'az') {
      items = [...items].sort((a, b) => a.product.title.localeCompare(b.product.title));
    } else if (sort === 'price_gap') {
      items = [...items].sort((a, b) => {
        const gapA = a.product.my_price && a.lowestCompetitor
          ? a.product.my_price - a.lowestCompetitor
          : -999;
        const gapB = b.product.my_price && b.lowestCompetitor
          ? b.product.my_price - b.lowestCompetitor
          : -999;
        return gapB - gapA; // biggest gap (most at risk) first
      });
    }
    return items;
  }, [classified, filter, search, sort]);

  const total = classified.length;

  return (
    <Layout>
      <div className="p-4 lg:p-6">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Command Center</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Your market position at a glance — every product, every competitor
            </p>
          </div>
          <button
            onClick={loadAll}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 glass border border-white/60 rounded-xl text-sm font-medium text-slate-600 hover:bg-white/40 transition-colors shadow-glass disabled:opacity-50"
          >
            <span className={loading ? 'animate-spin' : ''}>{Ico.refresh}</span>
            Refresh
          </button>
        </div>

        {/* Summary tiles */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
          {[
            { key: 'all',         label: 'All Products',  dotColor: 'bg-gray-400',    count: total },
            { key: 'at_risk',     label: 'At Risk',       dotColor: 'bg-red-500',     count: counts.at_risk },
            { key: 'opportunity', label: 'Opportunity',   dotColor: 'bg-amber-400',   count: counts.opportunity },
            { key: 'watching',    label: 'Watching',      dotColor: 'bg-blue-400',    count: counts.watching },
            { key: 'winning',     label: 'Winning',       dotColor: 'bg-emerald-500', count: counts.winning },
          ].map(({ key, label, dotColor, count }) => (
            <SummaryCard
              key={key}
              label={label}
              count={count}
              total={total}
              dotColor={dotColor}
              active={filter === key}
              onClick={() => setFilter(key)}
            />
          ))}
        </div>

        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row gap-3 mb-5">
          <div className="relative flex-1">
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
              {Ico.search}
            </div>
            <input
              type="text"
              placeholder="Search products…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 glass-input rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400/50 transition-shadow"
            />
          </div>
          <div className="relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
              {Ico.sort}
            </div>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="pl-9 pr-8 py-2.5 glass border border-white/60 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-400/50 transition-shadow appearance-none"
            >
              <option value="risk_first">Sort: Biggest Risk First</option>
              <option value="price_gap">Sort: Largest Price Gap</option>
              <option value="az">Sort: A → Z</option>
            </select>
          </div>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="glass-card rounded-2xl h-64 animate-pulse">
                <div className="h-1 w-full bg-white/40 rounded-t-2xl" />
              </div>
            ))}
          </div>
        )}

        {/* Product grid */}
        {!loading && visible.length === 0 && (
          <div className="text-center py-16 text-slate-400">
            <p className="text-lg font-medium">No products match your filter</p>
            <p className="text-sm mt-1">Try changing the filter or search term</p>
          </div>
        )}

        {!loading && visible.length > 0 && (
          <>
            <p className="text-xs text-slate-400 mb-3">
              Showing {visible.length} of {total} products
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {visible.map(({ product, matches }) => (
                <ProductCard key={product.id} product={product} matches={matches} />
              ))}
            </div>
          </>
        )}

        {/* Legend */}
        {!loading && (
          <div className="mt-8 glass-card rounded-2xl shadow-glass p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-3">Position Legend</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {Object.entries(POS).filter(([k]) => k !== 'no_data').map(([key, p]) => (
                <div key={key} className="flex items-start gap-2.5">
                  <div className={`w-2.5 h-2.5 rounded-full mt-1 shrink-0 ${p.dot}`} />
                  <div>
                    <p className="text-xs font-semibold text-slate-700">{p.label}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{p.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </Layout>
  );
}
