import { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import api from '../../lib/api';

// ─── Helpers ────────────────────────────────────────────────────────────────

function rankStatus(rank) {
  if (rank <= 3)  return { label: 'Top 3',  color: 'emerald' };
  if (rank <= 10) return { label: 'Page 1', color: 'blue' };
  return          { label: 'Page 2+', color: 'red' };
}

function rankStatusStyles(color) {
  return {
    emerald: { bg: 'rgba(5,150,105,0.15)',  border: 'rgba(5,150,105,0.3)',  text: '#34d399' },
    blue:    { bg: 'rgba(37,99,235,0.15)',   border: 'rgba(37,99,235,0.3)',  text: '#60a5fa' },
    red:     { bg: 'rgba(239,68,68,0.15)',   border: 'rgba(239,68,68,0.3)',  text: '#f87171' },
  }[color] ?? {};
}

function ChangeCell({ change }) {
  if (change == null || change === 0)
    return <span style={{ color: '#9ca3af' }}>—</span>;
  const isGain = change > 0; // lower rank number = better, so negative delta = improvement
  // Convention: positive change value = rank number went up (worse); negative = improved
  // We display from user perspective: gaining means rank improved (number decreased)
  const color = isGain ? '#34d399' : '#f87171';
  const prefix = isGain ? '+' : '';
  return (
    <span className="font-semibold text-xs" style={{ color }}>
      {prefix}{change}
    </span>
  );
}

function TrendArrow({ change }) {
  if (change == null || change === 0) return <span style={{ color: '#9ca3af' }}>─</span>;
  if (change > 0)  return <span style={{ color: '#34d399' }}>▲</span>;
  return <span style={{ color: '#f87171' }}>▼</span>;
}

function StatusBadge({ rank }) {
  const { label, color } = rankStatus(rank);
  const s = rankStatusStyles(color);
  return (
    <span
      className="inline-block px-2 py-0.5 rounded-full text-xs font-semibold"
      style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.text }}
    >
      {label}
    </span>
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

// ─── Keyword Table ────────────────────────────────────────────────────────────

function KeywordTable({ keywords }) {
  if (!keywords || keywords.length === 0)
    return <EmptyState message="No keywords tracked for this product yet." />;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border)' }}>
            {['Keyword', 'Rank', 'Change (7d)', 'Trend', 'Best Ever', 'Status'].map((h) => (
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
          {keywords.map((kw, i) => (
            <tr
              key={i}
              className="transition-colors"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.025)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <td className="py-3 pr-4">
                <span className="font-medium text-white">{kw.keyword ?? kw.term ?? '—'}</span>
              </td>
              <td className="py-3 pr-4">
                <span className="text-white font-bold">
                  {kw.current_rank != null ? `#${kw.current_rank}` : '—'}
                </span>
              </td>
              <td className="py-3 pr-4">
                <ChangeCell change={kw.change_7d ?? kw.rank_change} />
              </td>
              <td className="py-3 pr-4">
                <TrendArrow change={kw.change_7d ?? kw.rank_change} />
              </td>
              <td className="py-3 pr-4" style={{ color: 'rgba(255,255,255,0.6)' }}>
                {kw.best_rank != null ? `#${kw.best_rank}` : '—'}
              </td>
              <td className="py-3">
                {kw.current_rank != null ? <StatusBadge rank={kw.current_rank} /> : <span style={{ color: 'var(--text-muted)' }}>—</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Movements Section ───────────────────────────────────────────────────────

function MovementsSection({ movements }) {
  if (!movements || movements.length === 0) return null;

  const sorted = [...movements].sort((a, b) => (b.change_7d ?? 0) - (a.change_7d ?? 0));
  const top = sorted.slice(0, 5);

  return (
    <div
      className="rounded-2xl overflow-hidden mt-5"
      style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
    >
      <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
        <h2 className="text-sm font-semibold text-white">This Week&apos;s Biggest Movers</h2>
        <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
          Keywords with the largest rank changes in the last 7 days
        </p>
      </div>
      <div className="p-5 space-y-2">
        {top.map((mv, i) => {
          const change = mv.change_7d ?? 0;
          const isGain = change > 0;
          const color = isGain ? '#34d399' : '#f87171';
          return (
            <div
              key={i}
              className="flex items-center gap-3 rounded-xl px-4 py-3 transition-colors"
              style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)' }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
            >
              <span
                className="text-lg font-black w-5 text-center shrink-0"
                style={{ color }}
              >
                {isGain ? '▲' : '▼'}
              </span>
              <span className="flex-1 font-medium text-white text-sm">
                {mv.keyword ?? mv.term ?? '—'}
              </span>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {mv.product_title ?? ''}
              </span>
              <span className="font-bold text-sm" style={{ color }}>
                {isGain ? '+' : ''}{change}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Track Keyword Form ───────────────────────────────────────────────────────

function TrackKeywordForm({ products }) {
  const [formProductId, setFormProductId] = useState('');
  const [keyword, setKeyword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState('');
  const [formError, setFormError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    setSuccess('');
    setFormError('');

    if (!formProductId) { setFormError('Please select a product.'); return; }
    if (!keyword.trim()) { setFormError('Please enter a keyword.'); return; }

    try {
      setSubmitting(true);
      await api.addKeyword(formProductId, keyword.trim());
      setSuccess(`"${keyword.trim()}" is now being tracked.`);
      setKeyword('');
    } catch (err) {
      setFormError('Failed to add keyword. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
    >
      <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
        <h2 className="text-sm font-semibold text-white">Track a New Keyword</h2>
        <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
          Start monitoring search rank for a keyword on a specific product
        </p>
      </div>
      <div className="p-5">
        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 flex-wrap">
          <select
            value={formProductId}
            onChange={(e) => setFormProductId(e.target.value)}
            className="rounded-xl px-4 py-2.5 text-sm font-medium outline-none transition-colors w-full sm:w-64"
            style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              color: formProductId ? 'var(--text)' : 'var(--text-muted)',
            }}
          >
            <option value="">— Select product —</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>{p.title}</option>
            ))}
          </select>

          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="e.g. wireless bluetooth headphones"
            className="flex-1 min-w-0 rounded-xl px-4 py-2.5 text-sm outline-none transition-all"
            style={{
              background: 'var(--bg-elevated)',
              border: formError ? '1px solid rgba(239,68,68,0.5)' : '1px solid var(--border)',
              color: 'var(--text)',
            }}
            onFocus={(e) => {
              if (!formError) e.target.style.borderColor = 'rgba(245,158,11,0.5)';
            }}
            onBlur={(e) => {
              if (!formError) e.target.style.borderColor = 'var(--border)';
            }}
          />

          <button
            type="submit"
            disabled={submitting}
            className="rounded-xl px-5 py-2.5 text-sm font-semibold transition-all shrink-0"
            style={{
              background: submitting ? 'rgba(245,158,11,0.3)' : 'rgba(245,158,11,0.9)',
              color: '#08080e',
              cursor: submitting ? 'not-allowed' : 'pointer',
              border: 'none',
            }}
            onMouseEnter={(e) => {
              if (!submitting) e.currentTarget.style.background = '#f59e0b';
            }}
            onMouseLeave={(e) => {
              if (!submitting) e.currentTarget.style.background = 'rgba(245,158,11,0.9)';
            }}
          >
            {submitting ? 'Adding…' : 'Start Tracking'}
          </button>
        </form>

        {/* Feedback Messages */}
        {success && (
          <div
            className="mt-4 flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-medium"
            style={{
              background: 'rgba(5,150,105,0.12)',
              border: '1px solid rgba(5,150,105,0.25)',
              color: '#34d399',
            }}
          >
            <span>✓</span>
            <span>{success}</span>
          </div>
        )}
        {formError && (
          <div
            className="mt-4 flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-medium"
            style={{
              background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.25)',
              color: '#f87171',
            }}
          >
            <span>✕</span>
            <span>{formError}</span>
          </div>
        )}

        <p className="mt-4 text-xs" style={{ color: 'var(--text-muted)' }}>
          Rank data is updated daily. New keywords may take up to 24 hours to show their first position.
        </p>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function KeywordRanksPage() {
  const [portfolioKeywords, setPortfolioKeywords] = useState(null);
  const [products, setProducts] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [productKeywords, setProductKeywords] = useState(null);
  const [movements, setMovements] = useState([]);
  const [tab, setTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadInitial() {
      try {
        setLoading(true);
        const [summary, prods, moves] = await Promise.all([
          api.getPortfolioKeywords(),
          api.getProducts(),
          api.getRankMovements(7),
        ]);
        setPortfolioKeywords(summary);
        setProducts(prods ?? []);
        setMovements(moves ?? []);
      } catch (err) {
        setError('Failed to load keyword rank data.');
      } finally {
        setLoading(false);
      }
    }
    loadInitial();
  }, []);

  useEffect(() => {
    if (!selectedProductId) {
      setProductKeywords(null);
      return;
    }
    async function loadProductKeywords() {
      try {
        setDetailLoading(true);
        const data = await api.getProductKeywords(selectedProductId);
        setProductKeywords(data);
      } catch {
        setProductKeywords(null);
      } finally {
        setDetailLoading(false);
      }
    }
    loadProductKeywords();
  }, [selectedProductId]);

  const summary = portfolioKeywords ?? {};
  const kwList = productKeywords?.keywords ?? productKeywords ?? [];

  // Derive best gain from movements
  const bestGain = movements.length
    ? movements.reduce((best, m) => ((m.change_7d ?? 0) > (best.change_7d ?? 0) ? m : best), movements[0])
    : null;

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">

        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">Keyword Rank Tracking</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Monitor where your products appear in search results for tracked keywords
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
              label="Keywords Ranked #1–3"
              value={summary.top_3_count ?? 0}
              sub="Top positions"
              color="emerald"
              icon="🥇"
            />
            <StatCard
              label="Keywords Ranked #4–10"
              value={summary.page_1_count ?? 0}
              sub="Competitive"
              color="amber"
              icon="📊"
            />
            <StatCard
              label="Keywords Ranked >10"
              value={summary.beyond_page_1_count ?? 0}
              sub="Needs work"
              color="red"
              icon="📉"
            />
            <StatCard
              label="Biggest Gain This Week"
              value={bestGain ? `+${bestGain.change_7d}` : '—'}
              sub={bestGain ? (bestGain.keyword ?? bestGain.term ?? 'keyword') : 'No movements yet'}
              color="blue"
              icon="⬆️"
            />
          </div>
        )}

        {/* Tabs */}
        <div>
          <div className="flex gap-1 mb-6">
            {['overview', 'track'].map((t) => {
              const label = t === 'overview' ? 'Overview' : 'Track New Keyword';
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

          {/* Overview Tab */}
          {tab === 'overview' && (
            <div className="space-y-5">
              {/* Product Selector */}
              <div
                className="rounded-2xl overflow-hidden"
                style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
              >
                <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                  <h2 className="text-sm font-semibold text-white">Select Product</h2>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                    View keyword rankings for a specific product
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
                      <option key={p.id} value={p.id}>{p.title}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Keyword Table */}
              {detailLoading && <Skeleton height={300} />}

              {!detailLoading && selectedProductId && (
                <div
                  className="rounded-2xl overflow-hidden"
                  style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
                >
                  <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                    <h2 className="text-sm font-semibold text-white">Tracked Keywords</h2>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      {kwList.length} keyword{kwList.length !== 1 ? 's' : ''} tracked · sorted by rank
                    </p>
                  </div>
                  <div className="p-5">
                    <KeywordTable
                      keywords={[...kwList].sort((a, b) => (a.current_rank ?? 999) - (b.current_rank ?? 999))}
                    />
                  </div>
                </div>
              )}

              {!selectedProductId && !detailLoading && (
                <EmptyState message="Select a product above to view its keyword rankings." />
              )}

              {/* Movements */}
              {!loading && <MovementsSection movements={movements} />}
            </div>
          )}

          {/* Track New Keyword Tab */}
          {tab === 'track' && (
            <div className="space-y-5">
              <TrackKeywordForm products={products} />

              {/* Tips */}
              <div
                className="rounded-2xl p-5"
                style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
              >
                <h3 className="text-sm font-semibold text-white mb-3">Tips for effective keyword tracking</h3>
                <ul className="space-y-2">
                  {[
                    'Use long-tail keywords (3–5 words) for more actionable rank data.',
                    'Track the exact phrases your customers search for on Amazon.',
                    'Monitor competitor product names to catch cross-shopping.',
                    'Compare rank over time — a 7-day trend is more reliable than a single snapshot.',
                  ].map((tip, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs" style={{ color: 'rgba(255,255,255,0.6)' }}>
                      <span style={{ color: '#f59e0b', flexShrink: 0 }}>•</span>
                      {tip}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
