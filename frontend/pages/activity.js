import { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import api from '../lib/api';

// ─── Icons ────────────────────────────────────────────────────────────────────
const Icon = {
  product:     <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>,
  price:       <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>,
  alert:       <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>,
  rule:        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" /></svg>,
  competitor:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  integration: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>,
  account:     <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>,
  team:        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>,
  search:      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>,
  filter:      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>,
  chevLeft:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>,
  chevRight:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>,
  check:       <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>,
  error:       <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>,
  clock:       <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  refresh:     <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
};

// ─── Config ───────────────────────────────────────────────────────────────────
const CATEGORIES = [
  { value: null,          label: 'All Activity' },
  { value: 'product',     label: 'Products' },
  { value: 'price',       label: 'Prices' },
  { value: 'alert',       label: 'Alerts' },
  { value: 'rule',        label: 'Rules' },
  { value: 'competitor',  label: 'Competitors' },
  { value: 'integration', label: 'Integrations' },
  { value: 'account',     label: 'Account' },
  { value: 'team',        label: 'Team' },
];

const TIME_RANGES = [
  { value: 1,    label: 'Today' },
  { value: 7,    label: '7 days' },
  { value: 30,   label: '30 days' },
  { value: null, label: 'All time' },
];

const CATEGORY_STYLE = {
  product:     { bg: 'rgba(37,99,235,0.15)',   border: 'rgba(37,99,235,0.3)',   text: '#60a5fa', dot: '#3b82f6' },
  price:       { bg: 'rgba(245,158,11,0.15)',  border: 'rgba(245,158,11,0.3)',  text: '#fbbf24', dot: '#f59e0b' },
  alert:       { bg: 'rgba(239,68,68,0.15)',   border: 'rgba(239,68,68,0.3)',   text: '#f87171', dot: '#ef4444' },
  rule:        { bg: 'rgba(139,92,246,0.15)',  border: 'rgba(139,92,246,0.3)',  text: '#a78bfa', dot: '#8b5cf6' },
  competitor:  { bg: 'rgba(20,184,166,0.15)',  border: 'rgba(20,184,166,0.3)',  text: '#2dd4bf', dot: '#14b8a6' },
  integration: { bg: 'rgba(16,185,129,0.15)',  border: 'rgba(16,185,129,0.3)',  text: '#34d399', dot: '#10b981' },
  account:     { bg: 'rgba(156,163,175,0.15)', border: 'rgba(156,163,175,0.3)', text: '#9ca3af', dot: '#6b7280' },
  team:        { bg: 'rgba(251,146,60,0.15)',  border: 'rgba(251,146,60,0.3)',  text: '#fb923c', dot: '#f97316' },
};

function fallbackStyle() {
  return { bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.1)', text: '#9ca3af', dot: '#6b7280' };
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  const now = new Date();
  const diff = (now - d) / 1000;
  if (diff < 60)   return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatDateTime(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function groupByDate(items) {
  const groups = {};
  items.forEach(item => {
    const d = item.created_at ? new Date(item.created_at) : null;
    const key = d ? d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }) : 'Unknown';
    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
  });
  return groups;
}

// ─── Sub-components ───────────────────────────────────────────────────────────
function CategoryBadge({ category }) {
  const s = CATEGORY_STYLE[category] || fallbackStyle();
  const icon = Icon[category] || Icon.account;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium capitalize"
      style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.text }}
    >
      {icon}
      {category}
    </span>
  );
}

function StatusBadge({ status }) {
  if (status === 'success') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-emerald-400"
        style={{ background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.25)' }}>
        {Icon.check} success
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-red-400"
      style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.25)' }}>
      {Icon.error} {status}
    </span>
  );
}

