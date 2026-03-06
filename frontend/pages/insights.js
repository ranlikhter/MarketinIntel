import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../lib/api';

const Ico = {
  refresh: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  box:     <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>,
  users:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>,
  check:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  trend:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>,
  alert:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>,
  warn:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>,
  info:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  bolt:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  up:      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" /></svg>,
  down:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" /></svg>,
  fire:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" /><path strokeLinecap="round" strokeLinejoin="round" d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" /></svg>,
};

function StatCard({ label, value, sub, color, icon }) {
  const colorMap = {
    blue:    { bg: 'rgba(37,99,235,0.15)',   border: 'rgba(37,99,235,0.25)',   icon: 'rgba(37,99,235,0.3)' },
    violet:  { bg: 'rgba(124,58,237,0.15)',  border: 'rgba(124,58,237,0.25)',  icon: 'rgba(124,58,237,0.3)' },
    emerald: { bg: 'rgba(5,150,105,0.15)',   border: 'rgba(5,150,105,0.25)',   icon: 'rgba(5,150,105,0.3)' },
    amber:   { bg: 'rgba(245,158,11,0.15)',  border: 'rgba(245,158,11,0.25)',  icon: 'rgba(245,158,11,0.3)' },
  }[color] || { bg: 'var(--bg-surface)', border: 'var(--border)', icon: 'rgba(255,255,255,0.1)' };

  return (
    <div className="rounded-2xl p-5 flex items-center gap-4" style={{ background: colorMap.bg, border: `1px solid ${colorMap.border}` }}>
      <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-white" style={{ background: colorMap.icon }}>{icon}</div>
      <div>
        <p className="text-2xl font-bold text-white leading-none">{value ?? '—'}</p>
        <p className="text-xs text-white/80 mt-1">{label}</p>
        {sub && <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{sub}</p>}
      </div>
    </div>
  );
}

