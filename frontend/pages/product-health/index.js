import { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import api from '../../lib/api';

// ─── Helpers ────────────────────────────────────────────────────────────────

function velocityColor(v) {
  if (v >= 20) return { bg: 'rgba(5,150,105,0.15)', border: 'rgba(5,150,105,0.3)', text: '#34d399' };
  if (v >= 5)  return { bg: 'rgba(245,158,11,0.15)', border: 'rgba(245,158,11,0.3)', text: '#fbbf24' };
  return { bg: 'rgba(255,255,255,0.06)', border: 'rgba(255,255,255,0.1)', text: '#9ca3af' };
}

function ratingColor(r) {
  if (r >= 4.5) return '#34d399';
  if (r >= 4.0) return '#fbbf24';
  return '#f87171';
}

function RatingDot({ rating }) {
  return (
    <span
      className="inline-block w-2 h-2 rounded-full mr-1.5"
      style={{ background: ratingColor(rating), flexShrink: 0 }}
    />
  );
}

function TrendArrow({ trend }) {
  if (trend === 'up')   return <span style={{ color: '#34d399' }}>▲</span>;
  if (trend === 'down') return <span style={{ color: '#f87171' }}>▼</span>;
  return <span style={{ color: '#9ca3af' }}>─</span>;
}

function VelocityBadge({ value }) {
  const s = velocityColor(value);
  return (
    <span
      className="inline-block px-2 py-0.5 rounded-full text-xs font-semibold"
      style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.text }}
    >
      +{value}/wk
    </span>
  );
}

function ListingScoreBar({ score }) {
  const pct = Math.min(100, Math.max(0, score ?? 0));
  const color = pct >= 70 ? '#34d399' : pct >= 40 ? '#fbbf24' : '#f87171';
  return (
    <div className="flex items-center gap-2 mt-1">
      <div
        className="flex-1 rounded-full overflow-hidden"
        style={{ background: 'rgba(255,255,255,0.07)', height: 6 }}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="text-xs font-medium w-6 text-right" style={{ color }}>{pct}</span>
    </div>
  );
}

// ─── Stat Card ───────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color, icon }) {
  const styles = {
    blue:    { bg: 'rgba(37,99,235,0.12)',  border: 'rgba(37,99,235,0.2)',   text: '#60a5fa' },
    emerald: { bg: 'rgba(5,150,105,0.12)',  border: 'rgba(5,150,105,0.2)',   text: '#34d399' },
    amber:   { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.2)',  text: '#fbbf24' },
    red:     { bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.2)',   text: '#f87171' },
    violet:  { bg: 'rgba(124,58,237,0.12)', border: 'rgba(124,58,237,0.2)',  text: '#a78bfa' },
  }[color] || { bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.1)', text: '#9ca3af' };
  return (
    <div
      className="rounded-2xl p-5 flex items-center gap-4 animate-fade-in"
      style={{ background: styles.bg, border: `1px solid ${styles.border}` }}
    >
      <div
        className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 text-xl"
        style={{ background: 'rgba(0,0,0,0.25)', color: styles.text }}
      >
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-white leading-none">{value ?? '—'}</p>
        <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.5)' }}>{label}</p>
        {sub && <p className="text-xs mt-0.5" style={{ color: styles.text }}>{sub}</p>}
      </div>
    </div>
  );
}

// ─── Skeleton ────────────────────────────────────────────────────────────────

function Skeleton({ height = 200 }) {
  return (
    <div
      className="rounded-xl animate-pulse"
      style={{ background: 'rgba(255,255,255,0.06)', height }}
    />
  );
}

// ─── Empty State ─────────────────────────────────────────────────────────────

function EmptyState({ message }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <div className="text-4xl">🔍</div>
      <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{message}</p>
    </div>
  );
}

// ─── Portfolio Table ──────────────────────────────────────────────────────────

