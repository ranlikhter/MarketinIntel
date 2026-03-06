import { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import api from '../lib/api';
import { LoadingSpinner } from './LoadingStates';

const DARK_GRID = 'rgba(255,255,255,0.04)';
const DARK_TICK = '#4b5563';
const DARK_TOOLTIP_BG = 'rgba(14,14,26,0.95)';
const DARK_TOOLTIP_BORDER = 'rgba(255,255,255,0.1)';

export default function TrendlineChart({ productId, defaultDays = 30 }) {
  const [loading, setLoading] = useState(true);
  const [trendData, setTrendData] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState(defaultDays);
  const [customRange, setCustomRange] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [compareMode, setCompareMode] = useState(false);
  const [comparisonData, setComparisonData] = useState(null);
  const [startDate2, setStartDate2] = useState('');
  const [endDate2, setEndDate2] = useState('');
  const [validationError, setValidationError] = useState('');

  useEffect(() => {
    loadTrendline();
  }, [productId, selectedPeriod]);

  const loadTrendline = async () => {
    setLoading(true);
    try {
      const data = await api.getProductTrendline(productId, selectedPeriod);
      setTrendData(data);
    } catch (error) {
      console.error('Failed to load trendline:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCustomDateRange = async () => {
    if (!startDate || !endDate) {
      setValidationError('Please select both start and end dates');
      return;
    }
    setValidationError('');

    setLoading(true);
    try {
      const data = await api.getProductTrendlineCustom(productId, startDate, endDate);
      setTrendData(data);
    } catch (error) {
      console.error('Failed to load custom range:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCompareRanges = async () => {
    if (!startDate || !endDate || !startDate2 || !endDate2) {
      setValidationError('Please select both start and end dates for both periods');
      return;
    }
    setValidationError('');

    setLoading(true);
    try {
      const data = await api.getDateRangeComparison(productId, startDate, endDate, startDate2, endDate2);
      setComparisonData(data);
    } catch (error) {
      console.error('Failed to load comparison:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!trendData || !trendData.success) {
    return (
      <div className="text-center py-8" style={{ color: 'var(--text-muted)' }}>
        <p>No trend data available</p>
      </div>
    );
  }

  const { daily_trend, insights } = trendData;

  const chartData = {
    labels: daily_trend.map(d => d.date),
    datasets: [
      {
        label: 'Average Price',
        data: daily_trend.map(d => d.avg_price),
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245,158,11,0.08)',
        borderWidth: 2,
        tension: 0.4,
        fill: true,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: '#f59e0b',
        pointBorderColor: 'rgba(255,255,255,0.2)',
        pointBorderWidth: 2
      },
      {
        label: 'Min Price',
        data: daily_trend.map(d => d.min_price),
        borderColor: '#34d399',
        backgroundColor: 'rgba(52,211,153,0.05)',
        borderWidth: 1.5,
        borderDash: [5, 5],
        tension: 0.4,
        fill: false,
        pointRadius: 0,
        pointHoverRadius: 4
      },
      {
        label: 'Max Price',
        data: daily_trend.map(d => d.max_price),
        borderColor: '#f87171',
        backgroundColor: 'rgba(248,113,113,0.05)',
        borderWidth: 1.5,
        borderDash: [5, 5],
        tension: 0.4,
        fill: false,
        pointRadius: 0,
        pointHoverRadius: 4
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 15,
          font: { size: 12, weight: '500' },
          color: '#9ca3af',
        }
      },
      tooltip: {
        backgroundColor: DARK_TOOLTIP_BG,
        borderColor: DARK_TOOLTIP_BORDER,
        borderWidth: 1,
        titleColor: '#f1f5f9',
        bodyColor: '#9ca3af',
        padding: 12,
        callbacks: {
          label: function(context) {
            return `${context.dataset.label}: $${context.parsed.y.toFixed(2)}`;
          },
          footer: function(tooltipItems) {
            if (tooltipItems.length > 0) {
              const dataPoint = daily_trend[tooltipItems[0].dataIndex];
              return `Competitors: ${dataPoint.competitor_count}`;
            }
            return '';
          }
        }
      }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          maxRotation: 45,
          minRotation: 45,
          font: { size: 10 },
          color: DARK_TICK,
        },
        border: { color: 'rgba(255,255,255,0.07)' },
      },
      y: {
        beginAtZero: false,
        grid: { color: DARK_GRID },
        border: { color: 'rgba(255,255,255,0.07)' },
        ticks: {
          callback: function(value) { return '$' + value.toFixed(0); },
          font: { size: 11 },
          color: DARK_TICK,
        }
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4 p-4 rounded-xl" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
        {/* Quick Period Selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>Period:</span>
          {[7, 14, 30, 60, 90].map(days => (
            <button
              key={days}
              onClick={() => {
                setSelectedPeriod(days);
                setCustomRange(false);
              }}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                selectedPeriod === days && !customRange
                  ? 'gradient-brand text-white shadow-gradient'
                  : 'text-white/50 hover:text-white hover:bg-white/5'
              }`}
              style={selectedPeriod !== days || customRange ? { border: '1px solid var(--border)' } : {}}
            >
              {days}d
            </button>
          ))}
        </div>

        <div className="h-6 w-px" style={{ background: 'var(--border)' }} />

        {/* Custom Date Range */}
        <button
          onClick={() => setCustomRange(!customRange)}
          className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${
            customRange
              ? 'gradient-brand text-white shadow-gradient'
              : 'text-white/50 hover:text-white hover:bg-white/5'
          }`}
          style={!customRange ? { border: '1px solid var(--border)' } : {}}
        >
          Custom Range
        </button>

        {customRange && (
          <>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-1.5 text-sm rounded-lg glass-input text-white focus:outline-none"
            />
            <span style={{ color: 'var(--text-muted)' }}>to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-1.5 text-sm rounded-lg glass-input text-white focus:outline-none"
            />
            <button
              onClick={handleCustomDateRange}
              className="px-4 py-1.5 gradient-brand text-white text-sm font-medium rounded-lg shadow-gradient transition-opacity hover:opacity-90"
            >
              Apply
            </button>
            {validationError && <span className="text-xs text-red-400">{validationError}</span>}
          </>
        )}

        {/* Compare Mode Toggle */}
        <div className="ml-auto flex items-center gap-2">
          <label className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>Compare Periods</label>
          <button
            onClick={() => {
              setCompareMode(!compareMode);
              if (!compareMode) {
                setCustomRange(true);
              }
            }}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              compareMode ? 'bg-amber-500' : 'bg-white/10'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                compareMode ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Comparison Date Ranges */}
      {compareMode && (
        <div className="p-4 rounded-xl" style={{ background: 'rgba(245,158,11,0.05)', border: '1px solid rgba(245,158,11,0.2)' }}>
          <h3 className="text-sm font-bold text-white mb-3">Compare Two Time Periods</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
              <label className="block text-xs font-semibold text-amber-400 mb-2">Period 1</label>
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-sm rounded-lg glass-input text-white focus:outline-none"
                />
                <span style={{ color: 'var(--text-muted)' }}>to</span>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-sm rounded-lg glass-input text-white focus:outline-none"
                />
              </div>
            </div>

            <div className="p-4 rounded-xl" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
              <label className="block text-xs font-semibold text-orange-400 mb-2">Period 2</label>
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={startDate2}
                  onChange={(e) => setStartDate2(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-sm rounded-lg glass-input text-white focus:outline-none"
                />
                <span style={{ color: 'var(--text-muted)' }}>to</span>
                <input
                  type="date"
                  value={endDate2}
                  onChange={(e) => setEndDate2(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-sm rounded-lg glass-input text-white focus:outline-none"
                />
              </div>
            </div>
          </div>

          <button
            onClick={handleCompareRanges}
            className="mt-4 w-full px-4 py-2 gradient-brand text-white text-sm font-medium rounded-xl shadow-gradient hover:opacity-90 transition-opacity"
          >
            Compare Periods
          </button>
        </div>
      )}

      {/* Insights Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <InsightCard
          label="Current"
          value={`$${insights.current_price}`}
          icon="💵"
        />
        <InsightCard
          label="Change"
          value={`${insights.price_change > 0 ? '+' : ''}${insights.price_change_pct.toFixed(1)}%`}
          valueColor={insights.price_change < 0 ? 'text-emerald-400' : 'text-red-400'}
          icon={insights.price_change < 0 ? '📉' : '📈'}
        />
        <InsightCard
          label="Average"
          value={`$${insights.avg_price_period}`}
          icon="📊"
        />
        <InsightCard
          label="Lowest"
          value={`$${insights.lowest_price}`}
          icon="⭐"
          valueColor="text-emerald-400"
        />
        <InsightCard
          label="Highest"
          value={`$${insights.highest_price}`}
          icon="🔺"
          valueColor="text-red-400"
        />
        <InsightCard
          label="Trend"
          value={insights.trend_direction}
          icon={
            insights.trend_direction === 'increasing' ? '⬆️' :
            insights.trend_direction === 'decreasing' ? '⬇️' : '➡️'
          }
          valueColor={
            insights.trend_direction === 'increasing' ? 'text-red-400' :
            insights.trend_direction === 'decreasing' ? 'text-emerald-400' : ''
          }
        />
      </div>

      {/* Chart */}
      <div className="rounded-2xl p-6" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-base font-semibold text-white">Price Trendline</h3>
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {trendData.date_range.start} to {trendData.date_range.end}
          </span>
        </div>
        <div className="h-96">
          <Line data={chartData} options={chartOptions} />
        </div>
      </div>

      {/* Recommendation */}
      <div className="p-4 rounded-xl" style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)' }}>
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-0.5">
            <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h4 className="font-semibold text-amber-400 mb-1 text-sm">Recommendation</h4>
            <p className="text-sm text-white/70">{insights.recommendation}</p>
          </div>
        </div>
      </div>

      {/* Detailed Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatDetail
          label="Price Range"
          value={`$${insights.price_range}`}
          description="Difference between highest and lowest"
        />
        <StatDetail
          label="Volatility"
          value={`${insights.volatility_pct.toFixed(1)}%`}
          description="Price stability measure"
        />
        <StatDetail
          label="Stability Score"
          value={`${insights.stability_score.toFixed(0)}/100`}
          description="How consistent prices are"
        />
      </div>

      {/* Comparison Results */}
      {compareMode && comparisonData && comparisonData.success && (
        <div className="rounded-2xl p-6" style={{ background: 'rgba(245,158,11,0.04)', border: '1px solid rgba(245,158,11,0.15)' }}>
          <h3 className="text-base font-semibold text-white mb-4">Period Comparison Results</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-xl p-5" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderLeftColor: '#f59e0b', borderLeftWidth: '3px' }}>
              <h4 className="font-bold text-amber-400 mb-3 text-sm">Period 1 ({comparisonData.period_1.date_range.start} to {comparisonData.period_1.date_range.end})</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Average Price:</span>
                  <span className="font-semibold text-white text-sm">${comparisonData.period_1.avg_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Lowest Price:</span>
                  <span className="font-semibold text-emerald-400 text-sm">${comparisonData.period_1.lowest_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Highest Price:</span>
                  <span className="font-semibold text-red-400 text-sm">${comparisonData.period_1.highest_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Volatility:</span>
                  <span className="font-semibold text-white text-sm">{comparisonData.period_1.volatility_pct.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Trend:</span>
                  <span className="font-semibold text-white text-sm capitalize">{comparisonData.period_1.trend_direction}</span>
                </div>
              </div>
            </div>

            <div className="rounded-xl p-5" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderLeftColor: '#f97316', borderLeftWidth: '3px' }}>
              <h4 className="font-bold text-orange-400 mb-3 text-sm">Period 2 ({comparisonData.period_2.date_range.start} to {comparisonData.period_2.date_range.end})</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Average Price:</span>
                  <span className="font-semibold text-white text-sm">${comparisonData.period_2.avg_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Lowest Price:</span>
                  <span className="font-semibold text-emerald-400 text-sm">${comparisonData.period_2.lowest_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Highest Price:</span>
                  <span className="font-semibold text-red-400 text-sm">${comparisonData.period_2.highest_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Volatility:</span>
                  <span className="font-semibold text-white text-sm">{comparisonData.period_2.volatility_pct.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Trend:</span>
                  <span className="font-semibold text-white text-sm capitalize">{comparisonData.period_2.trend_direction}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 rounded-xl p-5" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
            <h4 className="font-bold text-white mb-3 text-sm">Key Differences</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-3 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)' }}>
                <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Average Price Change</div>
                <div className={`text-2xl font-bold ${comparisonData.comparison.avg_price_diff > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                  {comparisonData.comparison.avg_price_diff > 0 ? '+' : ''}{comparisonData.comparison.avg_price_diff_pct.toFixed(1)}%
                </div>
                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>${Math.abs(comparisonData.comparison.avg_price_diff).toFixed(2)}</div>
              </div>
              <div className="text-center p-3 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)' }}>
                <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Volatility Change</div>
                <div className={`text-2xl font-bold ${comparisonData.comparison.volatility_diff > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                  {comparisonData.comparison.volatility_diff > 0 ? '+' : ''}{comparisonData.comparison.volatility_diff.toFixed(1)}%
                </div>
                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{comparisonData.comparison.volatility_diff > 0 ? 'More Volatile' : 'More Stable'}</div>
              </div>
              <div className="text-center p-3 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)' }}>
                <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Better Period</div>
                <div className="text-2xl font-bold text-amber-400">
                  Period {comparisonData.comparison.better_period}
                </div>
                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Lower Average Price</div>
              </div>
            </div>
            <div className="mt-4 p-3 rounded-lg text-sm" style={{ background: 'rgba(245,158,11,0.08)', color: 'rgba(255,255,255,0.7)' }}>
              <strong className="text-amber-400">Analysis:</strong> {comparisonData.comparison.summary}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function InsightCard({ label, value, icon, valueColor = 'text-white' }) {
  return (
    <div className="rounded-xl p-4" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>{label}</div>
      <div className={`text-lg font-bold ${valueColor}`}>{value}</div>
    </div>
  );
}

function StatDetail({ label, value, description }) {
  return (
    <div className="rounded-xl p-4" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
      <div className="text-sm mb-1" style={{ color: 'var(--text-muted)' }}>{label}</div>
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{description}</div>
    </div>
  );
}