const SEVERITY = {
  high:   { bar: 'bg-red-500',   badge: { background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.2)' },   badgeText: 'text-red-400' },
  medium: { bar: 'bg-amber-400', badge: { background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.2)' }, badgeText: 'text-amber-400' },
  low:    { bar: 'bg-blue-400',  badge: { background: 'rgba(37,99,235,0.12)', border: '1px solid rgba(37,99,235,0.2)' },   badgeText: 'text-blue-400' },
};

function PriorityItem({ item }) {
  const s = SEVERITY[item.severity] || SEVERITY.low;
  return (
    <div className="flex gap-3">
      <div className={`w-1 rounded-full shrink-0 ${s.bar}`} />
      <div className="flex-1 min-w-0 py-0.5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold text-white">{item.title}</span>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.badgeText}`} style={s.badge}>{item.severity}</span>
          {item.count > 0 && (
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{item.count} product{item.count !== 1 ? 's' : ''}</span>
          )}
        </div>
        <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{item.description}</p>
        {item.action && (
          <p className="text-xs text-amber-400 mt-1 font-medium">→ {item.action}</p>
        )}
      </div>
    </div>
  );
}

export default function InsightsDashboard() {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => { fetchInsights(); }, []);

  const fetchInsights = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.request('/api/insights/dashboard');
      setInsights(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const km = insights?.key_metrics;

  if (loading) return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)' }} />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-48 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)' }} />)}
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
            <h1 className="text-xl font-bold text-white">Intelligence</h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>Actionable recommendations based on your competitive data</p>
          </div>
          <button
            onClick={fetchInsights}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors text-white hover:bg-white/5"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
          >
            {Ico.refresh} Refresh
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-2xl p-4 text-sm text-red-400" style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.2)' }}>
            Failed to load insights: {error}
          </div>
        )}

        {/* Stats */}
        {km && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Total Products"
              value={km.total_products}
              color="blue" icon={Ico.box}
            />
            <StatCard
              label="Competitors"
              value={km.total_competitors}
              sub={`${km.avg_competitors_per_product} avg per product`}
              color="violet" icon={Ico.users}
            />
            <StatCard
              label="You're Cheapest"
              value={km.competitive_position?.cheapest_pct != null ? `${km.competitive_position.cheapest_pct}%` : '—'}
              sub={`${km.competitive_position?.cheapest ?? 0} products`}
              color="emerald" icon={Ico.check}
            />
            <StatCard
              label="Price Changes (7d)"
              value={km.price_changes_last_week}
              sub={`${km.active_alerts} active alerts`}
              color="amber" icon={Ico.trend}
            />
          </div>
        )}

        {/* Today's Priorities */}
        {insights?.priorities?.length > 0 && (
          <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
              <h2 className="text-sm font-semibold text-white">Today's Priorities</h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Actions you should take right now</p>
            </div>
            <div className="p-5 space-y-4">
              {insights.priorities.map((p, i) => <PriorityItem key={i} item={p} />)}
            </div>
          </div>
        )}

        {/* Opportunities + Threats */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Opportunities */}
          {insights?.opportunities?.length > 0 && (
            <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <div className="px-5 py-4 flex items-center gap-2" style={{ borderBottom: '1px solid var(--border)' }}>
                <div className="w-7 h-7 rounded-lg flex items-center justify-center text-emerald-400" style={{ background: 'rgba(5,150,105,0.15)' }}>{Ico.up}</div>
                <div>
                  <h2 className="text-sm font-semibold text-white">Opportunities</h2>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Revenue growth potential</p>
                </div>
              </div>
              <div className="p-5 space-y-4">
                {insights.opportunities.map((opp, i) => (
                  <div key={i} className="flex gap-3">
                    <div className="w-1 bg-emerald-400 rounded-full shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-white">{opp.title}</p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{opp.description}</p>
                      {opp.potential_revenue != null && (
                        <p className="text-xs font-medium text-emerald-400 mt-1">
                          Potential: ${opp.potential_revenue.toFixed(2)}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Threats */}
          {insights?.threats?.length > 0 && (
            <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <div className="px-5 py-4 flex items-center gap-2" style={{ borderBottom: '1px solid var(--border)' }}>
                <div className="w-7 h-7 rounded-lg flex items-center justify-center text-red-400" style={{ background: 'rgba(239,68,68,0.12)' }}>{Ico.warn}</div>
                <div>
                  <h2 className="text-sm font-semibold text-white">Threats</h2>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Competitive risks to watch</p>
                </div>
              </div>
              <div className="p-5 space-y-4">
                {insights.threats.map((threat, i) => (
                  <div key={i} className="flex gap-3">
                    <div className="w-1 bg-red-400 rounded-full shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-semibold text-white">{threat.title}</p>
                        {threat.severity && (
                          <span className="px-2 py-0.5 rounded-full text-xs font-medium text-red-400" style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.2)' }}>
                            {threat.severity}
                          </span>
                        )}
                      </div>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{threat.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Trending Products */}
        {insights?.trending?.length > 0 && (
          <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <div className="px-5 py-4 flex items-center gap-2" style={{ borderBottom: '1px solid var(--border)' }}>
              <div className="w-7 h-7 rounded-lg flex items-center justify-center text-amber-400" style={{ background: 'rgba(245,158,11,0.15)' }}>{Ico.fire}</div>
              <div>
                <h2 className="text-sm font-semibold text-white">Trending Products</h2>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Products with high market activity</p>
              </div>
            </div>
            <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
              {insights.trending.map((product, i) => (
                <div key={i} className="px-5 py-3 flex items-center justify-between gap-3 hover:bg-white/5">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate">{product.product_title}</p>
                    <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>{product.reason}</p>
                  </div>
                  <span className="shrink-0 px-2.5 py-0.5 rounded-full text-xs font-medium text-amber-400" style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.2)' }}>
                    {product.change_count} changes
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && !insights?.priorities?.length && !insights?.opportunities?.length && !insights?.threats?.length && !insights?.trending?.length && (
          <div className="rounded-2xl p-16 text-center" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>
              {Ico.bolt}
            </div>
            <p className="text-sm font-medium text-white">No insights yet</p>
            <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Add products and competitors to start getting actionable recommendations</p>
          </div>
        )}

      </div>
    </Layout>
  );
}
