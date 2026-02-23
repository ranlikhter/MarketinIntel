import { useState, useEffect, useRef } from 'react';
import Layout from '../../components/Layout';
import api from '../../lib/api';

const Ico = {
  chart:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  trend:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>,
  down:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" /></svg>,
  box:     <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>,
  refresh: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
};

const DAYS_OPTIONS = [
  { label: '7 days',  value: 7 },
  { label: '30 days', value: 30 },
  { label: '90 days', value: 90 },
];

function StatCard({ label, value, color, icon }) {
  const styles = {
    blue:    { bg: 'rgba(37,99,235,0.12)',  border: 'rgba(37,99,235,0.2)',   text: '#60a5fa' },
    emerald: { bg: 'rgba(5,150,105,0.12)',  border: 'rgba(5,150,105,0.2)',   text: '#34d399' },
    amber:   { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.2)',  text: '#fbbf24' },
    violet:  { bg: 'rgba(124,58,237,0.12)', border: 'rgba(124,58,237,0.2)',  text: '#a78bfa' },
  }[color] || { bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.1)', text: '#9ca3af' };

  return (
    <div className="rounded-2xl p-5 flex items-center gap-4"
      style={{ background: styles.bg, border: `1px solid ${styles.border}` }}>
      <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: 'rgba(0,0,0,0.2)', color: styles.text }}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-white leading-none">{value ?? '—'}</p>
        <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.5)' }}>{label}</p>
      </div>
    </div>
  );
}

function TrendlineCanvas({ data }) {
  const canvasRef = useRef(null);
  const chartRef  = useRef(null);

  useEffect(() => {
    if (!data || !canvasRef.current) return;

    const loadChart = async () => {
      const { Chart, registerables } = await import('chart.js');
      Chart.register(...registerables);

      if (chartRef.current) chartRef.current.destroy();

      const labels = data.map(d => d.date);
      const prices = data.map(d => d.price);
      const forecasts = data.map(d => d.forecast ?? null);

      chartRef.current = new Chart(canvasRef.current, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: 'Market Price',
              data: prices,
              borderColor: '#f59e0b',
              backgroundColor: 'rgba(245,158,11,0.07)',
              fill: true,
              tension: 0.4,
              pointRadius: 3,
              pointBackgroundColor: '#f59e0b',
              pointBorderColor: '#f59e0b',
            },
            {
              label: 'Forecast',
              data: forecasts,
              borderColor: '#f97316',
              borderDash: [5, 5],
              fill: false,
              tension: 0.4,
              pointRadius: 2,
              pointBackgroundColor: '#f97316',
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'top',
              labels: {
                font: { size: 12 },
                boxWidth: 12,
                padding: 16,
                color: '#9ca3af',
              },
            },
            tooltip: {
              backgroundColor: 'rgba(14,14,26,0.95)',
              borderColor: 'rgba(255,255,255,0.1)',
              borderWidth: 1,
              titleColor: '#f1f5f9',
              bodyColor: '#9ca3af',
              callbacks: {
                label: ctx => `$${ctx.parsed.y?.toFixed(2) ?? ''}`,
              },
            },
          },
          scales: {
            x: {
              grid: { color: 'rgba(255,255,255,0.04)', display: true },
              ticks: { maxTicksLimit: 8, font: { size: 11 }, color: '#4b5563' },
              border: { color: 'rgba(255,255,255,0.07)' },
            },
            y: {
              grid: { color: 'rgba(255,255,255,0.04)' },
              ticks: {
                font: { size: 11 },
                color: '#4b5563',
                callback: v => `$${v.toFixed(0)}`,
              },
              border: { color: 'rgba(255,255,255,0.07)' },
            },
          },
        },
      });
    };

    loadChart();
    return () => { if (chartRef.current) chartRef.current.destroy(); };
  }, [data]);

  return <canvas ref={canvasRef} />;
}

