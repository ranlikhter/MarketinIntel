import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Chart as ChartJS,
  LineElement, PointElement, LinearScale, CategoryScale,
  BarElement, Filler, Tooltip, Legend,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import Layout from '../../components/Layout';
import api from '../../lib/api';

ChartJS.register(
  LineElement, PointElement, LinearScale, CategoryScale,
  BarElement, Filler, Tooltip, Legend,
);

// ─── Design tokens ────────────────────────────────────────────────────────────
const C = {
  amber:   '#f59e0b',
  blue:    '#3b82f6',
  emerald: '#10b981',
  red:     '#ef4444',
  violet:  '#8b5cf6',
  teal:    '#14b8a6',
  muted:   'rgba(255,255,255,0.35)',
  surface: 'rgba(255,255,255,0.04)',
  border:  'rgba(255,255,255,0.08)',
};

const COMPETITOR_PALETTE = [
  '#f59e0b','#3b82f6','#10b981','#8b5cf6','#ef4444',
  '#14b8a6','#fb923c','#a3e635','#e879f9','#67e8f9',
];

// ─── Icons ────────────────────────────────────────────────────────────────────
const Icon = {
  trend:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>,
  history:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  forecast: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  seasonal: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>,
  drops:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" /></svg>,
  up:       <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" /></svg>,
  down:     <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" /></svg>,
  minus:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M18 12H6" /></svg>,
  refresh:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  box:      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>,
  link:     <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>,
};

// ─── Shared chart defaults ────────────────────────────────────────────────────
const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(15,15,20,0.95)',
      borderColor: C.border,
      borderWidth: 1,
      titleColor: '#fff',
      bodyColor: 'rgba(255,255,255,0.7)',
      padding: 10,
      callbacks: {
        label: (ctx) => ` ${ctx.dataset.label}: $${Number(ctx.raw).toFixed(2)}`,
      },
    },
  },
  scales: {
    x: {
      grid:  { color: 'rgba(255,255,255,0.05)' },
      ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 11 }, maxTicksLimit: 10 },
    },
    y: {
      grid:  { color: 'rgba(255,255,255,0.05)' },
      ticks: {
        color: 'rgba(255,255,255,0.4)',
        font:  { size: 11 },
        callback: (v) => `$${v}`,
      },
    },
  },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
const fmt$  = (n) => n != null ? `$${Number(n).toFixed(2)}` : '—';
const fmtPct = (n) => n != null ? `${n > 0 ? '+' : ''}${Number(n).toFixed(1)}%` : '—';

function trendMeta(direction) {
  if (direction === 'increasing') return { icon: Icon.up,    color: '#ef4444', label: 'Rising',   bg: 'rgba(239,68,68,0.12)',   border: 'rgba(239,68,68,0.25)' };
  if (direction === 'decreasing') return { icon: Icon.down,  color: '#10b981', label: 'Falling',  bg: 'rgba(16,185,129,0.12)',  border: 'rgba(16,185,129,0.25)' };
  return                                  { icon: Icon.minus, color: '#f59e0b', label: 'Stable',   bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.25)' };
}

function volatilityMeta(v) {
  if (v === 'High')   return { color: '#ef4444', bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.25)' };
  if (v === 'Medium') return { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.25)' };
  return                     { color: '#10b981', bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.25)' };
}

function shortDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

// ─── Reusable card shell ──────────────────────────────────────────────────────
function Card({ title, action, children, className = '' }) {
  return (
    <div className={`rounded-2xl overflow-hidden ${className}`}
      style={{ background: C.surface, border: `1px solid ${C.border}` }}>
      {(title || action) && (
        <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: C.border }}>
          {title && <h3 className="text-sm font-semibold text-white">{title}</h3>}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

// ─── Stat card ────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, icon, color = 'amber' }) {
  const map = {
    amber:   { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.25)', icon: 'rgba(245,158,11,0.25)', text: C.amber  },
    blue:    { bg: 'rgba(59,130,246,0.12)', border: 'rgba(59,130,246,0.25)', icon: 'rgba(59,130,246,0.25)', text: C.blue   },
    emerald: { bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.25)', icon: 'rgba(16,185,129,0.25)', text: C.emerald },
    red:     { bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.25)',  icon: 'rgba(239,68,68,0.25)',  text: C.red    },
    violet:  { bg: 'rgba(139,92,246,0.12)', border: 'rgba(139,92,246,0.25)', icon: 'rgba(139,92,246,0.25)', text: C.violet },
  }[color];

  return (
    <div className="rounded-2xl p-5 flex items-center gap-4"
      style={{ background: map.bg, border: `1px solid ${map.border}` }}>
      <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: map.icon, color: map.text }}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-white leading-none">{value ?? '—'}</p>
        <p className="text-xs text-white/70 mt-1">{label}</p>
        {sub && <p className="text-xs mt-0.5" style={{ color: C.muted }}>{sub}</p>}
      </div>
    </div>
  );
}

