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
  price_leader:    { label: 'Price Leader',    bg: 'bg-red-50 text-red-700 border-red-200',     dot: 'bg-red-500',     desc: 'Always cheapest — aggressive pricing strategy' },
  premium_player:  { label: 'Premium Player',  bg: 'bg-violet-50 text-violet-700 border-violet-200', dot: 'bg-violet-500', desc: 'Commands higher prices — brand or quality positioning' },
  dynamic_pricer:  { label: 'Dynamic Pricer',  bg: 'bg-amber-50 text-amber-700 border-amber-200', dot: 'bg-amber-500', desc: 'Frequent algorithmic price changes — respond quickly' },
  market_follower: { label: 'Market Follower', bg: 'bg-blue-50 text-blue-700 border-blue-200',   dot: 'bg-blue-500',   desc: 'Matches average market pricing — predictable' },
  unknown:         { label: 'Unknown',         bg: 'bg-gray-100 text-gray-600 border-gray-200',  dot: 'bg-gray-400',   desc: 'Not enough data to determine strategy' },
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
        <span className="text-gray-500">{label}</span>
        <span className="font-semibold text-gray-700">{value}</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
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
      className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
      onClick={() => onSelect(competitor.competitor_name ?? competitor.name)}
    >
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-4">
          <div>
            <p className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
              {competitor.competitor_name ?? competitor.name}
            </p>
            {competitor.competitor_website && (
              <p className="text-xs text-gray-400 mt-0.5">{competitor.competitor_website}</p>
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
            <div className="bg-gray-50 rounded-xl p-3 text-center">
              <p className={`text-lg font-bold ${avgDiff < 0 ? 'text-red-600' : avgDiff > 0 ? 'text-emerald-600' : 'text-gray-700'}`}>
                {avgDiff > 0 ? '+' : ''}{avgDiff.toFixed(1)}%
              </p>
              <p className="text-xs text-gray-400 mt-0.5">vs market avg</p>
            </div>
          )}
          {stockRate != null && (
            <div className="bg-gray-50 rounded-xl p-3 text-center">
              <p className={`text-lg font-bold ${stockRate >= 80 ? 'text-emerald-600' : stockRate >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                {stockRate.toFixed(0)}%
              </p>
              <p className="text-xs text-gray-400 mt-0.5">in stock rate</p>
            </div>
          )}
        </div>

        {/* View profile link */}
        <div className="flex items-center justify-end text-xs text-blue-600 font-medium">
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
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-100 px-5 py-4 flex items-center justify-between">
          <h2 className="font-bold text-gray-900 text-lg">{name}</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
            {Ico.close}
          </button>
        </div>

        <div className="p-5">
          {loading && (
            <div className="space-y-4 animate-pulse">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-gray-100 rounded-xl" />
              ))}
            </div>
          )}
          {error && (
            <div className="bg-red-50 border border-red-100 rounded-xl p-4 text-sm text-red-700">
              {error}
            </div>
          )}
          {profile && !loading && (
            <div className="space-y-5">
              {/* Strategy + overview */}
              {profile.pricing_profile && (
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Cheaper than market', value: `${(profile.pricing_profile.cheaper_pct ?? 0).toFixed(0)}%`, color: 'text-emerald-600' },
                    { label: 'Similar to market', value: `${(profile.pricing_profile.similar_pct ?? 0).toFixed(0)}%`, color: 'text-blue-600' },
                    { label: 'More expensive', value: `${(profile.pricing_profile.expensive_pct ?? 0).toFixed(0)}%`, color: 'text-red-600' },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="bg-gray-50 rounded-xl p-3 text-center">
                      <p className={`text-xl font-bold ${color}`}>{value}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{label}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Availability */}
              {profile.availability && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Stock Availability</h3>
                  <div className="bg-gray-50 rounded-xl p-4 grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-gray-500">In Stock Rate</p>
                      <p className="font-bold text-gray-900">{(profile.availability.in_stock_rate ?? 0).toFixed(0)}%</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Total Products</p>
                      <p className="font-bold text-gray-900">{profile.total_products_tracked}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Recent activity */}
              {profile.recent_activity && profile.recent_activity.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Recent Price Activity (7d)</h3>
                  <div className="divide-y divide-gray-50">
                    {profile.recent_activity.slice(0, 8).map((act, i) => (
                      <div key={i} className="py-2.5 flex items-center justify-between text-xs">
                        <p className="text-gray-700 flex-1 min-w-0 truncate">{act.product_title}</p>
                        <span className={`ml-3 font-semibold shrink-0 ${
                          (act.change_pct ?? 0) < 0 ? 'text-red-600' : 'text-emerald-600'
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
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Sample Products</h3>
                  <div className="space-y-2">
                    {profile.product_sample.slice(0, 5).map((p, i) => (
                      <div key={i} className="flex items-center justify-between text-xs bg-gray-50 rounded-lg px-3 py-2">
                        <span className="text-gray-700 flex-1 min-w-0 truncate">{p.title}</span>
                        {p.price && <span className="font-semibold text-gray-900 ml-3 shrink-0">${p.price.toFixed(2)}</span>}
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
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${s.dot}`} />
        <h3 className="text-sm font-semibold text-gray-800">{s.label}</h3>
        <span className="text-xs text-gray-400">({competitors.length})</span>
      </div>
      <p className="text-xs text-gray-400 mb-3">{s.desc}</p>
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
            <h1 className="text-2xl font-bold text-gray-900">Competitor Intelligence</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Deep profiles of every competitor — pricing strategy, aggressiveness, availability
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={load}
              disabled={loading}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors shadow-sm disabled:opacity-50"
            >
              <span className={loading ? 'animate-spin' : ''}>{Ico.refresh}</span>
              Refresh
            </button>
            <Link
              href="/competitors"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors shadow-sm"
            >
              {Ico.users} Manage Competitors
            </Link>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-5 bg-red-50 border border-red-100 rounded-2xl p-4 text-sm text-red-700">
            {error}
            {error.includes('No competitors') || error.includes('not found') ? (
              <p className="mt-1 text-red-600">
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
              <div key={i} className="bg-white rounded-2xl border border-gray-100 h-52 animate-pulse" />
            ))}
          </div>
        )}

        {!loading && !error && (
          <>
            {/* Market Leader banner */}
            {comparison?.market_leader && (
              <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-2xl p-5 mb-6 flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center text-amber-600 shrink-0">
                  {Ico.fire}
                </div>
                <div>
                  <p className="text-sm font-semibold text-amber-900">
                    Market Leader: <span className="text-amber-700">{comparison.market_leader.name}</span>
                  </p>
                  <p className="text-xs text-amber-700 mt-0.5">
                    {comparison.market_leader.reason ?? 'Most competitive pricing across the most products'}
                  </p>
                </div>
              </div>
            )}

            {/* Summary row */}
            {comparison?.summary && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
                {[
                  { label: 'Most Aggressive', value: comparison.summary.most_aggressive, icon: Ico.fire, color: 'text-red-600', bg: 'bg-red-50' },
                  { label: 'Most Reliable Stock', value: comparison.summary.most_reliable, icon: Ico.shield, color: 'text-emerald-600', bg: 'bg-emerald-50' },
                  { label: 'Most Dynamic Pricing', value: comparison.summary.most_dynamic, icon: Ico.chart, color: 'text-blue-600', bg: 'bg-blue-50' },
                ].filter((s) => s.value).map(({ label, value, icon, color, bg }) => (
                  <div key={label} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${bg} ${color}`}>{icon}</div>
                    <div>
                      <p className="text-xs text-gray-500">{label}</p>
                      <p className="text-sm font-bold text-gray-900">{value}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Competitor cards */}
            {competitors.length > 0 ? (
              <>
                <h2 className="text-sm font-semibold text-gray-700 mb-3">
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
              <div className="text-center py-16 text-gray-400 bg-white rounded-2xl border border-gray-100 mb-8">
                <p className="text-lg font-medium">No competitor data yet</p>
                <p className="text-sm mt-1">Add competitors and run a scrape to see intelligence profiles</p>
                <Link href="/competitors/add" className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 transition-colors">
                  {Ico.users} Add First Competitor
                </Link>
              </div>
            )}

            {/* Strategy breakdown */}
            {Object.keys(byStrategy).length > 0 && (
              <>
                <h2 className="text-sm font-semibold text-gray-700 mb-3">Pricing Strategy Breakdown</h2>
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