export default function AnalyticsPage() {
  const [products, setProducts] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [days, setDays] = useState(30);
  const [trendline, setTrendline] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingProducts, setLoadingProducts] = useState(true);

  useEffect(() => {
    api.getProducts()
      .then(data => {
        setProducts(data);
        if (data.length > 0) setSelectedId(String(data[0].id));
      })
      .catch(console.error)
      .finally(() => setLoadingProducts(false));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    loadTrendline();
  }, [selectedId, days]);

  const loadTrendline = async () => {
    setLoading(true);
    setTrendline(null);
    try {
      const data = await api.getProductTrendline(selectedId, days);
      setTrendline(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const stats = trendline?.statistics;
  const selectedProduct = products.find(p => String(p.id) === selectedId);

  return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">

        {/* Header */}
        <div>
          <h1 className="text-xl font-bold text-white">Analytics</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>Price trendlines, forecasting and historical analysis</p>
        </div>

        {/* Product + Days selectors */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-48">
            <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>Product</label>
            {loadingProducts ? (
              <div className="h-10 rounded-xl animate-pulse" style={{ background: 'var(--bg-surface)' }} />
            ) : (
              <select
                value={selectedId}
                onChange={e => setSelectedId(e.target.value)}
                className="w-full px-3 py-2.5 glass-input rounded-xl text-sm focus:outline-none"
              >
                {products.length === 0 && <option value="">No products yet</option>}
                {products.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
              </select>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>Period</label>
            <div className="flex gap-1">
              {DAYS_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setDays(opt.value)}
                  className={`px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                    days === opt.value
                      ? 'gradient-brand text-white shadow-gradient'
                      : 'text-white/50 hover:text-white hover:bg-white/5'
                  }`}
                  style={days !== opt.value ? { border: '1px solid var(--border)' } : {}}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-end pb-0.5">
            <button onClick={loadTrendline} disabled={loading || !selectedId}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 disabled:opacity-40 transition-colors"
              style={{ border: '1px solid rgba(245,158,11,0.2)' }}>
              <span className={loading ? 'animate-spin' : ''}>{Ico.refresh}</span>
              Refresh
            </button>
          </div>
        </div>

        {/* Stat cards */}
        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Min Price"  value={stats.min  != null ? `$${stats.min.toFixed(2)}`  : '—'} color="emerald" icon={Ico.down} />
            <StatCard label="Max Price"  value={stats.max  != null ? `$${stats.max.toFixed(2)}`  : '—'} color="amber"   icon={Ico.trend} />
            <StatCard label="Avg Price"  value={stats.mean != null ? `$${stats.mean.toFixed(2)}` : '—'} color="blue"    icon={Ico.chart} />
            <StatCard label="Std Dev"    value={stats.std  != null ? `$${stats.std.toFixed(2)}`  : '—'} color="violet"  icon={Ico.box} />
          </div>
        )}

        {/* Chart */}
        <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <h2 className="text-sm font-semibold text-white">
              {selectedProduct ? selectedProduct.title : 'Price Trendline'}
            </h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Market price over time with linear regression forecast</p>
          </div>
          <div className="p-5">
            {!selectedId || loadingProducts ? (
              <div className="h-72 flex items-center justify-center text-sm" style={{ color: 'var(--text-muted)' }}>
                Select a product to view trendline
              </div>
            ) : loading ? (
              <div className="h-72 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-amber-500 border-t-transparent" />
              </div>
            ) : trendline?.data?.length > 0 ? (
              <div className="h-72">
                <TrendlineCanvas data={trendline.data} />
              </div>
            ) : (
              <div className="h-72 flex flex-col items-center justify-center text-center">
                <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-3"
                  style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>
                  {Ico.chart}
                </div>
                <p className="text-sm font-medium text-white">No price history yet</p>
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Scrape products to start building historical data</p>
              </div>
            )}
          </div>
        </div>

        {/* Forecast info */}
        {trendline?.forecast && (
          <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
              <h2 className="text-sm font-semibold text-white">Forecast</h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Linear regression projection with confidence interval</p>
            </div>
            <div className="p-5 grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                { label: '7-Day Forecast', value: trendline.forecast.price_7d != null ? `$${trendline.forecast.price_7d.toFixed(2)}` : '—' },
                { label: '30-Day Forecast', value: trendline.forecast.price_30d != null ? `$${trendline.forecast.price_30d.toFixed(2)}` : '—' },
                {
                  label: 'Trend Direction',
                  value: trendline.forecast.slope > 0 ? 'Rising' : trendline.forecast.slope < 0 ? 'Falling' : 'Stable',
                  color: trendline.forecast.slope > 0 ? '#f87171' : trendline.forecast.slope < 0 ? '#34d399' : 'var(--text)',
                },
              ].map((item, i) => (
                <div key={i} className="text-center p-4 rounded-xl" style={{ background: 'var(--bg-elevated)' }}>
                  <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>{item.label}</p>
                  <p className="text-xl font-bold" style={{ color: item.color || 'white' }}>{item.value}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Seasonal patterns */}
        {trendline?.seasonal_patterns && (
          <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
              <h2 className="text-sm font-semibold text-white">Seasonal Patterns</h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Day-of-week and monthly price patterns</p>
            </div>
            <div className="p-5">
              {trendline.seasonal_patterns.best_time_to_buy && (
                <div className="inline-flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-emerald-400 font-medium"
                  style={{ background: 'rgba(5,150,105,0.12)', border: '1px solid rgba(5,150,105,0.2)' }}>
                  Best time to buy: {trendline.seasonal_patterns.best_time_to_buy}
                </div>
              )}
              {trendline.seasonal_patterns.day_of_week && (
                <div className="mt-4 grid grid-cols-7 gap-2">
                  {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((d, i) => {
                    const val = trendline.seasonal_patterns.day_of_week[i];
                    return (
                      <div key={d} className="text-center">
                        <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>{d}</p>
                        <div className="h-16 rounded-lg flex items-end overflow-hidden" style={{ background: 'var(--bg-elevated)' }}>
                          {val != null && (
                            <div
                              className="w-full rounded-lg"
                              style={{ height: `${Math.max(10, Math.min(100, val))}%`, background: 'rgba(245,158,11,0.5)' }}
                            />
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </Layout>
  );
}
