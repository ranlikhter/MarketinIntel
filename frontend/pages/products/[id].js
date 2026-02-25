import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { PriceTimelineChart } from '../../components/Charts';
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
  image:   <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1} style={{ color: 'var(--text-muted)' }}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>,
  link:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>,
  close:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>,
  pin:     <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" /></svg>,
};

// ─── MANUAL URL MODAL ─────────────────────────────────────────────────────────
function AddUrlModal({ productId, onClose, onSuccess }) {
  const { addToast } = useToast();
  const [url, setUrl]   = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading]   = useState(false);
  const [phase, setPhase]       = useState('idle'); // idle | scraping | done | error
  const [errorMsg, setErrorMsg] = useState('');
  const [previewTitle, setPreviewTitle] = useState('');

  // Close on Escape
  const handleKey = (e) => { if (e.key === 'Escape') onClose(); };

  const isValidUrl = (s) => {
    try { return ['http:', 'https:'].includes(new URL(s).protocol); } catch { return false; }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isValidUrl(url)) { setErrorMsg('Enter a valid URL starting with https://'); return; }
    setLoading(true);
    setPhase('scraping');
    setErrorMsg('');
    try {
      const res = await api.scrapeProductUrl(productId, url.trim(), name.trim() || null);
      if (res.status === 'error') {
        setPhase('error');
        setErrorMsg(res.error || 'Scraping failed — the page may require a login or block bots.');
      } else {
        setPhase('done');
        setPreviewTitle(res.match?.competitor_product_title || url);
        addToast('Competitor URL added and scraped', 'success');
        onSuccess(res.match);
      }
    } catch (err) {
      setPhase('error');
      setErrorMsg(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      onKeyDown={handleKey}
    >
      <div className="rounded-2xl shadow-2xl w-full max-w-md overflow-hidden" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
        {/* Header */}
        <div className="flex items-start justify-between px-5 pt-5 pb-4" style={{ borderBottom: '1px solid var(--border)' }}>
          <div>
            <h2 className="text-base font-semibold text-white">Add competitor URL manually</h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
              Paste a product page URL you already know is the same item. We'll scrape it and link it here.
            </p>
          </div>
          <button onClick={onClose} className="ml-3 mt-0.5 hover:text-white/70 transition-colors shrink-0" style={{ color: 'var(--text-muted)' }}>
            {Ico.close}
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* URL input */}
          <div>
            <label className="block text-xs font-medium text-white/70 mb-1.5">
              Competitor product URL <span className="text-red-400">*</span>
            </label>
            <input
              type="url"
              autoFocus
              value={url}
              onChange={e => { setUrl(e.target.value); setErrorMsg(''); setPhase('idle'); }}
              placeholder="https://www.amazon.com/dp/B09XYZ..."
              className="glass-input w-full text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/50 transition-shadow font-mono text-white placeholder-white/30"
              disabled={loading}
              required
            />
            {errorMsg && (
              <p className="mt-1.5 text-xs text-red-400 flex items-center gap-1">
                <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                {errorMsg}
              </p>
            )}
          </div>

          {/* Optional competitor name */}
          <div>
            <label className="block text-xs font-medium text-white/70 mb-1.5">
              Competitor name <span className="font-normal" style={{ color: 'var(--text-muted)' }}>(optional — auto-detected from URL)</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. Amazon, Walmart, Argos…"
              className="glass-input w-full text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/50 transition-shadow text-white placeholder-white/30"
              disabled={loading}
            />
          </div>

          {/* What happens info box */}
          {phase === 'idle' && (
            <div className="rounded-xl p-3 flex gap-2.5 text-xs text-amber-400" style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.15)' }}>
              <svg className="w-3.5 h-3.5 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              <span>We'll open this URL, extract the price, stock status, images, and all available product data, then pin it to this product with a 100% match score.</span>
            </div>
          )}

          {/* Scraping progress */}
          {phase === 'scraping' && (
            <div className="rounded-xl p-4 flex items-center gap-3" style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.15)' }}>
              <span className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin shrink-0" />
              <div>
                <p className="text-sm font-medium text-amber-400">Scraping page…</p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Extracting price, stock, images and product details</p>
              </div>
            </div>
          )}

          {/* Success state */}
          {phase === 'done' && (
            <div className="rounded-xl p-3 flex items-start gap-2.5 text-xs text-emerald-400" style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <svg className="w-4 h-4 shrink-0 mt-0.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
              <div>
                <p className="font-semibold">Linked successfully</p>
                <p className="mt-0.5 line-clamp-2" style={{ color: 'var(--text-muted)' }}>{previewTitle}</p>
              </div>
            </div>
          )}

          {/* Footer buttons */}
          <div className="flex gap-2 pt-1">
            {phase === 'done' ? (
              <button
                type="button" onClick={onClose}
                className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-medium transition-colors"
              >
                Done
              </button>
            ) : (
              <>
                <button
                  type="button" onClick={onClose}
                  className="flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors hover:bg-white/5 text-white/70"
                  style={{ border: '1px solid var(--border)' }}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !url.trim()}
                  className="flex-1 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Scraping…</>
                  ) : (
                    <>{Ico.link} Scrape &amp; Link</>
                  )}
                </button>
              </>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── ADD-URL CARD (shown in matches grid) ─────────────────────────────────────