function ActivityRow({ item }) {
  const s = CATEGORY_STYLE[item.category] || fallbackStyle();
  const [expanded, setExpanded] = useState(false);
  const hasMeta = item.metadata && Object.keys(item.metadata).length > 0;

  return (
    <div className="flex gap-4 py-3 group">
      {/* Timeline dot */}
      <div className="flex flex-col items-center shrink-0 mt-1">
        <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
          style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.text }}>
          {Icon[item.category] || Icon.account}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-start gap-2 mb-1">
          <p className="text-sm text-white font-medium leading-snug flex-1 min-w-0">
            {item.description}
          </p>
          <StatusBadge status={item.status} />
        </div>

        <div className="flex flex-wrap items-center gap-2 mt-1">
          <CategoryBadge category={item.category} />

          <span className="text-xs font-mono px-1.5 py-0.5 rounded"
            style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>
            {item.action}
          </span>

          {item.entity_name && (
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              → <span className="text-white/70">{item.entity_name}</span>
            </span>
          )}

          <span className="text-xs ml-auto flex items-center gap-1" style={{ color: 'var(--text-muted)' }}
            title={formatDateTime(item.created_at)}>
            {Icon.clock}
            {formatTime(item.created_at)}
          </span>
        </div>

        {hasMeta && (
          <button
            onClick={() => setExpanded(v => !v)}
            className="text-xs mt-1.5 transition-colors"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => e.currentTarget.style.color = '#f59e0b'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
          >
            {expanded ? '▾ hide details' : '▸ show details'}
          </button>
        )}

        {expanded && hasMeta && (
          <pre className="mt-2 text-xs rounded-xl p-3 overflow-x-auto"
            style={{ background: 'rgba(0,0,0,0.3)', color: '#94a3b8', border: '1px solid rgba(255,255,255,0.07)' }}>
            {JSON.stringify(item.metadata, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}

function DateGroup({ label, items }) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-3 mb-3">
        <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
          {label}
        </span>
        <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{items.length} event{items.length !== 1 ? 's' : ''}</span>
      </div>

      <div className="rounded-2xl overflow-hidden divide-y" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', divideColor: 'var(--border)' }}>
        {items.map((item, i) => (
          <div key={item.id} className="px-4" style={{ borderTop: i > 0 ? '1px solid var(--border)' : 'none' }}>
            <ActivityRow item={item} />
          </div>
        ))}
      </div>
    </div>
  );
}

function EmptyState({ filtered }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
        style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)' }}>
        <svg className="w-8 h-8 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      </div>
      <p className="text-white font-semibold text-lg mb-1">No activity found</p>
      <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
        {filtered ? 'Try adjusting your filters or time range.' : 'Actions you take will appear here.'}
      </p>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function ActivityPage() {
  const [items, setItems]           = useState([]);
  const [total, setTotal]           = useState(0);
  const [pages, setPages]           = useState(1);
  const [page, setPage]             = useState(1);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(null);
  const [category, setCategory]     = useState(null);
  const [days, setDays]             = useState(7);
  const [search, setSearch]         = useState('');
  const [searchInput, setSearchInput] = useState('');

  const LIMIT = 50;

  const fetchActivity = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getActivity({
        page,
        limit: LIMIT,
        category: category || undefined,
        days: days || undefined,
      });
      setItems(data.items || []);
      setTotal(data.total || 0);
      setPages(data.pages || 1);
    } catch (e) {
      setError(e.message || 'Failed to load activity');
    } finally {
      setLoading(false);
    }
  }, [page, category, days]);

  useEffect(() => { fetchActivity(); }, [fetchActivity]);

  // Client-side search filter on description / action / entity_name
  const filtered = search
    ? items.filter(i =>
        i.description?.toLowerCase().includes(search) ||
        i.action?.toLowerCase().includes(search) ||
        i.entity_name?.toLowerCase().includes(search)
      )
    : items;

  const grouped = groupByDate(filtered);

  const isFiltered = !!category || !!days || !!search;

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Activity Log</h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
              A full audit trail of every action taken in your account.
            </p>
          </div>
          <button
            onClick={fetchActivity}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all"
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(245,158,11,0.4)'; e.currentTarget.style.color = '#f59e0b'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-muted)'; }}
          >
            <span className={loading ? 'animate-spin' : ''}>{Icon.refresh}</span>
            Refresh
          </button>
        </div>

        {/* Stats bar */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[
            { label: 'Total Events', value: total },
            { label: 'This Page',    value: items.length },
            { label: 'Page',         value: `${page} / ${pages}` },
          ].map(s => (
            <div key={s.label} className="rounded-2xl p-4 text-center"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <p className="text-xl font-bold text-white">{s.value}</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{s.label}</p>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="rounded-2xl p-4 mb-6 flex flex-col gap-4"
          style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>

          {/* Search */}
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }}>{Icon.search}</span>
            <input
              type="text"
              placeholder="Search actions, descriptions, entity names…"
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { setSearch(searchInput.toLowerCase()); setPage(1); } }}
              onBlur={() => { setSearch(searchInput.toLowerCase()); setPage(1); }}
              className="w-full pl-9 pr-4 py-2.5 rounded-xl text-sm bg-transparent text-white placeholder-zinc-500 outline-none"
              style={{ border: '1px solid var(--border)' }}
            />
          </div>

          {/* Category tabs */}
          <div className="flex flex-wrap gap-1.5">
            {CATEGORIES.map(c => {
              const active = category === c.value;
              const s = c.value ? (CATEGORY_STYLE[c.value] || fallbackStyle()) : null;
              return (
                <button
                  key={String(c.value)}
                  onClick={() => { setCategory(c.value); setPage(1); }}
                  className="px-3 py-1.5 rounded-xl text-xs font-medium transition-all"
                  style={active
                    ? { background: s ? s.bg : 'rgba(245,158,11,0.15)', border: `1px solid ${s ? s.border : 'rgba(245,158,11,0.4)'}`, color: s ? s.text : '#f59e0b' }
                    : { background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-muted)' }
                  }
                >
                  {c.label}
                </button>
              );
            })}
          </div>

          {/* Time range */}
          <div className="flex items-center gap-2">
            <span className="text-xs shrink-0" style={{ color: 'var(--text-muted)' }}>Time range:</span>
            <div className="flex gap-1.5 flex-wrap">
              {TIME_RANGES.map(t => {
                const active = days === t.value;
                return (
                  <button
                    key={String(t.value)}
                    onClick={() => { setDays(t.value); setPage(1); }}
                    className="px-3 py-1 rounded-xl text-xs font-medium transition-all"
                    style={active
                      ? { background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.4)', color: '#f59e0b' }
                      : { background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-muted)' }
                    }
                  >
                    {t.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Content */}
        {error ? (
          <div className="rounded-2xl p-6 text-center" style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
            <p className="text-red-400 font-medium">{error}</p>
            <button onClick={fetchActivity} className="mt-3 text-sm text-amber-400 hover:text-amber-300">Try again</button>
          </div>
        ) : loading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="rounded-2xl p-4 animate-pulse" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                <div className="flex gap-4">
                  <div className="w-8 h-8 rounded-xl shrink-0" style={{ background: 'rgba(255,255,255,0.07)' }} />
                  <div className="flex-1 space-y-2">
                    <div className="h-3 rounded-full w-3/4" style={{ background: 'rgba(255,255,255,0.07)' }} />
                    <div className="h-3 rounded-full w-1/2" style={{ background: 'rgba(255,255,255,0.05)' }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState filtered={isFiltered} />
        ) : (
          Object.entries(grouped).map(([label, groupItems]) => (
            <DateGroup key={label} label={label} items={groupItems} />
          ))
        )}

        {/* Pagination */}
        {!loading && pages > 1 && (
          <div className="flex items-center justify-center gap-3 mt-8">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="w-9 h-9 rounded-xl flex items-center justify-center transition-all disabled:opacity-30"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
            >
              {Icon.chevLeft}
            </button>

            <div className="flex gap-1">
              {[...Array(Math.min(pages, 7))].map((_, i) => {
                let p;
                if (pages <= 7) {
                  p = i + 1;
                } else if (page <= 4) {
                  p = i + 1;
                } else if (page >= pages - 3) {
                  p = pages - 6 + i;
                } else {
                  p = page - 3 + i;
                }
                const active = p === page;
                return (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className="w-9 h-9 rounded-xl text-sm font-medium transition-all"
                    style={active
                      ? { background: 'rgba(245,158,11,0.2)', border: '1px solid rgba(245,158,11,0.4)', color: '#f59e0b' }
                      : { background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }
                    }
                  >
                    {p}
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => setPage(p => Math.min(pages, p + 1))}
              disabled={page === pages}
              className="w-9 h-9 rounded-xl flex items-center justify-center transition-all disabled:opacity-30"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
            >
              {Icon.chevRight}
            </button>
          </div>
        )}
      </div>
    </Layout>
  );
}
