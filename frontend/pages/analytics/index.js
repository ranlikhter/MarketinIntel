import { useState, useEffect, useRef } from 'react';
import Layout from '../../components/Layout';
import api from '../../lib/api';

const Ico = {
  chart:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  trend:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>,
  down:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" /></svg>,
  box:     <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>,
};

const DAYS_OPTIONS = [
  { label: '7 days',  value: 7 },
  { label: '30 days', value: 30 },
  { label: '90 days', value: 90 },
];

function StatCard({ label, value, color, icon }) {
  const grad = {
    blue:    'stat-blue',
    emerald: 'stat-emerald',
    amber:   'stat-amber',
    violet:  'stat-violet',
  }[color];
  return (
    <div className={`${grad} rounded-2xl shadow-gradient p-5 flex items-center gap-4`}>
      <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 bg-white/20 text-white">{icon}</div>
      <div>
        <p className="text-2xl font-bold text-white leading-none">{value ?? '—'}</p>
        <p className="text-xs text-white/80 mt-1">{label}</p>
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
              borderColor: '#3b82f6',
              backgroundColor: 'rgba(59,130,246,0.08)',
              fill: true,
              tension: 0.4,
              pointRadius: 3,
              pointBackgroundColor: '#3b82f6',
            },
            {
              label: 'Forecast',
              data: forecasts,
              borderColor: '#8b5cf6',
              borderDash: [5, 5],
              fill: false,
              tension: 0.4,
              pointRadius: 2,
              pointBackgroundColor: '#8b5cf6',
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'top', labels: { font: { size: 12 }, boxWidth: 12, padding: 16 } },
            tooltip: {
              callbacks: {
                label: ctx => `$${ctx.parsed.y?.toFixed(2) ?? ''}`,
              },
            },
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { maxTicksLimit: 8, font: { size: 11 } },
            },
            y: {
              grid: { color: '#f3f4f6' },
              ticks: {
                font: { size: 11 },
                callback: v => `$${v.toFixed(0)}`,
              },
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
          <h1 className="text-xl font-bold text-slate-900">Analytics</h1>
          <p className="text-sm text-slate-500 mt-0.5">Price trendlines, forecasting and historical analysis</p>
        </div>

        {/* Product + Days selectors */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-48">
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Product</label>
            {loadingProducts ? (
              <div className="h-10 bg-white/40 rounded-xl animate-pulse" />
            ) : (
              <select
                value={selectedId}
                onChange={e => setSelectedId(e.target.value)}
                className="w-full px-3 py-2.5 glass-input rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
              >
                {products.length === 0 && <option value="">No products yet</option>}
                {products.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
              </select>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Period</label>
            <div className="flex gap-1">
              {DAYS_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setDays(opt.value)}
                  className={`px-3 py-2 rounded-xl text-xs font-medium transition-all ${days === opt.value ? 'gradient-brand text-white shadow-gradient' : 'glass border border-white/60 text-slate-600 hover:bg-white/40'}`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
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
        <div className="glass-card rounded-2xl shadow-glass overflow-hidden">
          <div className="px-5 py-4 border-b border-white/40">
            <h2 className="text-sm font-semibold text-slate-900">
              {selectedProduct ? selectedProduct.title : 'Price Trendline'}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Market price over time with linear regression forecast</p>
          </div>
          <div className="p-5">
            {!selectedId || loadingProducts ? (
              <div className="h-72 flex items-center justify-center text-sm text-slate-400">
                Select a product to view trendline
              </div>
            ) : loading ? (
              <div className="h-72 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent" />
              </div>
            ) : trendline?.data?.length > 0 ? (
              <div className="h-72">
                <TrendlineCanvas data={trendline.data} />
              </div>
            ) : (
              <div className="h-72 flex flex-col items-center justify-center text-center">
                <div className="w-12 h-12 bg-white/40 rounded-2xl flex items-center justify-center text-slate-300 mb-3">{Ico.chart}</div>
                <p className="text-sm font-medium text-slate-700">No price history yet</p>
                <p className="text-xs text-slate-400 mt-1">Scrape products to start building historical data</p>
              </div>
            )}
          </div>
        </div>

        {/* Forecast info */}
        {trendline?.forecast && (
          <div className="glass-card rounded-2xl shadow-glass overflow-hidden">
            <div className="px-5 py-4 border-b border-white/40">
              <h2 className="text-sm font-semibold text-slate-900">Forecast</h2>
              <p className="text-xs text-slate-500 mt-0.5">Linear regression projection with confidence interval</p>
            </div>
            <div className="p-5 grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-white/40 rounded-xl">
                <p className="text-xs text-slate-500 mb-1">7-Day Forecast</p>
                <p className="text-xl font-bold text-slate-900">
                  {trendline.forecast.price_7d != null ? `$${trendline.forecast.price_7d.toFixed(2)}` : '—'}
                </p>
              </div>
              <div className="text-center p-4 bg-white/40 rounded-xl">
                <p className="text-xs text-slate-500 mb-1">30-Day Forecast</p>
                <p className="text-xl font-bold text-slate-900">
                  {trendline.forecast.price_30d != null ? `$${trendline.forecast.price_30d.toFixed(2)}` : '—'}
                </p>
              </div>
              <div className="text-center p-4 bg-white/40 rounded-xl">
                <p className="text-xs text-slate-500 mb-1">Trend Direction</p>
                <p className={`text-xl font-bold ${trendline.forecast.slope > 0 ? 'text-red-600' : trendline.forecast.slope < 0 ? 'text-emerald-600' : 'text-slate-700'}`}>
                  {trendline.forecast.slope > 0 ? 'Rising' : trendline.forecast.slope < 0 ? 'Falling' : 'Stable'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Seasonal patterns */}
        {trendline?.seasonal_patterns && (
          <div className="glass-card rounded-2xl shadow-glass overflow-hidden">
            <div className="px-5 py-4 border-b border-white/40">
              <h2 className="text-sm font-semibold text-slate-900">Seasonal Patterns</h2>
              <p className="text-xs text-slate-500 mt-0.5">Day-of-week and monthly price patterns</p>
            </div>
            <div className="p-5">
              {trendline.seasonal_patterns.best_time_to_buy && (
                <div className="inline-flex items-center gap-2 px-3 py-2 bg-emerald-100/40 rounded-xl text-xs text-emerald-700 font-medium">
                  Best time to buy: {trendline.seasonal_patterns.best_time_to_buy}
                </div>
              )}
              {trendline.seasonal_patterns.day_of_week && (
                <div className="mt-4 grid grid-cols-7 gap-2">
                  {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((d, i) => {
                    const val = trendline.seasonal_patterns.day_of_week[i];
                    return (
                      <div key={d} className="text-center">
                        <p className="text-xs text-slate-500 mb-1">{d}</p>
                        <div className="h-16 bg-white/40 rounded-lg flex items-end overflow-hidden">
                          {val != null && (
                            <div
                              className="w-full bg-blue-400 rounded-lg"
                              style={{ height: `${Math.max(10, Math.min(100, val))}%` }}
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