function AddUrlCard({ onClick }) {
  return (
    <button
      onClick={onClick}
      className="group border-2 border-dashed rounded-2xl flex flex-col items-center justify-center gap-3 py-10 px-4 text-center transition-all hover:bg-white/5"
      style={{ borderColor: 'var(--border)' }}
    >
      <div className="w-12 h-12 rounded-2xl flex items-center justify-center transition-colors" style={{ background: 'var(--bg-elevated)' }}>
        <svg className="w-6 h-6 transition-colors text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
      </div>
      <div>
        <p className="text-sm font-semibold text-white/70">Add from URL</p>
        <p className="text-xs mt-0.5 leading-snug max-w-[160px]" style={{ color: 'var(--text-muted)' }}>
          Know the exact product page? Paste the URL and we'll scrape it.
        </p>
      </div>
    </button>
  );
}

function StatCard({ label, sub, value, color, icon }) {
  const bg = {
    blue:    'rgba(59,130,246,0.12)',
    emerald: 'rgba(16,185,129,0.12)',
    violet:  'rgba(139,92,246,0.12)',
    amber:   'rgba(245,158,11,0.12)',
  }[color];
  const textColor = {
    blue:    '#60a5fa',
    emerald: '#34d399',
    violet:  '#a78bfa',
    amber:   '#f59e0b',
  }[color];
  return (
    <div className="rounded-2xl shadow-sm p-5 flex items-center gap-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
      <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: bg, color: textColor }}>{icon}</div>
      <div>
        <p className="text-2xl font-bold text-white leading-none">{value}</p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
        {sub && <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{sub}</p>}
      </div>
    </div>
  );
}

function StockBadge({ status }) {
  if (status === 'In Stock')    return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ background: 'rgba(16,185,129,0.12)', color: '#34d399' }}>In Stock</span>;
  if (status === 'Out of Stock') return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>Out of Stock</span>;
  return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ background: 'rgba(245,158,11,0.12)', color: '#f59e0b' }}>Low Stock</span>;
}