function PortfolioTable({ rows }) {
  const sorted = [...rows].sort((a, b) => (b.velocity_7d ?? 0) - (a.velocity_7d ?? 0));

  if (!sorted.length) return <EmptyState message="No flagged products found." />;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border)' }}>
            {['Product', 'Competitor', '7d Velocity', '30d Velocity', 'Rating', 'Trend'].map((h) => (
              <th
                key={h}
                className="text-left pb-3 pr-4 font-semibold text-xs uppercase tracking-wider"
                style={{ color: 'var(--text-muted)' }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr
              key={i}
              className="transition-colors"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.025)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <td className="py-3 pr-4">
                <span className="font-medium text-white">{row.product_title ?? '—'}</span>
              </td>
              <td className="py-3 pr-4" style={{ color: 'var(--text-muted)' }}>
                {row.competitor_name ?? '—'}
              </td>
              <td className="py-3 pr-4">
                <VelocityBadge value={row.velocity_7d ?? 0} />
              </td>
              <td className="py-3 pr-4" style={{ color: 'rgba(255,255,255,0.6)' }}>
                +{row.velocity_30d ?? 0}/mo
              </td>
              <td className="py-3 pr-4">
                <span className="flex items-center">
                  <RatingDot rating={row.rating ?? 0} />
                  <span className="text-white font-medium">{row.rating?.toFixed(1) ?? '—'}</span>
                </span>
              </td>
              <td className="py-3">
                <TrendArrow trend={row.rating_trend} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Competitor Card ──────────────────────────────────────────────────────────

function CompetitorCard({ comp }) {
  const vel = comp.velocity_7d ?? 0;
  const vc = velocityColor(vel);

  return (
    <div
      className="rounded-2xl p-5"
      style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <p className="font-semibold text-white leading-tight">{comp.competitor_name ?? 'Unknown'}</p>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
            {comp.total_reviews ?? '—'} total reviews
          </p>
        </div>
        <span
          className="shrink-0 px-2 py-0.5 rounded-full text-xs font-bold"
          style={{ background: vc.bg, border: `1px solid ${vc.border}`, color: vc.text }}
        >
          +{vel}/wk
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs mb-3">
        <div>
          <p style={{ color: 'var(--text-muted)' }}>Rating</p>
          <p className="flex items-center mt-0.5">
            <RatingDot rating={comp.rating ?? 0} />
            <span className="text-white font-semibold">{comp.rating?.toFixed(1) ?? '—'}</span>
          </p>
        </div>
        <div>
          <p style={{ color: 'var(--text-muted)' }}>Questions</p>
          <p className="text-white font-semibold mt-0.5">{comp.questions_count ?? 0}</p>
        </div>
      </div>

      <div>
        <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
          Listing Score
        </p>
        <ListingScoreBar score={comp.listing_quality_score} />
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ProductHealthPage() {
  const [portfolioHealth, setPortfolioHealth] = useState(null);
  const [products, setProducts] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [productHealth, setProductHealth] = useState(null);
  const [tab, setTab] = useState('portfolio');
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadInitial() {
      try {
        setLoading(true);
        const [ph, prods] = await Promise.all([
          api.getPortfolioHealth(),
          api.getProducts(),
        ]);
        setPortfolioHealth(ph);
        setProducts(prods ?? []);
      } catch (err) {
        setError('Failed to load portfolio health data.');
      } finally {
        setLoading(false);
      }
    }
    loadInitial();
  }, []);

  useEffect(() => {
    if (!selectedProductId) {
      setProductHealth(null);
      return;
    }
    async function loadProductDetail() {
      try {
        setDetailLoading(true);
        const data = await api.getProductHealth(selectedProductId);
        setProductHealth(data);
      } catch (err) {
        setProductHealth(null);
      } finally {
        setDetailLoading(false);
      }
    }
    loadProductDetail();
  }, [selectedProductId]);

  const stats = portfolioHealth ?? {};

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">

        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">Product Health Monitor</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Track competitor review velocity, rating trends, and listing momentum
          </p>
        </div>

        {/* Stat Cards */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => <Skeleton key={i} height={90} />)}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <StatCard
              label="Surging Competitors"
              value={stats.surging_competitors ?? 0}
              sub="Gaining 20+ reviews/week"
              color="emerald"
              icon="🚀"
            />
            <StatCard
              label="Rating Threats"
              value={stats.rating_threats ?? 0}
              sub="Dropped rating this period"
              color="red"
              icon="⚠️"
            />
            <StatCard
              label="Products Monitored"
              value={stats.products_monitored ?? products.length}
              sub="Active tracking"
              color="blue"
              icon="📦"
            />
            <StatCard
              label="Avg Review Velocity (7d)"
              value={stats.avg_velocity_7d != null ? `+${stats.avg_velocity_7d}/wk` : '—'}
              sub="Across all competitors"
              color="amber"
              icon="📈"
            />
          </div>
        )}

        {/* Legend */}
        <div
          className="flex flex-wrap gap-4 rounded-xl px-4 py-3 text-xs"
          style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
        >
          <span>
            <span style={{ color: '#34d399' }}>● </span>
            <span style={{ color: 'rgba(255,255,255,0.6)' }}>+20/week = surging</span>
          </span>
          <span>
            <span style={{ color: '#fbbf24' }}>● </span>
            <span style={{ color: 'rgba(255,255,255,0.6)' }}>+5–20/week = growing</span>
          </span>
          <span>
            <span style={{ color: '#9ca3af' }}>● </span>
            <span style={{ color: 'rgba(255,255,255,0.6)' }}>&lt;5/week = stable</span>
          </span>
        </div>

        {/* Tabs */}
        <div>
          <div className="flex gap-1 mb-6">
            {['portfolio', 'detail'].map((t) => {
              const label = t === 'portfolio' ? 'Portfolio View' : 'Product Detail';
              const active = tab === t;
              return (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
                  style={{
                    background: active ? 'rgba(245,158,11,0.15)' : 'transparent',
                    color: active ? '#f59e0b' : 'var(--text-muted)',
                    border: active ? '1px solid rgba(245,158,11,0.3)' : '1px solid transparent',
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>

          {/* Portfolio View Tab */}
          {tab === 'portfolio' && (
            <div
              className="rounded-2xl overflow-hidden"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
            >
              <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                <h2 className="text-sm font-semibold text-white">Flagged Products</h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Competitors sorted by 7-day review velocity
                </p>
              </div>
              <div className="p-5">
                {loading ? (
                  <Skeleton height={240} />
                ) : error ? (
                  <EmptyState message={error} />
                ) : (
                  <PortfolioTable rows={stats.flagged_products ?? []} />
                )}
              </div>
            </div>
          )}

          {/* Product Detail Tab */}
          {tab === 'detail' && (
            <div className="space-y-5">
              {/* Product Selector */}
              <div
                className="rounded-2xl overflow-hidden"
                style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
              >
                <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                  <h2 className="text-sm font-semibold text-white">Select Product</h2>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                    Choose a product to view per-competitor analysis
                  </p>
                </div>
                <div className="p-5">
                  <select
                    value={selectedProductId}
                    onChange={(e) => setSelectedProductId(e.target.value)}
                    className="w-full sm:w-80 rounded-xl px-4 py-2.5 text-sm font-medium outline-none transition-colors"
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border)',
                      color: selectedProductId ? 'var(--text)' : 'var(--text-muted)',
                    }}
                  >
                    <option value="">— Select a product —</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.title}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Detail Content */}
              {detailLoading && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[...Array(3)].map((_, i) => <Skeleton key={i} height={160} />)}
                </div>
              )}

              {!detailLoading && selectedProductId && !productHealth && (
                <EmptyState message="No competitor data available for this product." />
              )}

              {!detailLoading && productHealth && (
                <>
                  {(productHealth.competitors ?? []).length === 0 ? (
                    <EmptyState message="No competitors tracked for this product." />
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                      {productHealth.competitors.map((comp, i) => (
                        <CompetitorCard key={i} comp={comp} />
                      ))}
                    </div>
                  )}
                </>
              )}

              {!selectedProductId && !detailLoading && (
                <EmptyState message="Select a product above to see competitor details." />
              )}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
