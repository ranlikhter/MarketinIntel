/**
 * Competitor Promotions Page
 *
 * Displays promotional offers (Buy X Get Y, BOGO, % discounts, free items, etc.)
 * detected on competitor product pages during scraping.
 */

import { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import api from '../lib/api';

// ─── Icons ────────────────────────────────────────────────────────────────────

const Ico = {
  gift:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" /></svg>,
  tag:     <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>,
  bolt:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  percent: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" /></svg>,
  filter:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>,
  refresh: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  ext:     <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>,
  empty:   <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" /></svg>,
};

// ─── Promotion type config ────────────────────────────────────────────────────

const TYPE_CONFIG = {
  bogo:      { label: 'BOGO',      icon: Ico.gift,    color: 'emerald', badge: 'Buy One Get One' },
  bundle:    { label: 'Bundle',    icon: Ico.tag,     color: 'blue',    badge: 'Buy X Get Y' },
  pct_off:   { label: '% Off',    icon: Ico.percent, color: 'amber',   badge: 'Qty Discount' },
  free_item: { label: 'Free Item', icon: Ico.gift,    color: 'violet',  badge: 'Free Gift' },
  other:     { label: 'Other',     icon: Ico.bolt,    color: 'slate',   badge: 'Promotion' },
};

const COLOR = {
  emerald: { bg: 'rgba(5,150,105,0.12)',   border: 'rgba(5,150,105,0.25)',   text: '#34d399' },
  blue:    { bg: 'rgba(37,99,235,0.12)',   border: 'rgba(37,99,235,0.25)',   text: '#60a5fa' },
  amber:   { bg: 'rgba(245,158,11,0.12)',  border: 'rgba(245,158,11,0.25)',  text: '#fbbf24' },
  violet:  { bg: 'rgba(124,58,237,0.12)', border: 'rgba(124,58,237,0.25)', text: '#a78bfa' },
  slate:   { bg: 'rgba(100,116,139,0.12)',border: 'rgba(100,116,139,0.25)',text: '#94a3b8' },
};

// ─── Components ───────────────────────────────────────────────────────────────

function StatCard({ label, value, icon, color }) {
  const c = COLOR[color] || COLOR.slate;
  return (
    <div className="rounded-2xl p-5 flex items-center gap-4"
         style={{ background: c.bg, border: `1px solid ${c.border}` }}>
      <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
           style={{ background: c.bg, color: c.text }}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-white leading-none">{value ?? 0}</p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
      </div>
    </div>
  );
}

function TypeBadge({ type }) {
  const cfg = TYPE_CONFIG[type] || TYPE_CONFIG.other;
  const c = COLOR[cfg.color] || COLOR.slate;
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
          style={{ background: c.bg, border: `1px solid ${c.border}`, color: c.text }}>
      {cfg.badge}
    </span>
  );
}

