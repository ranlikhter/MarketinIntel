/**
 * Competitor Intelligence — Who are your rivals, really?
 *
 * This page surfaces the backend's competitor_intel_service data into a
 * rich, actionable UI. It answers questions like:
 *   • Which competitor is most aggressive (most price drops)?
 *   • Who is always the price leader vs the premium player?
 *   • Which competitor changed prices most in the last 7 days?
 *   • What's each competitor's pricing strategy?
 *
 * Data is pulled from:
 *   GET /api/competitor-intel/compare        → all-competitor overview
 *   GET /api/competitor-intel/strategies     → strategy categorisation
 *   GET /api/competitor-intel/competitors/:name  → drill-down profile
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import api from '../lib/api';

// ─── Icons ────────────────────────────────────────────────────────────────────
const Ico = {
  refresh: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  close: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>,
  arrow: <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>,
  fire: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" /></svg>,
  shield: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
  chart: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  users: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>,
  star: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>,
};

// ─── Strategy badge config ────────────────────────────────────────────────────
const STRATEGY = {
  price_leader:    { label: 'Price Leader',    bg: 'bg-red-900/40 text-red-300 border-red-800',         dot: 'bg-red-500',     desc: 'Always cheapest — aggressive pricing strategy' },
  premium_player:  { label: 'Premium Player',  bg: 'bg-violet-900/40 text-violet-300 border-violet-800', dot: 'bg-violet-500', desc: 'Commands higher prices — brand or quality positioning' },
  dynamic_pricer:  { label: 'Dynamic Pricer',  bg: 'bg-amber-900/40 text-amber-300 border-amber-800',   dot: 'bg-amber-500',  desc: 'Frequent algorithmic price changes — respond quickly' },
  market_follower: { label: 'Market Follower', bg: 'bg-blue-900/40 text-blue-300 border-blue-800',       dot: 'bg-blue-500',   desc: 'Matches average market pricing — predictable' },
  unknown:         { label: 'Unknown',         bg: 'bg-white/5 text-white/40 border-white/10',           dot: 'bg-white/30',   desc: 'Not enough data to determine strategy' },
};

function strategyFor(key) {
  return STRATEGY[key] || STRATEGY.unknown;
}

// ─── Metric bar ───────────────────────────────────────────────────────────────
function MetricBar({ label, value, max, color = 'bg-blue-500' }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span style={{ color: 'var(--text-muted)' }}>{label}</span>
        <span className="font-semibold text-white/70">{value}</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-elevated)' }}>
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ─── Competitor card ──────────────────────────────────────────────────────────
function CompetitorCard({ competitor, maxProducts, maxChanges, onSelect }) {
  const strategy = strategyFor(competitor.pricing_strategy || competitor.detected_strategy);
  const products = competitor.total_products_tracked ?? 0;
  const changes = competitor.price_change_frequency ?? competitor.recent_changes ?? 0;
  const avgDiff = competitor.avg_price_diff_pct ?? competitor.pricing_profile?.avg_price_diff_pct ?? null;
  const stockRate = competitor.stock_rate ?? competitor.availability?.in_stock_rate ?? null;

  return (
    <div
      className="glass-card rounded-2xl hover:shadow-glass-lg transition-shadow cursor-pointer group"
      onClick={() => onSelect(competitor.competitor_name ?? competitor.name)}
    >
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-4">
          <div>
            <p className="font-semibold text-white group-hover:text-amber-400 transition-colors">
              {competitor.competitor_name ?? competitor.name}
            </p>
            {competitor.competitor_website && (
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{competitor.competitor_website}</p>
            )}
          </div>
          <span className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium border ${strategy.bg}`}>
            {strategy.label}
          </span>
        </div>

        {/* Metrics */}
        <div className="space-y-2.5 mb-4">
          <MetricBar label="Products tracked" value={products} max={maxProducts} color="bg-blue-500" />
          <MetricBar label="Price changes (7d)" value={changes} max={Math.max(maxChanges, 1)} color="bg-amber-400" />
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          {avgDiff != null && (
            <div className="rounded-xl p-3 text-center" style={{ background: 'var(--bg-elevated)' }}>
              <p className={`text-lg font-bold ${avgDiff < 0 ? 'text-red-400' : avgDiff > 0 ? 'text-emerald-400' : 'text-white/60'}`}>
                {avgDiff > 0 ? '+' : ''}{avgDiff.toFixed(1)}%
              </p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>vs market avg</p>
            </div>
          )}
          {stockRate != null && (
            <div className="rounded-xl p-3 text-center" style={{ background: 'var(--bg-elevated)' }}>
              <p className={`text-lg font-bold ${stockRate >= 80 ? 'text-emerald-400' : stockRate >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                {stockRate.toFixed(0)}%
              </p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>in stock rate</p>
            </div>
          )}
        </div>

        {/* View profile link */}
        <div className="flex items-center justify-end text-xs text-amber-400 font-medium">
          View full profile {Ico.arrow}
        </div>
      </div>
    </div>
  );
}

// ─── Competitor detail panel ──────────────────────────────────────────────────
function CompetitorDetail({ name, onClose }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.getCompetitorProfile(name)
      .then(setProfile)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [name]);

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="glass-card rounded-2xl shadow-glass-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 glass px-5 py-4 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)' }}>
          <h2 className="font-bold text-white text-lg">{name}</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors">
            {Ico.close}
          </button>
        </div>

        <div className="p-5">
          {loading && (
            <div className="space-y-4 animate-pulse">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 rounded-xl" style={{ background: 'var(--bg-surface)' }} />
              ))}
            </div>
          )}
          {error && (
            <div className="rounded-xl p-4 text-sm text-red-400" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}>
              {error}
            </div>
          )}
          {profile && !loading && (
            <div className="space-y-5">
              {/* Strategy + overview */}
              {profile.pricing_profile && (
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Cheaper than market', value: `${(profile.pricing_profile.cheaper_pct ?? 0).toFixed(0)}%`, color: 'text-emerald-400' },
                    { label: 'Similar to market', value: `${(profile.pricing_profile.similar_pct ?? 0).toFixed(0)}%`, color: 'text-blue-400' },
                    { label: 'More expensive', value: `${(profile.pricing_profile.expensive_pct ?? 0).toFixed(0)}%`, color: 'text-red-400' },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="rounded-xl p-3 text-center" style={{ background: 'var(--bg-elevated)' }}>
                      <p className={`text-xl font-bold ${color}`}>{value}</p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{label}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Availability */}
              {profile.availability && (
                <div>
                  <h3 className="text-sm font-semibold text-white/70 mb-2">Stock Availability</h3>
                  <div className="rounded-xl p-4 grid grid-cols-2 gap-3 text-sm" style={{ background: 'var(--bg-elevated)' }}>
                    <div>
                      <p style={{ color: 'var(--text-muted)' }}>In Stock Rate</p>
                      <p className="font-bold text-white">{(profile.availability.in_stock_rate ?? 0).toFixed(0)}%</p>
                    </div>
                    <div>
                      <p style={{ color: 'var(--text-muted)' }}>Total Products</p>
                      <p className="font-bold text-white">{profile.total_products_tracked}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Recent activity */}
              {profile.recent_activity && profile.recent_activity.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-white/70 mb-2">Recent Price Activity (7d)</h3>
                  <div>
                    {profile.recent_activity.slice(0, 8).map((act, i) => (
                      <div key={i} className="py-2.5 flex items-center justify-between text-xs" style={{ borderBottom: '1px solid var(--border)' }}>
                        <p className="text-white/70 flex-1 min-w-0 truncate">{act.product_title}</p>
                        <span className={`ml-3 font-semibold shrink-0 ${
                          (act.change_pct ?? 0) < 0 ? 'text-red-400' : 'text-emerald-400'
                        }`}>
                          {(act.change_pct ?? 0) > 0 ? '+' : ''}{(act.change_pct ?? 0).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Product sample */}
              {profile.product_sample && profile.product_sample.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-white/70 mb-2">Sample Products</h3>
                  <div className="space-y-2">
                    {profile.product_sample.slice(0, 5).map((p, i) => (
                      <div key={i} className="flex items-center justify-between text-xs rounded-lg px-3 py-2" style={{ background: 'var(--bg-elevated)' }}>
                        <span className="text-white/70 flex-1 min-w-0 truncate">{p.title}</span>
                        {p.price && <span className="font-semibold text-white ml-3 shrink-0">${p.price.toFixed(2)}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Strategy tile ────────────────────────────────────────────────────────────
function StrategyTile({ strategyKey, competitors = [] }) {
  const s = strategyFor(strategyKey);
  if (competitors.length === 0) return null;
  return (
    <div className="glass-card rounded-2xl shadow-glass p-5">
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${s.dot}`} />
        <h3 className="text-sm font-semibold text-white/80">{s.label}</h3>
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>({competitors.length})</span>
      </div>
      <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>{s.desc}</p>
      <div className="flex flex-wrap gap-1.5">
        {competitors.map((c) => (
          <span key={c} className={`px-2 py-0.5 rounded-full text-xs border ${s.bg}`}>{c}</span>
        ))}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function CompetitorIntel() {
  const [comparison, setComparison] = useState(null);
  const [strategies, setStrategies] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null); // competitor name for drill-down panel

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [comp, strat] = await Promise.all([
        api.getCompetitorComparison(),
        api.getCompetitorStrategies(),
      ]);
      setComparison(comp);
      setStrategies(strat);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const competitors = comparison?.competitors ?? [];
  const maxProducts = Math.max(...competitors.map((c) => c.total_products_tracked ?? 0), 1);
  const maxChanges = Math.max(...competitors.map((c) => c.price_change_frequency ?? c.recent_changes ?? 0), 1);

  // Organise by strategy for the strategy grid
  const byStrategy = (strategies?.strategy_groups ?? strategies?.strategies ?? {});

  return (
    <Layout>
      <div className="p-4 lg:p-6">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Competitor Intelligence</h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
              Deep profiles of every competitor — pricing strategy, aggressiveness, availability
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={load}
              disabled={loading}
              className="inline-flex items-center gap-2 px-4 py-2 glass rounded-xl text-sm font-medium text-white/60 hover:bg-white/5 transition-colors shadow-glass disabled:opacity-50"
              style={{ border: '1px solid var(--border)' }}
            >
              <span className={loading ? 'animate-spin' : ''}>{Ico.refresh}</span>
              Refresh
            </button>
            <Link
              href="/competitors"
              className="inline-flex items-center gap-2 px-4 py-2 gradient-brand text-white text-sm font-semibold rounded-xl transition-opacity hover:opacity-90 shadow-gradient"
            >
              {Ico.users} Manage Competitors
            </Link>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-5 rounded-2xl p-4 text-sm text-red-400" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.15)' }}>
            {error}
            {error.includes('No competitors') || error.includes('not found') ? (
              <p className="mt-1 text-red-400">
                Add competitors and run scrapes first to see intelligence data.{' '}
                <Link href="/competitors/add" className="underline font-medium">Add a competitor →</Link>
              </p>
            ) : null}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="glass-card rounded-2xl h-52 animate-pulse" style={{ background: 'var(--bg-surface)' }} />
            ))}
          </div>
        )}

        {!loading && !error && (
          <>
            {/* Market Leader banner */}
            {comparison?.market_leader && (
              <div className="rounded-2xl p-5 mb-6 flex items-center gap-4" style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)' }}>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center text-amber-400 shrink-0" style={{ background: 'rgba(245,158,11,0.15)' }}>
                  {Ico.fire}
                </div>
                <div>
                  <p className="text-sm font-semibold text-amber-300">
                    Market Leader: <span className="text-amber-400">{comparison.market_leader.name}</span>
                  </p>
                  <p className="text-xs text-amber-400/70 mt-0.5">
                    {comparison.market_leader.reason ?? 'Most competitive pricing across the most products'}
                  </p>
                </div>
              </div>
            )}

            {/* Summary row */}
            {comparison?.summary && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
                {[
                  { label: 'Most Aggressive', value: comparison.summary.most_aggressive, icon: Ico.fire, color: 'text-red-400', bg: 'rgba(239,68,68,0.12)' },
                  { label: 'Most Reliable Stock', value: comparison.summary.most_reliable, icon: Ico.shield, color: 'text-emerald-400', bg: 'rgba(16,185,129,0.12)' },
                  { label: 'Most Dynamic Pricing', value: comparison.summary.most_dynamic, icon: Ico.chart, color: 'text-blue-400', bg: 'rgba(59,130,246,0.12)' },
                ].filter((s) => s.value).map(({ label, value, icon, color, bg }) => (
                  <div key={label} className="glass-card rounded-2xl shadow-glass p-4 flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${color}`} style={{ background: bg }}>{icon}</div>
                    <div>
                      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</p>
                      <p className="text-sm font-bold text-white">{value}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Competitor cards */}
            {competitors.length > 0 ? (
              <>
                <h2 className="text-sm font-semibold text-white/70 mb-3">
                  All Competitors ({competitors.length})
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
                  {competitors.map((c) => (
                    <CompetitorCard
                      key={c.competitor_name ?? c.name}
                      competitor={c}
                      maxProducts={maxProducts}
                      maxChanges={maxChanges}
                      onSelect={setSelected}
                    />
                  ))}
                </div>
              </>
            ) : (
              <div className="text-center py-16 glass-card rounded-2xl shadow-glass mb-8" style={{ color: 'var(--text-muted)' }}>
                <p className="text-lg font-medium text-white/50">No competitor data yet</p>
                <p className="text-sm mt-1">Add competitors and run a scrape to see intelligence profiles</p>
                <Link href="/competitors/add" className="inline-flex items-center gap-2 mt-4 px-4 py-2 gradient-brand text-white text-sm font-semibold rounded-xl transition-opacity hover:opacity-90 shadow-gradient">
                  {Ico.users} Add First Competitor
                </Link>
              </div>
            )}

            {/* Strategy breakdown */}
            {Object.keys(byStrategy).length > 0 && (
              <>
                <h2 className="text-sm font-semibold text-white/70 mb-3">Pricing Strategy Breakdown</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {Object.entries(byStrategy).map(([key, names]) => (
                    <StrategyTile key={key} strategyKey={key} competitors={Array.isArray(names) ? names : []} />
                  ))}
                </div>
              </>
            )}
          </>
        )}

        {/* Detail panel */}
        {selected && (
          <CompetitorDetail name={selected} onClose={() => setSelected(null)} />
        )}

      </div>
    </Layout>
  );
}