function StarRating({ rating }) {
  if (!rating) return null;
  const full = Math.floor(rating);
  const half = rating % 1 >= 0.5;
  return (
    <span className="flex items-center gap-0.5">
      {[...Array(5)].map((_, i) => (
        <svg key={i} className={`w-3 h-3 ${i < full ? 'text-amber-400' : i === full && half ? 'text-amber-300' : 'text-white/20'}`} fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </span>
  );
}

function MatchCard({ match, myPrice }) {
  const [imgErr, setImgErr] = useState(false);
  const priceDiff = myPrice != null && match.latest_price != null ? match.latest_price - myPrice : null;
  const priceDiffPct = priceDiff != null && myPrice ? ((priceDiff / myPrice) * 100).toFixed(1) : null;

  return (
    <div className="rounded-2xl shadow-sm overflow-hidden flex flex-col" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
      {/* Image with badge overlay */}
      <div className="relative h-36 flex items-center justify-center overflow-hidden" style={{ background: 'var(--bg-elevated)' }}>
        {!imgErr && match.image_url ? (
          <img src={match.image_url} alt={match.competitor_product_title} className="w-full h-full object-contain p-2" onError={() => setImgErr(true)} />
        ) : (
          <div>{Ico.image}</div>
        )}
        <div className="absolute top-2 left-2 flex flex-wrap gap-1">
          {match.is_prime && (
            <span className="px-1.5 py-0.5 bg-blue-600 text-white text-xs font-bold rounded">Prime</span>
          )}
          {match.promotion_label && (
            <span className="px-1.5 py-0.5 bg-red-500 text-white text-xs font-semibold rounded truncate max-w-[120px]" title={match.promotion_label}>
              {match.promotion_label}
            </span>
          )}
          {match.product_condition && match.product_condition !== 'New' && (
            <span className="px-1.5 py-0.5 text-xs font-semibold rounded" style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}>{match.product_condition}</span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="p-4 flex-1 flex flex-col">
        {/* Source + match score */}
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>{match.competitor_name}</span>
          {match.match_score != null && (
            match.match_score === 100 ? (
              <span className="inline-flex items-center gap-1 text-xs font-semibold px-1.5 py-0.5 rounded-full" style={{ color: '#a78bfa', background: 'rgba(139,92,246,0.12)' }} title="Manually pinned by you">
                {Ico.pin} Pinned
              </span>
            ) : (
              <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }} title="Auto match confidence">{match.match_score.toFixed(0)}% match</span>
            )
          )}
        </div>

        {/* Title */}
        <p className="text-sm font-medium text-white line-clamp-2 mb-1">{match.competitor_product_title}</p>

        {/* Variant */}
        {match.variant && (
          <p className="text-xs mb-2 truncate" style={{ color: 'var(--text-muted)' }} title={match.variant}>{match.variant}</p>
        )}

        {/* Rating */}
        {(match.rating != null || match.review_count != null) && (
          <div className="flex items-center gap-1.5 mb-3">
            {match.rating != null && <StarRating rating={match.rating} />}
            {match.rating != null && <span className="text-xs font-semibold text-white/70">{match.rating.toFixed(1)}</span>}
            {match.review_count != null && <span className="text-xs" style={{ color: 'var(--text-muted)' }}>({match.review_count.toLocaleString()})</span>}
          </div>
        )}

        {/* Price block */}
        <div className="rounded-xl p-3 mb-3 space-y-1.5" style={{ background: 'var(--bg-elevated)' }}>
          <div className="flex items-center justify-between">
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Price</span>
            <div className="flex items-center gap-2">
              {match.was_price && (
                <span className="text-xs line-through" style={{ color: 'var(--text-muted)' }}>${match.was_price.toFixed(2)}</span>
              )}
              <span className="text-base font-bold text-amber-400">
                {match.latest_price != null ? `$${match.latest_price.toFixed(2)}` : '—'}
              </span>
              {match.discount_pct != null && (
                <span className="text-xs font-bold text-red-400">-{match.discount_pct.toFixed(0)}%</span>
              )}
            </div>
          </div>
          {match.shipping_cost != null && (
            <div className="flex items-center justify-between">
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Shipping</span>
              <span className={`text-xs font-medium ${match.shipping_cost === 0 ? 'text-emerald-400' : 'text-white/70'}`}>
                {match.shipping_cost === 0 ? '✓ Free' : `+$${match.shipping_cost.toFixed(2)}`}
              </span>
            </div>
          )}
          {match.total_price != null && match.shipping_cost > 0 && (
            <div className="flex items-center justify-between pt-1.5" style={{ borderTop: '1px solid var(--border)' }}>
              <span className="text-xs font-semibold text-white/70">Total landed</span>
              <span className="text-sm font-bold text-white">${match.total_price.toFixed(2)}</span>
            </div>
          )}
          {priceDiff != null && (
            <div className="flex items-center justify-between pt-1.5" style={{ borderTop: '1px solid var(--border)' }}>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>vs My Price</span>
              <span className={`text-xs font-bold ${priceDiff < 0 ? 'text-red-400' : priceDiff > 0 ? 'text-emerald-400' : 'text-white/50'}`}>
                {priceDiff > 0 ? `+$${priceDiff.toFixed(2)} (+${priceDiffPct}%)` : priceDiff < 0 ? `-$${Math.abs(priceDiff).toFixed(2)} (${Math.abs(priceDiffPct)}%)` : 'Same'}
              </span>
            </div>
          )}
        </div>

        {/* Meta row: stock + fulfillment + seller */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-3 text-xs" style={{ color: 'var(--text-muted)' }}>
          <StockBadge status={match.stock_status} />
          {match.fulfillment_type && <span>{match.fulfillment_type}</span>}
          {match.seller_name && <span className="truncate max-w-[90px]" title={match.seller_name}>by {match.seller_name}</span>}
        </div>

        {/* Category */}
        {match.category && (
          <p className="text-xs mb-2 truncate" style={{ color: 'var(--text-muted)' }} title={match.category}>{match.category}</p>
        )}

        <a
          href={match.competitor_url} target="_blank" rel="noopener noreferrer"
          className="mt-auto flex items-center justify-center gap-1.5 w-full py-2 gradient-brand text-white rounded-xl text-xs font-medium transition-colors"
        >
          View Product {Ico.external}
        </a>
        <p className="text-center text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
          Updated {match.last_checked ? new Date(match.last_checked).toLocaleDateString() : '—'}
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
  const [myPriceHistory, setMyPriceHistory] = useState([]);
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
  const [showAddUrl, setShowAddUrl] = useState(false);
  const cancelPriceRef = useRef(false);

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
      const [p, m, h, mph] = await Promise.all([
        api.getProduct(id),
        api.getProductMatches(id),
        api.getProductPriceHistory(id),
        api.getMyPriceHistory(id).catch(() => []),
      ]);
      setProduct(p); setMatches(m); setPriceHistory(h); setMyPriceHistory(mph || []);
    } catch { addToast('Failed to load product', 'error'); }
    finally { setLoading(false); }
  };

  const PRESET_SITES = [
    { label: 'Amazon', value: 'amazon.com' },
    { label: 'eBay', value: 'ebay.com' },
    { label: 'Walmart', value: 'walmart.com' },
    { label: 'Target', value: 'target.com' },
  ];

  const handleUrlMatchSuccess = (newMatch) => {
    if (!newMatch) return;
    setMatches(prev => {
      // If it's an update to an existing match, replace it; otherwise prepend
      const exists = prev.find(m => m.id === newMatch.id);
      if (exists) return prev.map(m => m.id === newMatch.id ? { ...m, ...newMatch } : m);
      return [newMatch, ...prev];
    });
  };

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
        <div className="h-36 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }} />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }} />)}
        </div>
        <div className="h-56 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }} />
      </div>
    </Layout>
  );

  if (!product) return (
    <Layout>
      <div className="p-4 lg:p-6">
        <div className="rounded-2xl p-12 text-center" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <p className="mb-3" style={{ color: 'var(--text-muted)' }}>Product not found</p>
          <Link href="/products" className="text-sm text-amber-400 hover:text-amber-300 hover:underline">Back to Products</Link>
        </div>
      </div>
    </Layout>
  );

  const pricedMatches = matches.filter(m => m.latest_price != null);
  const lowestPrice = pricedMatches.length ? Math.min(...pricedMatches.map(m => m.latest_price)) : null;
  const avgPrice = pricedMatches.length ? pricedMatches.reduce((s, m) => s + m.latest_price, 0) / pricedMatches.length : null;
  const priceRange = pricedMatches.length > 1 ? (Math.max(...pricedMatches.map(m => m.latest_price)) - lowestPrice) : null;

  return (
    <Layout>
      {showAddUrl && (
        <AddUrlModal
          productId={id}
          onClose={() => setShowAddUrl(false)}
          onSuccess={(match) => { handleUrlMatchSuccess(match); }}
        />
      )}
      <div className="p-4 lg:p-6 space-y-5">

        {/* Back link */}
        <Link href="/products" className="inline-flex items-center gap-1.5 text-sm hover:text-white transition-colors" style={{ color: 'var(--text-muted)' }}>
          {Ico.back} Back to Products
        </Link>

        {/* Product header card */}
        <div className="rounded-2xl shadow-sm p-5" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          {editingProduct ? (
            /* ── Edit mode ── */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-white">Edit Product Info</p>
                <div className="flex gap-2">
                  <button onClick={() => setEditingProduct(false)} className="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors hover:bg-white/5 text-white/70" style={{ border: '1px solid var(--border)' }}>
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveProduct} disabled={savingProduct || !productInput.title.trim()}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 gradient-brand text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    {savingProduct ? <><span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />Saving…</> : 'Save Changes'}
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-white/70 mb-1">Product Title <span className="text-red-400">*</span></label>
                  <input
                    type="text" value={productInput.title}
                    onChange={e => setProductInput(p => ({ ...p, title: e.target.value }))}
                    className="glass-input w-full text-sm rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/50 text-white placeholder-white/30"
                    placeholder="Product title"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-white/70 mb-1">Brand</label>
                  <input
                    type="text" value={productInput.brand}
                    onChange={e => setProductInput(p => ({ ...p, brand: e.target.value }))}
                    className="glass-input w-full text-sm rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/50 text-white placeholder-white/30"
                    placeholder="Brand name"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-white/70 mb-1">SKU</label>
                  <input
                    type="text" value={productInput.sku}
                    onChange={e => setProductInput(p => ({ ...p, sku: e.target.value }))}
                    className="glass-input w-full text-sm font-mono rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/50 text-white placeholder-white/30"
                    placeholder="SKU-001"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-white/70 mb-1">Image URL</label>
                  <div className="flex gap-2">
                    <input
                      type="url" value={productInput.image_url}
                      onChange={e => setProductInput(p => ({ ...p, image_url: e.target.value }))}
                      className="glass-input flex-1 text-sm rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/50 text-white placeholder-white/30"
                      placeholder="https://example.com/image.jpg"
                    />
                    {productInput.image_url && (
                      <div className="w-10 h-10 shrink-0 rounded-xl overflow-hidden flex items-center justify-center" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
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
              <div className="w-20 h-20 shrink-0 rounded-xl overflow-hidden flex items-center justify-center" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                {product.image_url ? (
                  <img src={product.image_url} alt={product.title} className="w-full h-full object-contain" onError={e => e.target.style.display = 'none'} />
                ) : (
                  <div>{Ico.image}</div>
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <h1 className="text-xl font-bold text-white leading-tight">{product.title}</h1>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
                  {product.brand && <span>{product.brand}</span>}
                  {product.sku && <span className="font-mono text-xs px-2 py-0.5 rounded" style={{ background: 'var(--bg-elevated)' }}>SKU: {product.sku}</span>}
                  <span className="text-xs">{new Date(product.created_at).toLocaleDateString()}</span>
                </div>
                {/* My Price — inline editable */}
                <div className="mt-2 flex items-center gap-2 flex-wrap">
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>My Price:</span>
                  {editingPrice ? (
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm" style={{ color: 'var(--text-muted)' }}>$</span>
                      <input
                        autoFocus
                        type="number" step="0.01" min="0"
                        value={priceInput}
                        onChange={e => setPriceInput(e.target.value)}
                        onBlur={() => { if (!cancelPriceRef.current) handleSavePrice(); cancelPriceRef.current = false; }}
                        onKeyDown={e => { if (e.key === 'Enter') { e.target.blur(); } if (e.key === 'Escape') { cancelPriceRef.current = true; setEditingPrice(false); } }}
                        className="w-24 text-sm font-semibold text-white border-b-2 border-amber-500 bg-transparent focus:outline-none"
                      />
                      {savingPrice && <span className="text-xs animate-pulse" style={{ color: 'var(--text-muted)' }}>saving…</span>}
                    </div>
                  ) : (
                    <button
                      onClick={() => { setPriceInput(product.my_price ?? ''); setEditingPrice(true); }}
                      className="text-sm font-semibold text-white hover:text-amber-400 transition-colors"
                      title="Click to edit your price"
                    >
                      {product.my_price != null ? `$${product.my_price.toFixed(2)}` : (
                        <span className="font-normal text-xs" style={{ color: 'var(--text-muted)' }}>Set price</span>
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
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium hover:bg-white/5 transition-colors text-amber-400"
                      style={{ background: 'rgba(245,158,11,0.1)' }}
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
                  <div className="flex rounded-xl overflow-hidden" style={{ border: '1px solid rgba(245,158,11,0.5)' }}>
                    <button
                      onClick={() => handleScrape()} disabled={scraping}
                      className="inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white text-sm font-medium transition-colors disabled:opacity-50"
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
                      className="px-2 py-2.5 gradient-brand text-white transition-colors disabled:opacity-50"
                      style={{ borderLeft: '1px solid rgba(255,255,255,0.15)' }}
                      title="Choose site to scrape"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>
                    </button>
                  </div>

                  {/* Site picker dropdown */}
                  {showSitePicker && (
                    <div className="absolute top-full left-0 mt-1 w-56 rounded-xl shadow-lg z-20 p-2" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                      <p className="text-xs font-medium uppercase tracking-wide px-2 mb-1" style={{ color: 'var(--text-muted)' }}>Quick pick</p>
                      {PRESET_SITES.map(site => (
                        <button
                          key={site.value}
                          onClick={() => { setScrapeTarget(site.value); setCustomSite(''); setShowSitePicker(false); handleScrape(site.value); }}
                          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${scrapeTarget === site.value ? 'text-amber-400 font-medium' : 'text-white/70 hover:bg-white/5'}`}
                          style={scrapeTarget === site.value ? { background: 'rgba(245,158,11,0.1)' } : {}}
                        >
                          {site.label}
                          <span className="font-normal ml-1 text-xs" style={{ color: 'var(--text-muted)' }}>{site.value}</span>
                        </button>
                      ))}
                      <div className="mt-2 pt-2" style={{ borderTop: '1px solid var(--border)' }}>
                        <p className="text-xs font-medium uppercase tracking-wide px-2 mb-1" style={{ color: 'var(--text-muted)' }}>Custom domain</p>
                        <div className="flex gap-1 px-1">
                          <input
                            type="text"
                            value={customSite}
                            onChange={e => setCustomSite(e.target.value)}
                            placeholder="example.com"
                            className="glass-input flex-1 text-sm rounded-lg px-2 py-1.5 focus:outline-none focus:border-amber-500/50 text-white placeholder-white/30"
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
                            className="px-2 py-1.5 gradient-brand text-white rounded-lg text-sm transition-colors disabled:opacity-40"
                          >
                            Go
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <button
                  onClick={() => setShowAddUrl(true)}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors hover:bg-white/5 text-white/70"
                  style={{ border: '1px solid var(--border)' }}
                  title="Manually add a competitor URL you already know is this product"
                >
                  {Ico.link}
                  <span className="hidden sm:inline">Add URL</span>
                </button>

                <button onClick={startEditProduct} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors hover:bg-white/5 text-white/70" style={{ border: '1px solid var(--border)' }}>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                  Edit
                </button>
                <Link
                  href={`/products/${id}/report?print=1`}
                  target="_blank"
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors hover:bg-white/5 text-white/70"
                  style={{ border: '1px solid var(--border)' }}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                  <span className="hidden sm:inline">PDF</span>
                </Link>
                <button
                  onClick={async () => {
                    try {
                      const blob = await api.exportProductXLSX(id);
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `marketintel_${product.title.slice(0, 30).replace(/ /g, '_')}_${id}.xlsx`;
                      a.click();
                      URL.revokeObjectURL(url);
                    } catch (e) { addToast('Excel export failed: ' + e.message, 'error'); }
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors hover:bg-white/5 text-white/70"
                  style={{ border: '1px solid var(--border)' }}
                  title="Download as Excel (.xlsx)"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                  <span className="hidden sm:inline">Excel</span>
                </button>
                <button onClick={loadData} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors hover:bg-white/5 text-white/70" style={{ border: '1px solid var(--border)' }}>
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

        {/* Price timeline — competitors + my price on one chart */}
        <div className="rounded-2xl shadow-sm p-5" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="flex items-center justify-between mb-1">
            <p className="text-sm font-semibold text-white">Price Timeline</p>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{priceHistory.length} data point{priceHistory.length !== 1 ? 's' : ''}</span>
          </div>
          <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
            Competitor prices vs your price over time.{' '}
            {myPriceHistory.length > 0 && <span className="text-sky-400 font-medium">Diamond markers = your price changes.</span>}
          </p>
          {priceHistory.length === 0 && myPriceHistory.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-3" style={{ background: 'var(--bg-elevated)' }}>{Ico.avg}</div>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No price history yet</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Scrape competitors to start tracking</p>
            </div>
          ) : (
            <PriceTimelineChart
              priceHistory={priceHistory}
              myPriceHistory={myPriceHistory}
              myCurrentPrice={product?.my_price}
            />
          )}
        </div>

        {/* Competitor matches */}
        <div className="rounded-2xl shadow-sm p-5" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold text-white">Competitor Matches ({matches.length})</p>
            <button
              onClick={() => setShowAddUrl(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border-dashed text-xs font-medium transition-all hover:text-amber-400 hover:bg-white/5 text-white/50"
              style={{ border: '1px dashed var(--border)' }}
            >
              {Ico.link} Add from URL
            </button>
          </div>

          {matches.length === 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {/* Empty state */}
              <div className="sm:col-span-2 xl:col-span-2 flex flex-col items-center justify-center py-12 text-center">
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4" style={{ background: 'var(--bg-elevated)' }}>
                  {Ico.search}
                </div>
                <p className="text-sm font-medium text-white">No matches yet</p>
                <p className="text-sm mt-1 mb-4" style={{ color: 'var(--text-muted)' }}>Use the Scrape button above to search automatically, or paste a URL you already know.</p>
                <button
                  onClick={() => handleScrape()} disabled={scraping}
                  className="inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {Ico.search} Scrape {PRESET_SITES.find(s => s.value === scrapeTarget)?.label || scrapeTarget}
                </button>
              </div>
              {/* Add from URL card */}
              <AddUrlCard onClick={() => setShowAddUrl(true)} />
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {matches.map(m => (
                <MatchCard key={m.id} match={m} myPrice={product?.my_price} />
              ))}
              {/* Always show the "add from URL" card at the end */}
              <AddUrlCard onClick={() => setShowAddUrl(true)} />
            </div>
          )}
        </div>

        {/* My Price History timeline */}
        <div className="rounded-2xl shadow-sm p-5" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold text-white">My Price History</p>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{myPriceHistory.length} change{myPriceHistory.length !== 1 ? 's' : ''}</span>
          </div>

          {myPriceHistory.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No price changes recorded yet</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Every time you update your price, it's logged here automatically</p>
            </div>
          ) : (
            <div className="relative">
              {/* Vertical timeline line */}
              <div className="absolute left-3 top-2 bottom-2 w-px" style={{ background: 'var(--border)' }} />
              <div className="space-y-3">
                {[...myPriceHistory].reverse().map((entry, i) => {
                  const isUp = entry.change != null && entry.change > 0;
                  const isDown = entry.change != null && entry.change < 0;
                  return (
                    <div key={entry.id} className="flex items-start gap-3 pl-8 relative">
                      {/* Dot */}
                      <div className={`absolute left-1.5 top-1.5 w-3 h-3 rounded-full border-2 ${
                        isUp ? 'bg-emerald-400 border-emerald-400/30' : isDown ? 'bg-red-400 border-red-400/30' : 'border-white/10'
                      }`} style={!isUp && !isDown ? { background: 'var(--bg-elevated)' } : {}} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-bold text-white">${entry.new_price.toFixed(2)}</span>
                          {entry.old_price != null && (
                            <span className="text-xs line-through" style={{ color: 'var(--text-muted)' }}>${entry.old_price.toFixed(2)}</span>
                          )}
                          {entry.change_pct != null && (
                            <span className={`text-xs font-semibold ${isUp ? 'text-emerald-400' : isDown ? 'text-red-400' : 'text-white/50'}`}>
                              {entry.change_pct > 0 ? '+' : ''}{entry.change_pct.toFixed(1)}%
                            </span>
                          )}
                        </div>
                        <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                          {new Date(entry.changed_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                          {entry.note && <span className="ml-1.5 text-white/50">— {entry.note}</span>}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

      </div>
    </Layout>
  );
}