// ─── Chip buttons ─────────────────────────────────────────────────────────────
function Chip({ active, onClick, children }) {
  return (
    <button onClick={onClick}
      className="px-3 py-1.5 rounded-xl text-xs font-medium transition-all"
      style={active
        ? { background: 'rgba(245,158,11,0.18)', border: '1px solid rgba(245,158,11,0.45)', color: C.amber }
        : { background: 'transparent', border: `1px solid ${C.border}`, color: C.muted }
      }>
      {children}
    </button>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────
function Skeleton({ h = 'h-48' }) {
  return (
    <div className={`${h} rounded-2xl animate-pulse`}
      style={{ background: 'rgba(255,255,255,0.05)', border: `1px solid ${C.border}` }} />
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────
function Empty({ msg = 'No data available for this product yet.' }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
        style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)' }}>
        <svg className="w-7 h-7 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      </div>
      <p className="text-white font-semibold mb-1">No data yet</p>
      <p className="text-sm max-w-xs" style={{ color: C.muted }}>{msg}</p>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB: Overview
// ══════════════════════════════════════════════════════════════════════════════
function TabOverview({ productId, summary }) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!productId) return;
    setLoading(true);
    api.getForecastHistory(productId, 30)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [productId]);

  if (loading) return <div className="grid grid-cols-2 lg:grid-cols-4 gap-4"><Skeleton /><Skeleton /><Skeleton /><Skeleton /></div>;
  if (!data || data.message) return <Empty msg={data?.message} />;

  const { statistics: s, trend, best_buying_times } = data;
  const tm = trendMeta(trend?.direction);
  const vm = volatilityMeta(s?.volatility);

  return (
    <div className="space-y-6">
      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Average Price"  value={fmt$(s?.avg_price)}    icon={Icon.box}      color="amber"   sub={`Median ${fmt$(s?.median_price)}`} />
        <StatCard label="Price Range"    value={fmt$(s?.price_range)}   icon={Icon.trend}    color="blue"    sub={`${fmt$(s?.min_price)} – ${fmt$(s?.max_price)}`} />
        <StatCard label="Market Trend"   value={tm.label}               icon={tm.icon}       color={trend?.direction === 'increasing' ? 'red' : trend?.direction === 'decreasing' ? 'emerald' : 'amber'} sub={fmtPct(trend?.change_pct) + ' vs period start'} />
        <StatCard label="Volatility"     value={s?.volatility ?? '—'}   icon={Icon.forecast} color={s?.volatility === 'High' ? 'red' : s?.volatility === 'Medium' ? 'amber' : 'emerald'} sub={`Std dev ${fmt$(s?.std_dev)}`} />
      </div>

      {/* Trend detail + best buying times */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="30-Day Trend">
          <div className="p-5 space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: tm.bg, border: `1px solid ${tm.border}`, color: tm.color }}>{tm.icon}</div>
              <div>
                <p className="text-white font-semibold">{tm.label} trend</p>
                <p className="text-xs" style={{ color: C.muted }}>
                  Week 1 avg {fmt$(trend?.first_week_avg)} → Week 4 avg {fmt$(trend?.last_week_avg)}
                </p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3 pt-2">
              {[
                { label: 'Period start', value: fmt$(trend?.first_week_avg) },
                { label: 'Change',       value: fmtPct(trend?.change_pct) },
                { label: 'Period end',   value: fmt$(trend?.last_week_avg) },
              ].map(({ label, value }) => (
                <div key={label} className="rounded-xl p-3 text-center" style={{ background: 'rgba(255,255,255,0.04)', border: `1px solid ${C.border}` }}>
                  <p className="text-white font-bold">{value}</p>
                  <p className="text-xs mt-0.5" style={{ color: C.muted }}>{label}</p>
                </div>
              ))}
            </div>
          </div>
        </Card>

        <Card title="Best Historical Buying Periods">
          <div className="p-5 space-y-3">
            {best_buying_times?.length > 0 ? best_buying_times.map((t, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold"
                  style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', color: C.amber }}>
                  {i + 1}
                </div>
                <div>
                  <p className="text-sm text-white font-medium">{t.period}</p>
                  <p className="text-xs mt-0.5" style={{ color: C.muted }}>{t.insight}</p>
                </div>
              </div>
            )) : (
              <p className="text-sm" style={{ color: C.muted }}>Not enough history to detect patterns yet.</p>
            )}
          </div>
        </Card>
      </div>

      {/* Market summary from global summary */}
      {summary && (
        <Card title="Portfolio Summary">
          <div className="grid grid-cols-3 divide-x p-0" style={{ '--divide-color': C.border }}>
            {[
              { label: 'Prices Rising',  value: summary.trend_distribution?.increasing ?? 0, color: '#ef4444' },
              { label: 'Prices Stable',  value: summary.trend_distribution?.stable     ?? 0, color: C.amber   },
              { label: 'Prices Falling', value: summary.trend_distribution?.decreasing ?? 0, color: '#10b981' },
            ].map(({ label, value, color }, i) => (
              <div key={label} className="p-5 text-center" style={{ borderLeft: i > 0 ? `1px solid ${C.border}` : 'none' }}>
                <p className="text-3xl font-bold" style={{ color }}>{value}</p>
                <p className="text-xs mt-1" style={{ color: C.muted }}>{label}</p>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB: Price History
// ══════════════════════════════════════════════════════════════════════════════
function TabHistory({ productId }) {
  const [days,    setDays]    = useState(90);
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!productId) return;
    setLoading(true);
    api.getForecastHistory(productId, days)
      .then(setData).catch(() => setData(null)).finally(() => setLoading(false));
  }, [productId, days]);

  // Build chart dataset from competitor histories
  const chartData = (() => {
    if (!data?.competitor_histories) return null;
    const entries = Object.entries(data.competitor_histories);
    if (!entries.length) return null;

    // Collect all timestamps
    const allTs = new Set();
    entries.forEach(([, pts]) => pts.forEach(p => allTs.add(p.timestamp)));
    const labels = [...allTs].sort().map(shortDate);

    const datasets = entries.map(([name, pts], i) => ({
      label: name,
      data: pts.map(p => p.price),
      borderColor: COMPETITOR_PALETTE[i % COMPETITOR_PALETTE.length],
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: pts.length > 30 ? 0 : 3,
      tension: 0.3,
    }));

    return { labels, datasets };
  })();

  const s = data?.statistics;

  return (
    <div className="space-y-5">
      {/* Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs" style={{ color: C.muted }}>Period:</span>
        {[30, 60, 90, 180].map(d => (
          <Chip key={d} active={days === d} onClick={() => setDays(d)}>{d} days</Chip>
        ))}
      </div>

      {loading ? <Skeleton h="h-64" /> : !chartData ? <Empty /> : (
        <>
          {/* Chart */}
          <Card title="Price History by Competitor">
            {/* Legend */}
            <div className="flex flex-wrap gap-3 px-5 pt-4">
              {chartData.datasets.map((ds, i) => (
                <span key={i} className="flex items-center gap-1.5 text-xs" style={{ color: 'rgba(255,255,255,0.7)' }}>
                  <span className="w-3 h-0.5 rounded-full inline-block" style={{ background: ds.borderColor }} />
                  {ds.label}
                </span>
              ))}
            </div>
            <div className="p-5" style={{ height: 300 }}>
              <Line data={chartData} options={CHART_DEFAULTS} />
            </div>
          </Card>

          {/* Stats table */}
          {s && (
            <Card title="Price Statistics">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-px" style={{ background: C.border }}>
                {[
                  { label: 'Minimum',  value: fmt$(s.min_price)    },
                  { label: 'Maximum',  value: fmt$(s.max_price)    },
                  { label: 'Average',  value: fmt$(s.avg_price)    },
                  { label: 'Median',   value: fmt$(s.median_price) },
                  { label: 'Std Dev',  value: fmt$(s.std_dev)      },
                  { label: 'Range',    value: fmt$(s.price_range)  },
                  { label: 'Volatility', value: s.volatility       },
                  { label: 'Data Points', value: data.total_data_points },
                ].map(({ label, value }) => (
                  <div key={label} className="p-4" style={{ background: 'var(--bg-page, #0d0d12)' }}>
                    <p className="text-lg font-bold text-white">{value ?? '—'}</p>
                    <p className="text-xs mt-0.5" style={{ color: C.muted }}>{label}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB: Forecast
// ══════════════════════════════════════════════════════════════════════════════
function TabForecast({ productId }) {
  const [horizon, setHorizon] = useState(30);
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!productId) return;
    setLoading(true);
    api.getForecast(productId, horizon)
      .then(setData).catch(() => setData(null)).finally(() => setLoading(false));
  }, [productId, horizon]);

  const chartData = (() => {
    if (!data?.forecast_points?.length) return null;
    return {
      labels:   data.forecast_points.map(p => `+${p.days_from_now}d`),
      datasets: [{
        label: 'Predicted Price',
        data:  data.forecast_points.map(p => p.predicted_price),
        borderColor: C.amber,
        backgroundColor: 'rgba(245,158,11,0.08)',
        borderWidth: 2,
        borderDash: [5, 4],
        pointRadius: 4,
        pointBackgroundColor: C.amber,
        fill: true,
        tension: 0.3,
      }],
    };
  })();

  const tm = data ? trendMeta(data.trend_direction) : null;
  const isRising = data?.price_change > 0;

  return (
    <div className="space-y-5">
      {/* Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs" style={{ color: C.muted }}>Horizon:</span>
        {[7, 14, 30, 60].map(d => (
          <Chip key={d} active={horizon === d} onClick={() => setHorizon(d)}>{d} days</Chip>
        ))}
      </div>

      {loading ? <><Skeleton h="h-32" /><Skeleton h="h-56" /></> : !data || data.message ? <Empty msg={data?.message} /> : (
        <>
          {/* Prediction headline */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Current → Predicted */}
            <div className="md:col-span-2 rounded-2xl p-6 flex items-center gap-6"
              style={{ background: isRising ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)', border: `1px solid ${isRising ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)'}` }}>
              <div className="flex-1">
                <p className="text-xs uppercase tracking-widest mb-1" style={{ color: C.muted }}>Current Price</p>
                <p className="text-4xl font-bold text-white">{fmt$(data.current_price)}</p>
              </div>
              <div className="flex flex-col items-center gap-1" style={{ color: isRising ? C.red : C.emerald }}>
                {isRising ? Icon.up : Icon.down}
                <span className="text-xl font-bold">{fmtPct(data.price_change_pct)}</span>
                <span className="text-xs" style={{ color: C.muted }}>in {horizon} days</span>
              </div>
              <div className="flex-1 text-right">
                <p className="text-xs uppercase tracking-widest mb-1" style={{ color: C.muted }}>Predicted</p>
                <p className="text-4xl font-bold" style={{ color: isRising ? C.red : C.emerald }}>
                  {fmt$(data.predicted_price)}
                </p>
              </div>
            </div>

            {/* Confidence */}
            <div className="rounded-2xl p-5 space-y-3" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
              <p className="text-xs font-semibold text-white uppercase tracking-widest">Confidence Range</p>
              <div className="space-y-2">
                <div>
                  <p className="text-xs mb-1" style={{ color: C.muted }}>Upper bound</p>
                  <p className="text-lg font-bold text-red-400">{fmt$(data.confidence?.upper_bound)}</p>
                </div>
                <div className="h-px" style={{ background: C.border }} />
                <div>
                  <p className="text-xs mb-1" style={{ color: C.muted }}>Lower bound</p>
                  <p className="text-lg font-bold text-emerald-400">{fmt$(data.confidence?.lower_bound)}</p>
                </div>
              </div>
              <p className="text-xs pt-1" style={{ color: C.muted }}>{data.confidence?.note}</p>
            </div>
          </div>

          {/* Forecast chart */}
          {chartData && (
            <Card title={`${horizon}-Day Price Forecast`}
              action={<span className="text-xs px-2 py-1 rounded-lg" style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)', color: C.amber }}>{data.methodology}</span>}>
              <div className="p-5" style={{ height: 280 }}>
                <Line data={chartData} options={{ ...CHART_DEFAULTS, plugins: { ...CHART_DEFAULTS.plugins, legend: { display: false } } }} />
              </div>
            </Card>
          )}

          {/* Meta */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Trend Direction', value: tm?.label ?? '—', color: tm?.color },
              { label: 'Price Change',    value: fmt$(data.price_change)                },
              { label: 'Data Points Used', value: data.data_points_used               },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-2xl p-4 text-center" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
                <p className="text-xl font-bold" style={{ color: color ?? '#fff' }}>{value}</p>
                <p className="text-xs mt-1" style={{ color: C.muted }}>{label}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB: Seasonal Patterns
// ══════════════════════════════════════════════════════════════════════════════
function TabSeasonal({ productId }) {
  const [months,  setMonths]  = useState(12);
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!productId) return;
    setLoading(true);
    api.getSeasonalPatterns(productId, months)
      .then(setData).catch(() => setData(null)).finally(() => setLoading(false));
  }, [productId, months]);

  const dayChart = (() => {
    if (!data?.day_of_week_patterns) return null;
    const entries = Object.entries(data.day_of_week_patterns);
    if (!entries.length) return null;
    const prices = entries.map(([, v]) => v.avg_price);
    const min = Math.min(...prices);
    return {
      labels:   entries.map(([day]) => day.slice(0, 3)),
      datasets: [{
        label: 'Avg Price',
        data:  prices,
        backgroundColor: prices.map(p => p === min ? 'rgba(16,185,129,0.6)' : 'rgba(245,158,11,0.35)'),
        borderColor:     prices.map(p => p === min ? '#10b981' : C.amber),
        borderWidth: 1,
        borderRadius: 6,
      }],
    };
  })();

  const monthChart = (() => {
    if (!data?.monthly_patterns) return null;
    const entries = Object.entries(data.monthly_patterns);
    if (!entries.length) return null;
    const prices = entries.map(([, v]) => v.avg_price);
    const min = Math.min(...prices);
    return {
      labels:   entries.map(([m]) => m.slice(0, 3)),
      datasets: [{
        label: 'Avg Price',
        data:  prices,
        backgroundColor: prices.map(p => p === min ? 'rgba(16,185,129,0.6)' : 'rgba(59,130,246,0.35)'),
        borderColor:     prices.map(p => p === min ? '#10b981' : C.blue),
        borderWidth: 1,
        borderRadius: 6,
      }],
    };
  })();

  const BAR_OPTS = {
    ...CHART_DEFAULTS,
    interaction: { mode: 'index', intersect: true },
    plugins: {
      ...CHART_DEFAULTS.plugins,
      tooltip: {
        ...CHART_DEFAULTS.plugins.tooltip,
        callbacks: { label: (ctx) => ` Avg: $${Number(ctx.raw).toFixed(2)}` },
      },
    },
  };

  const recs = data?.recommendations;

  return (
    <div className="space-y-5">
      {/* Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs" style={{ color: C.muted }}>Analysis period:</span>
        {[3, 6, 12].map(m => (
          <Chip key={m} active={months === m} onClick={() => setMonths(m)}>{m} months</Chip>
        ))}
      </div>

      {loading ? <><Skeleton h="h-56" /><Skeleton h="h-56" /></> : !data || data.message ? <Empty msg={data?.message} /> : (
        <>
          {/* Recommendation cards */}
          {recs && (recs.best_day_to_buy || recs.best_month_to_buy) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {recs.best_day_to_buy && (
                <div className="rounded-2xl p-5 flex items-center gap-4"
                  style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-emerald-400"
                    style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.3)' }}>
                    {Icon.seasonal}
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-widest" style={{ color: C.muted }}>Best Day to Buy</p>
                    <p className="text-xl font-bold text-white mt-0.5">{recs.best_day_to_buy}</p>
                    <p className="text-xs mt-0.5 text-emerald-400">Historically lowest average price</p>
                  </div>
                </div>
              )}
              {recs.best_month_to_buy && (
                <div className="rounded-2xl p-5 flex items-center gap-4"
                  style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)' }}>
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-blue-400"
                    style={{ background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.3)' }}>
                    {Icon.seasonal}
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-widest" style={{ color: C.muted }}>Best Month to Buy</p>
                    <p className="text-xl font-bold text-white mt-0.5">{recs.best_month_to_buy}</p>
                    <p className="text-xs mt-0.5 text-blue-400">Historically lowest average price</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Day of week chart */}
          {dayChart && (
            <Card title="Average Price by Day of Week"
              action={<span className="text-xs" style={{ color: C.muted }}>Green = cheapest day</span>}>
              <div className="p-5" style={{ height: 240 }}>
                <Bar data={dayChart} options={BAR_OPTS} />
              </div>
            </Card>
          )}

          {/* Monthly chart */}
          {monthChart && (
            <Card title="Average Price by Month"
              action={<span className="text-xs" style={{ color: C.muted }}>Green = cheapest month</span>}>
              <div className="p-5" style={{ height: 240 }}>
                <Bar data={monthChart} options={BAR_OPTS} />
              </div>
            </Card>
          )}

          {!dayChart && !monthChart && <Empty msg="Not enough seasonal data yet — keep monitoring products to build patterns." />}
        </>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB: Price Drops
// ══════════════════════════════════════════════════════════════════════════════
function TabDrops() {
  const [days,   setDays]   = useState(30);
  const [minPct, setMinPct] = useState(10);
  const [data,   setData]   = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getPriceDrops(days, minPct)
      .then(setData).catch(() => setData(null)).finally(() => setLoading(false));
  }, [days, minPct]);

  const drops = data?.significant_drops ?? [];

  return (
    <div className="space-y-5">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-xs" style={{ color: C.muted }}>Period:</span>
          {[7, 14, 30, 60, 90].map(d => (
            <Chip key={d} active={days === d} onClick={() => setDays(d)}>{d}d</Chip>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs" style={{ color: C.muted }}>Min drop:</span>
          {[5, 10, 15, 20, 30].map(p => (
            <Chip key={p} active={minPct === p} onClick={() => setMinPct(p)}>{p}%</Chip>
          ))}
        </div>
      </div>

      {/* Summary */}
      {data && (
        <div className="rounded-2xl p-4 flex items-center gap-3"
          style={{ background: 'rgba(239,68,68,0.07)', border: '1px solid rgba(239,68,68,0.18)' }}>
          <span className="text-red-400">{Icon.drops}</span>
          <p className="text-sm text-white">
            Found <span className="font-bold text-red-400">{data.total_drops_found}</span> competitor price drop{data.total_drops_found !== 1 ? 's' : ''} of {minPct}%+ in the last {days} days
          </p>
        </div>
      )}

      {loading ? (
        <div className="space-y-3">{[...Array(4)].map((_, i) => <Skeleton key={i} h="h-20" />)}</div>
      ) : drops.length === 0 ? (
        <Empty msg={`No competitor price drops of ${minPct}%+ found in the last ${days} days.`} />
      ) : (
        <div className="space-y-3">
          {drops.map((d, i) => {
            const isLarge = d.drop_pct >= 20;
            return (
              <div key={i} className="rounded-2xl p-4 flex items-center gap-4"
                style={{ background: C.surface, border: `1px solid ${C.border}` }}>
                {/* Drop % badge */}
                <div className="w-16 h-16 rounded-xl flex flex-col items-center justify-center shrink-0"
                  style={{ background: isLarge ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.1)', border: `1px solid ${isLarge ? 'rgba(239,68,68,0.3)' : 'rgba(245,158,11,0.25)'}` }}>
                  <span className="text-lg font-bold" style={{ color: isLarge ? C.red : C.amber }}>-{d.drop_pct}%</span>
                  <span className="text-xs" style={{ color: C.muted }}>drop</span>
                </div>

                {/* Product + competitor */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">{d.product_title}</p>
                  <p className="text-xs mt-0.5" style={{ color: C.muted }}>{d.competitor_name}</p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-xs line-through" style={{ color: C.muted }}>{fmt$(d.original_price)}</span>
                    <span className="text-xs text-emerald-400 font-semibold">{fmt$(d.current_price)}</span>
                    <span className="text-xs" style={{ color: C.muted }}>saved {fmt$(d.drop_amount)}</span>
                  </div>
                </div>

                {/* Link */}
                {d.competitor_url && (
                  <a href={d.competitor_url} target="_blank" rel="noopener noreferrer"
                    className="shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-colors"
                    style={{ background: 'rgba(255,255,255,0.05)', border: `1px solid ${C.border}`, color: C.muted }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(245,158,11,0.4)'; e.currentTarget.style.color = C.amber; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.color = C.muted; }}>
                    {Icon.link}
                  </a>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// Main Page
// ══════════════════════════════════════════════════════════════════════════════
const TABS = [
  { id: 'overview',  label: 'Overview',         icon: Icon.trend    },
  { id: 'history',   label: 'Price History',    icon: Icon.history  },
  { id: 'forecast',  label: 'Forecast',         icon: Icon.forecast },
  { id: 'seasonal',  label: 'Seasonal',         icon: Icon.seasonal },
  { id: 'drops',     label: 'Price Drops',      icon: Icon.drops    },
];

export default function ForecastingPage() {
  const [products,   setProducts]   = useState([]);
  const [productId,  setProductId]  = useState(null);
  const [tab,        setTab]        = useState('overview');
  const [summary,    setSummary]    = useState(null);
  const [loadingProd, setLoadingProd] = useState(true);

  // Load product list
  useEffect(() => {
    api.getProducts?.()
      .then(data => {
        const list = data?.products ?? data ?? [];
        setProducts(list);
        if (list.length > 0) setProductId(list[0].id);
      })
      .catch(() => {})
      .finally(() => setLoadingProd(false));
  }, []);

  // Load global summary once
  useEffect(() => {
    api.getForecastSummary()
      .then(setSummary)
      .catch(() => {});
  }, []);

  const selectedProduct = products.find(p => p.id === productId);

  return (
    <Layout>
      <div className="max-w-5xl mx-auto px-4 py-8">

        {/* ── Header ───────────────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Price Forecasting</h1>
            <p className="text-sm mt-1" style={{ color: C.muted }}>
              Historical analysis, trend detection, and price predictions for your products.
            </p>
          </div>

          {/* Product selector */}
          <div className="shrink-0">
            {loadingProd ? (
              <div className="w-56 h-10 rounded-xl animate-pulse" style={{ background: C.surface, border: `1px solid ${C.border}` }} />
            ) : products.length === 0 ? (
              <span className="text-sm" style={{ color: C.muted }}>No products tracked yet</span>
            ) : (
              <select
                value={productId ?? ''}
                onChange={e => setProductId(Number(e.target.value))}
                className="w-56 px-3 py-2 rounded-xl text-sm text-white appearance-none outline-none"
                style={{ background: C.surface, border: `1px solid ${C.border}` }}>
                {products.map(p => (
                  <option key={p.id} value={p.id}>{p.title?.slice(0, 35) ?? `Product #${p.id}`}</option>
                ))}
              </select>
            )}
          </div>
        </div>

        {/* ── Selected product banner ───────────────────────────────────── */}
        {selectedProduct && (
          <div className="flex items-center gap-3 rounded-2xl px-5 py-3 mb-6"
            style={{ background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.18)' }}>
            <span className="text-amber-500">{Icon.box}</span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white truncate">{selectedProduct.title}</p>
              {selectedProduct.sku && (
                <p className="text-xs" style={{ color: C.muted }}>SKU: {selectedProduct.sku}</p>
              )}
            </div>
            {selectedProduct.my_price != null && (
              <span className="ml-auto text-sm font-bold text-amber-400 shrink-0">
                My price: {fmt$(selectedProduct.my_price)}
              </span>
            )}
          </div>
        )}

        {/* ── Tab bar ──────────────────────────────────────────────────── */}
        <div className="flex gap-1 p-1 rounded-2xl mb-6 overflow-x-auto"
          style={{ background: C.surface, border: `1px solid ${C.border}` }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all flex-1 justify-center"
              style={tab === t.id
                ? { background: 'rgba(245,158,11,0.18)', border: '1px solid rgba(245,158,11,0.35)', color: C.amber }
                : { background: 'transparent', border: '1px solid transparent', color: C.muted }
              }>
              {t.icon}
              <span className="hidden sm:inline">{t.label}</span>
            </button>
          ))}
        </div>

        {/* ── Tab content ───────────────────────────────────────────────── */}
        {!productId && tab !== 'drops' ? (
          <Empty msg="Select a product above to start analysing." />
        ) : (
          <>
            {tab === 'overview'  && <TabOverview  productId={productId} summary={summary} />}
            {tab === 'history'   && <TabHistory   productId={productId} />}
            {tab === 'forecast'  && <TabForecast  productId={productId} />}
            {tab === 'seasonal'  && <TabSeasonal  productId={productId} />}
            {tab === 'drops'     && <TabDrops />}
          </>
        )}
      </div>
    </Layout>
  );
}
