import { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import api from '../lib/api';
import { LoadingSpinner } from './LoadingStates';

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
      alert('Please select both start and end dates');
      return;
    }

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
      alert('Please select both start and end dates for both periods');
      return;
    }

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
      <div className="text-center py-8 text-gray-500">
        <p>No trend data available</p>
      </div>
    );
  }

  const { daily_trend, insights } = trendData;

  // Prepare chart data
  const chartData = {
    labels: daily_trend.map(d => d.date),
    datasets: [
      {
        label: 'Average Price',
        data: daily_trend.map(d => d.avg_price),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 3,
        tension: 0.4,
        fill: true,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: 'rgb(59, 130, 246)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      },
      {
        label: 'Min Price',
        data: daily_trend.map(d => d.min_price),
        borderColor: 'rgb(16, 185, 129)',
        backgroundColor: 'rgba(16, 185, 129, 0.05)',
        borderWidth: 2,
        borderDash: [5, 5],
        tension: 0.4,
        fill: false,
        pointRadius: 0,
        pointHoverRadius: 4
      },
      {
        label: 'Max Price',
        data: daily_trend.map(d => d.max_price),
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'rgba(239, 68, 68, 0.05)',
        borderWidth: 2,
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
          font: {
            size: 12,
            weight: '500'
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        padding: 12,
        titleFont: {
          size: 14,
          weight: 'bold'
        },
        bodyFont: {
          size: 13
        },
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
        grid: {
          display: false
        },
        ticks: {
          maxRotation: 45,
          minRotation: 45,
          font: {
            size: 10
          }
        }
      },
      y: {
        beginAtZero: false,
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        },
        ticks: {
          callback: function(value) {
            return '$' + value.toFixed(0);
          },
          font: {
            size: 11
          }
        }
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
        {/* Quick Period Selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Period:</span>
          {[7, 14, 30, 60, 90].map(days => (
            <button
              key={days}
              onClick={() => {
                setSelectedPeriod(days);
                setCustomRange(false);
              }}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                selectedPeriod === days && !customRange
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
              }`}
            >
              {days}d
            </button>
          ))}
        </div>

        <div className="h-6 w-px bg-gray-300" />

        {/* Custom Date Range */}
        <button
          onClick={() => setCustomRange(!customRange)}
          className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
            customRange
              ? 'bg-primary-600 text-white'
              : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
          }`}
        >
          Custom Range
        </button>

        {customRange && (
          <>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
            />
            <span className="text-gray-500">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
            />
            <button
              onClick={handleCustomDateRange}
              className="px-4 py-1.5 bg-primary-600 text-white text-sm font-medium rounded-md hover:bg-primary-700 transition-colors"
            >
              Apply
            </button>
          </>
        )}

        {/* Compare Mode Toggle */}
        <div className="ml-auto flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Compare Periods</label>
          <button
            onClick={() => {
              setCompareMode(!compareMode);
              if (!compareMode) {
                setCustomRange(true); // Enable custom range when compare mode is on
              }
            }}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              compareMode ? 'bg-primary-600' : 'bg-gray-300'
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
        <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200">
          <h3 className="text-sm font-bold text-gray-900 mb-3">Compare Two Time Periods</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Period 1 */}
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <label className="block text-xs font-semibold text-blue-600 mb-2">Period 1</label>
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
                <span className="text-gray-500">to</span>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            {/* Period 2 */}
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <label className="block text-xs font-semibold text-purple-600 mb-2">Period 2</label>
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={startDate2}
                  onChange={(e) => setStartDate2(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-purple-500 focus:border-purple-500"
                />
                <span className="text-gray-500">to</span>
                <input
                  type="date"
                  value={endDate2}
                  onChange={(e) => setEndDate2(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-purple-500 focus:border-purple-500"
                />
              </div>
            </div>
          </div>

          <button
            onClick={handleCompareRanges}
            className="mt-4 w-full px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white text-sm font-medium rounded-md hover:from-blue-700 hover:to-purple-700 transition-colors"
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
          valueColor={insights.price_change < 0 ? 'text-green-600' : 'text-red-600'}
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
          valueColor="text-green-600"
        />
        <InsightCard
          label="Highest"
          value={`$${insights.highest_price}`}
          icon="🔺"
          valueColor="text-red-600"
        />
        <InsightCard
          label="Trend"
          value={insights.trend_direction}
          icon={
            insights.trend_direction === 'increasing' ? '⬆️' :
            insights.trend_direction === 'decreasing' ? '⬇️' : '➡️'
          }
          valueColor={
            insights.trend_direction === 'increasing' ? 'text-red-600' :
            insights.trend_direction === 'decreasing' ? 'text-green-600' : 'text-gray-600'
          }
        />
      </div>

      {/* Chart */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-bold text-gray-900">Price Trendline</h3>
          <span className="text-sm text-gray-500">
            {trendData.date_range.start} to {trendData.date_range.end}
          </span>
        </div>
        <div className="h-96">
          <Line data={chartData} options={chartOptions} />
        </div>
      </div>

      {/* Recommendation */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0">
            <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h4 className="font-semibold text-blue-900 mb-1">Recommendation</h4>
            <p className="text-sm text-blue-800">{insights.recommendation}</p>
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
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">📊 Period Comparison Results</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Period 1 Stats */}
            <div className="bg-white rounded-lg shadow p-5 border-l-4 border-blue-500">
              <h4 className="font-bold text-blue-700 mb-3">Period 1 ({comparisonData.period_1.date_range.start} to {comparisonData.period_1.date_range.end})</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Average Price:</span>
                  <span className="font-semibold">${comparisonData.period_1.avg_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Lowest Price:</span>
                  <span className="font-semibold text-green-600">${comparisonData.period_1.lowest_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Highest Price:</span>
                  <span className="font-semibold text-red-600">${comparisonData.period_1.highest_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Volatility:</span>
                  <span className="font-semibold">{comparisonData.period_1.volatility_pct.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Trend:</span>
                  <span className="font-semibold capitalize">{comparisonData.period_1.trend_direction}</span>
                </div>
              </div>
            </div>

            {/* Period 2 Stats */}
            <div className="bg-white rounded-lg shadow p-5 border-l-4 border-purple-500">
              <h4 className="font-bold text-purple-700 mb-3">Period 2 ({comparisonData.period_2.date_range.start} to {comparisonData.period_2.date_range.end})</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Average Price:</span>
                  <span className="font-semibold">${comparisonData.period_2.avg_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Lowest Price:</span>
                  <span className="font-semibold text-green-600">${comparisonData.period_2.lowest_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Highest Price:</span>
                  <span className="font-semibold text-red-600">${comparisonData.period_2.highest_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Volatility:</span>
                  <span className="font-semibold">{comparisonData.period_2.volatility_pct.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Trend:</span>
                  <span className="font-semibold capitalize">{comparisonData.period_2.trend_direction}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Comparison Insights */}
          <div className="mt-6 bg-white rounded-lg shadow p-5">
            <h4 className="font-bold text-gray-900 mb-3">🔍 Key Differences</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-600 mb-1">Average Price Change</div>
                <div className={`text-2xl font-bold ${comparisonData.comparison.avg_price_diff > 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {comparisonData.comparison.avg_price_diff > 0 ? '+' : ''}{comparisonData.comparison.avg_price_diff_pct.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-500">${Math.abs(comparisonData.comparison.avg_price_diff).toFixed(2)}</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-600 mb-1">Volatility Change</div>
                <div className={`text-2xl font-bold ${comparisonData.comparison.volatility_diff > 0 ? 'text-yellow-600' : 'text-blue-600'}`}>
                  {comparisonData.comparison.volatility_diff > 0 ? '+' : ''}{comparisonData.comparison.volatility_diff.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-500">{comparisonData.comparison.volatility_diff > 0 ? 'More Volatile' : 'More Stable'}</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-600 mb-1">Better Period</div>
                <div className="text-2xl font-bold text-blue-600">
                  Period {comparisonData.comparison.better_period}
                </div>
                <div className="text-xs text-gray-500">Lower Average Price</div>
              </div>
            </div>
            <div className="mt-4 p-3 bg-blue-100 rounded text-sm text-blue-800">
              <strong>Analysis:</strong> {comparisonData.comparison.summary}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function InsightCard({ label, value, icon, valueColor = 'text-gray-900' }) {
  return (
    <div className="bg-white rounded-lg shadow p-4 border border-gray-100">
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-lg font-bold ${valueColor}`}>{value}</div>
    </div>
  );
}

function StatDetail({ label, value, description }) {
  return (
    <div className="bg-white rounded-lg shadow p-4 border border-gray-100">
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold text-gray-900 mb-1">{value}</div>
      <div className="text-xs text-gray-500">{description}</div>
    </div>
  );
}