function PromoCard({ promo }) {
  const cfg = TYPE_CONFIG[promo.promo_type] || TYPE_CONFIG.other;
  const c = COLOR[cfg.color] || COLOR.slate;
  const seen = promo.last_seen_at ? new Date(promo.last_seen_at) : null;
  const daysAgo = seen ? Math.floor((Date.now() - seen.getTime()) / 86400000) : null;

  return (
    <div className="rounded-2xl p-5 transition-all hover:scale-[1.01]"
         style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
      <div className="flex items-start gap-3">
        {/* Type icon */}
        <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
             style={{ background: c.bg, color: c.text }}>
          {cfg.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <TypeBadge type={promo.promo_type} />
            {promo.is_active && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                    style={{ background: 'rgba(5,150,105,0.12)', border: '1px solid rgba(5,150,105,0.25)', color: '#34d399' }}>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse inline-block" />
                Active
              </span>
            )}
          </div>

          {/* Deal description */}
          <p className="text-sm font-semibold text-white leading-snug">{promo.description}</p>

          {/* Structured details */}
          {(promo.buy_qty || promo.get_qty || promo.discount_pct || promo.free_item_name) && (
            <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-xs" style={{ color: 'var(--text-muted)' }}>
              {promo.buy_qty && <span>Buy {promo.buy_qty}</span>}
              {promo.get_qty && <span>Get {promo.get_qty} Free</span>}
              {promo.discount_pct && <span>{promo.discount_pct}% off</span>}
              {promo.free_item_name && <span>Free: {promo.free_item_name}</span>}
            </div>
          )}

          {/* Meta row */}
          <div className="mt-2.5 flex items-center gap-3 text-xs" style={{ color: 'var(--text-muted)' }}>
            <span className="font-medium text-white/60">{promo.competitor_name}</span>
            <span>·</span>
            <span className="truncate max-w-xs">{promo.product_title}</span>
            {daysAgo !== null && (
              <>
                <span>·</span>
                <span>{daysAgo === 0 ? 'Today' : `${daysAgo}d ago`}</span>
              </>
            )}
            <a href={promo.competitor_url}
               target="_blank"
               rel="noopener noreferrer"
               className="ml-auto flex items-center gap-0.5 hover:text-white transition-colors">
              View page {Ico.ext}
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const PROMO_TYPES = [
  { value: '', label: 'All types' },
  { value: 'bogo', label: 'BOGO' },
  { value: 'bundle', label: 'Bundle / Buy X Get Y' },
  { value: 'pct_off', label: '% Discount' },
  { value: 'free_item', label: 'Free Item' },
  { value: 'other', label: 'Other' },
];

const DAYS_OPTIONS = [7, 14, 30, 60, 90];

export default function PromotionsPage() {
  const [promotions, setPromotions] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [promoType, setPromoType] = useState('');
  const [competitor, setCompetitor] = useState('');
  const [days, setDays] = useState(30);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ days });
      if (promoType) params.set('promo_type', promoType);
      if (competitor) params.set('competitor', competitor);

      const [promos, st] = await Promise.all([
        api.request(`/api/promotions?${params}`),
        api.request(`/api/promotions/stats?days=${days}`),
      ]);
      setPromotions(Array.isArray(promos) ? promos : []);
      setStats(st);
    } catch (err) {
      setError(err.message || 'Failed to load promotions');
    } finally {
      setLoading(false);
    }
  }, [promoType, competitor, days]);

  useEffect(() => { load(); }, [load]);

  // Competitors derived from results for the filter dropdown
  const competitorNames = [...new Set(promotions.map(p => p.competitor_name))].sort();

  return (
    <Layout title="Competitor Promotions">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Competitor Promotions</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Buy X Get Y, BOGO, bundles and other deals detected on competitor pages
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-white/70 hover:text-white transition-colors disabled:opacity-50"
          style={{ background: 'var(--bg-glass)', border: '1px solid var(--border)' }}
        >
          <span className={loading ? 'animate-spin' : ''}>{Ico.refresh}</span>
          Refresh
        </button>
      </div>

      {/* Stats row */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <StatCard label="Active promotions" value={stats.total_active} icon={Ico.bolt}    color="blue" />
          <StatCard label="BOGO deals"         value={stats.by_type?.bogo || 0}      icon={Ico.gift}    color="emerald" />
          <StatCard label="Bundle offers"      value={stats.by_type?.bundle || 0}    icon={Ico.tag}     color="amber" />
          <StatCard label="% Discounts"        value={stats.by_type?.pct_off || 0}   icon={Ico.percent} color="violet" />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <select
          value={promoType}
          onChange={e => setPromoType(e.target.value)}
          className="glass-input rounded-xl px-3 py-2 text-sm text-white focus:outline-none"
        >
          {PROMO_TYPES.map(t => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>

        <select
          value={competitor}
          onChange={e => setCompetitor(e.target.value)}
          className="glass-input rounded-xl px-3 py-2 text-sm text-white focus:outline-none"
        >
          <option value="">All competitors</option>
          {competitorNames.map(n => <option key={n} value={n}>{n}</option>)}
        </select>

        <select
          value={days}
          onChange={e => setDays(Number(e.target.value))}
          className="glass-input rounded-xl px-3 py-2 text-sm text-white focus:outline-none"
        >
          {DAYS_OPTIONS.map(d => <option key={d} value={d}>Last {d} days</option>)}
        </select>

        {(promoType || competitor) && (
          <button
            onClick={() => { setPromoType(''); setCompetitor(''); }}
            className="px-3 py-2 rounded-xl text-sm text-white/60 hover:text-white transition-colors"
            style={{ background: 'var(--bg-glass)', border: '1px solid var(--border)' }}
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Content */}
      {error && (
        <div className="rounded-2xl p-5 mb-4 text-sm text-red-400"
             style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {[1,2,3,4].map(i => (
            <div key={i} className="rounded-2xl h-24 animate-pulse"
                 style={{ background: 'var(--bg-surface)' }} />
          ))}
        </div>
      ) : promotions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
               style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
            {Ico.empty}
          </div>
          <p className="text-white font-semibold mb-1">No promotions detected yet</p>
          <p className="text-sm max-w-sm" style={{ color: 'var(--text-muted)' }}>
            Promotions are automatically extracted from competitor pages when your products are scraped.
            Try adjusting the date range or check back after the next scrape run.
          </p>
        </div>
      ) : (
        <>
          <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
            {promotions.length} promotion{promotions.length !== 1 ? 's' : ''} found
          </p>
          <div className="space-y-3">
            {promotions.map(p => <PromoCard key={p.id} promo={p} />)}
          </div>
        </>
      )}
    </Layout>
  );
}
