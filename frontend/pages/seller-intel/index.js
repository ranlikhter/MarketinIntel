import { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import api from '../../lib/api';

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(
      new Date(dateStr)
    );
  } catch {
    return dateStr;
  }
}

function formatTimestamp(ts) {
  if (!ts) return '—';
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
    }).format(new Date(ts));
  } catch {
    return ts;
  }
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

// ─── Feedback Dots ───────────────────────────────────────────────────────────

function FeedbackDots({ pct }) {
  const filled = Math.round((pct ?? 0) / 20); // 0–5 dots
  return (
    <span className="flex gap-1 items-center">
      {[...Array(5)].map((_, i) => (
        <span
          key={i}
          className="w-2.5 h-2.5 rounded-full"
          style={{
            background: i < filled ? '#34d399' : 'rgba(255,255,255,0.1)',
          }}
        />
      ))}
    </span>
  );
}

// ─── Volatility Gauge ────────────────────────────────────────────────────────

function VolatilityGauge({ score }) {
  const pct = Math.min(100, Math.max(0, score ?? 0));
  const color = pct >= 70 ? '#f87171' : pct >= 40 ? '#fbbf24' : '#34d399';
  const label = pct >= 70 ? 'High Danger' : pct >= 40 ? 'Moderate' : 'Stable';

  return (
    <div className="flex flex-col items-center gap-2 py-4">
      <div className="relative w-32 h-16 overflow-hidden">
        {/* Semicircle track */}
        <svg viewBox="0 0 120 60" className="w-full h-full">
          <path
            d="M 10 60 A 50 50 0 0 1 110 60"
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="12"
            strokeLinecap="round"
          />
          <path
            d="M 10 60 A 50 50 0 0 1 110 60"
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${(pct / 100) * 157} 157`}
            style={{ transition: 'stroke-dasharray 0.6s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-end justify-center pb-1">
          <span className="text-xl font-bold" style={{ color }}>{pct}</span>
        </div>
      </div>
      <span className="text-xs font-semibold" style={{ color }}>{label}</span>
    </div>
  );
}

// ─── Seller Card ─────────────────────────────────────────────────────────────

function SellerCard({ seller }) {
  const isAmazon = seller.amazon_is_seller || seller.is_amazon;
  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-4 transition-all"
      style={{
        background: isAmazon ? 'rgba(239,68,68,0.06)' : 'var(--bg-elevated)',
        border: isAmazon ? '1px solid rgba(239,68,68,0.25)' : '1px solid var(--border)',
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-base font-bold text-white leading-tight">{seller.seller_name ?? 'Unknown Seller'}</p>
        {isAmazon && (
          <span
            className="shrink-0 px-2 py-0.5 rounded-full text-xs font-bold"
            style={{ background: 'rgba(239,68,68,0.2)', border: '1px solid rgba(239,68,68,0.4)', color: '#f87171' }}
          >
            Amazon 1P
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <p style={{ color: 'var(--text-muted)' }}>Feedback Rating</p>
          <div className="mt-1.5">
            <FeedbackDots pct={seller.positive_feedback_pct} />
          </div>
        </div>
        <div>
          <p style={{ color: 'var(--text-muted)' }}>Positive Feedback</p>
          <p className="text-white font-semibold mt-1">
            {seller.positive_feedback_pct != null ? `${seller.positive_feedback_pct}%` : '—'}
          </p>
        </div>
        <div>
          <p style={{ color: 'var(--text-muted)' }}>Competing On</p>
          <p className="text-white font-semibold mt-1">
            {seller.competing_products_count ?? seller.products_count ?? 0} products
          </p>
        </div>
        <div>
          <p style={{ color: 'var(--text-muted)' }}>First Seen</p>
          <p className="text-white font-semibold mt-1">{formatDate(seller.first_seen)}</p>
        </div>
      </div>
    </div>
  );
}

// ─── Buybox Timeline ─────────────────────────────────────────────────────────

function BuyboxTimeline({ history }) {
  if (!history || history.length === 0)
    return <EmptyState message="No buy box history available for this product." />;

  return (
    <div className="space-y-2">
      {history.map((entry, i) => {
        const isFirst = i === 0;
        return (
          <div
            key={i}
            className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm transition-colors"
            style={{
              background: isFirst ? 'rgba(96,165,250,0.08)' : 'rgba(255,255,255,0.02)',
              border: isFirst ? '1px solid rgba(96,165,250,0.2)' : '1px solid rgba(255,255,255,0.04)',
            }}
          >
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ background: isFirst ? '#60a5fa' : 'rgba(255,255,255,0.2)' }}
            />
            <span className="font-medium text-white flex-1">{entry.seller_name ?? '—'}</span>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {formatTimestamp(entry.timestamp)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function SellerIntelPage() {
  const [overview, setOverview] = useState(null);
  const [amazonThreats, setAmazonThreats] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [volatilityData, setVolatilityData] = useState(null);
  const [tab, setTab] = useState('profiles');
  const [loading, setLoading] = useState(true);
  const [volatilityLoading, setVolatilityLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadInitial() {
      try {
        setLoading(true);
        const [ov, threats, prods] = await Promise.all([
          api.getSellerOverview(),
          api.getAmazonThreats(),
          api.getProducts(),
        ]);
        setOverview(ov);
        setAmazonThreats(threats ?? []);
        setProducts(prods ?? []);
      } catch (err) {
        setError('Failed to load seller intelligence data.');
      } finally {
        setLoading(false);
      }
    }
    loadInitial();
  }, []);

  useEffect(() => {
    if (!selectedProductId) {
      setVolatilityData(null);
      return;
    }
    async function loadVolatility() {
      try {
        setVolatilityLoading(true);
        const data = await api.getBuyboxVolatility(selectedProductId);
        setVolatilityData(data);
      } catch {
        setVolatilityData(null);
      } finally {
        setVolatilityLoading(false);
      }
    }
    loadVolatility();
  }, [selectedProductId]);

  const stats = overview ?? {};
  const sellers = stats.sellers ?? [];

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">

        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">Seller Intelligence</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Who is actually selling on your products — and is Amazon coming for you?
          </p>
        </div>

        {/* Amazon Alert Banner */}
        {!loading && amazonThreats.length > 0 && (
          <div
            className="rounded-2xl p-5"
            style={{
              background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.3)',
            }}
          >
            <div className="flex items-start gap-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <p className="font-bold text-white text-base">
                  Amazon 1P Alert: Amazon is directly selling on{' '}
                  <span style={{ color: '#f87171' }}>{amazonThreats.length}</span> of your products
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {amazonThreats.map((threat, i) => (
                    <span
                      key={i}
                      className="px-3 py-1 rounded-full text-xs font-medium"
                      style={{
                        background: 'rgba(239,68,68,0.15)',
                        border: '1px solid rgba(239,68,68,0.35)',
                        color: '#f87171',
                      }}
                    >
                      {threat.product_title ?? threat.title ?? threat.asin ?? `Product ${i + 1}`}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Stat Cards */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => <Skeleton key={i} height={90} />)}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <StatCard
              label="Total Unique Sellers"
              value={stats.total_unique_sellers ?? sellers.length}
              sub="Across all products"
              color="violet"
              icon="🏪"
            />
            <StatCard
              label="Amazon 1P Threats"
              value={amazonThreats.length}
              sub="Products with Amazon selling"
              color="red"
              icon="🛡️"
            />
            <StatCard
              label="High Volatility Products"
              value={stats.high_volatility_products ?? 0}
              sub="Buy box changes frequently"
              color="amber"
              icon="⚡"
            />
            <StatCard
              label="Avg Seller Feedback"
              value={stats.avg_positive_feedback_pct != null ? `${stats.avg_positive_feedback_pct}%` : '—'}
              sub="Positive feedback average"
              color="blue"
              icon="⭐"
            />
          </div>
        )}

        {/* Tabs */}
        <div>
          <div className="flex gap-1 mb-6">
            {['profiles', 'buybox'].map((t) => {
              const label = t === 'profiles' ? 'Seller Profiles' : 'Buy Box Volatility';
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

          {/* Seller Profiles Tab */}
          {tab === 'profiles' && (
            <div
              className="rounded-2xl overflow-hidden"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
            >
              <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                <h2 className="text-sm font-semibold text-white">Active Sellers</h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  All sellers competing on your catalog
                </p>
              </div>
              <div className="p-5">
                {loading ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {[...Array(6)].map((_, i) => <Skeleton key={i} height={160} />)}
                  </div>
                ) : error ? (
                  <EmptyState message={error} />
                ) : sellers.length === 0 ? (
                  <EmptyState message="No sellers found in your catalog." />
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {sellers.map((seller, i) => (
                      <SellerCard key={seller.seller_id ?? i} seller={seller} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Buy Box Volatility Tab */}
          {tab === 'buybox' && (
            <div className="space-y-5">
              {/* Product Selector */}
              <div
                className="rounded-2xl overflow-hidden"
                style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
              >
                <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                  <h2 className="text-sm font-semibold text-white">Select Product</h2>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                    View buy box ownership history for a specific product
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

              {/* Volatility Content */}
              {volatilityLoading && <Skeleton height={300} />}

              {!volatilityLoading && selectedProductId && volatilityData && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                  {/* Gauge */}
                  <div
                    className="rounded-2xl overflow-hidden"
                    style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
                  >
                    <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                      <h2 className="text-sm font-semibold text-white">Volatility Score</h2>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                        0 = stable · 100 = extreme
                      </p>
                    </div>
                    <div className="p-5 flex flex-col items-center">
                      <VolatilityGauge score={volatilityData.volatility_score} />
                      <p className="text-xs text-center mt-2" style={{ color: 'var(--text-muted)' }}>
                        Based on {volatilityData.total_changes ?? 0} ownership changes
                      </p>
                    </div>
                  </div>

                  {/* Timeline */}
                  <div
                    className="lg:col-span-2 rounded-2xl overflow-hidden"
                    style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
                  >
                    <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                      <h2 className="text-sm font-semibold text-white">Ownership Timeline</h2>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                        Most recent buy box holders
                      </p>
                    </div>
                    <div className="p-5 max-h-80 overflow-y-auto">
                      <BuyboxTimeline history={volatilityData.history ?? volatilityData.price_history ?? []} />
                    </div>
                  </div>
                </div>
              )}

              {!volatilityLoading && selectedProductId && !volatilityData && (
                <EmptyState message="No buy box data available for this product." />
              )}

              {!selectedProductId && !volatilityLoading && (
                <EmptyState message="Select a product above to view buy box volatility." />
              )}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
