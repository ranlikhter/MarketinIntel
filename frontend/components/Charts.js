import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const DARK_GRID = 'rgba(255,255,255,0.04)';
const DARK_TICK = '#4b5563';
const DARK_TOOLTIP_BG = 'rgba(14,14,26,0.95)';
const DARK_TOOLTIP_BORDER = 'rgba(255,255,255,0.1)';

export function PriceHistoryChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 rounded-xl" style={{ background: 'var(--bg-elevated)' }}>
        <p style={{ color: 'var(--text-muted)' }}>No price history data available</p>
      </div>
    );
  }

  // Group data by competitor
  const competitorData = {};
  data.forEach(item => {
    const name = item.competitor_name || 'Unknown';
    if (!competitorData[name]) {
      competitorData[name] = [];
    }
    competitorData[name].push(item);
  });

  // Amber-forward dark theme color palette
  const colors = [
    { border: '#f59e0b', bg: 'rgba(245,158,11,0.08)' },
    { border: '#34d399', bg: 'rgba(52,211,153,0.08)' },
    { border: '#f97316', bg: 'rgba(249,115,22,0.08)' },
    { border: '#f87171', bg: 'rgba(248,113,113,0.08)' },
    { border: '#a78bfa', bg: 'rgba(167,139,250,0.08)' },
  ];

  const datasets = Object.entries(competitorData).map(([name, items], idx) => {
    const color = colors[idx % colors.length];
    return {
      label: name,
      data: items.map(item => ({
        x: new Date(item.timestamp).toLocaleDateString(),
        y: item.price
      })),
      borderColor: color.border,
      backgroundColor: color.bg,
      borderWidth: 2,
      tension: 0.4,
      fill: true,
      pointRadius: 4,
      pointHoverRadius: 6,
      pointBackgroundColor: color.border,
    };
  });

  const chartData = { datasets };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
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
          }
        }
      }
    },
    scales: {
      x: {
        type: 'category',
        grid: { display: false },
        ticks: { font: { size: 11 }, color: DARK_TICK },
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
    <div className="h-80">
      <Line data={chartData} options={options} />
    </div>
  );
}

export function CompetitorComparisonChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 rounded-xl" style={{ background: 'var(--bg-elevated)' }}>
        <p style={{ color: 'var(--text-muted)' }}>No competitor data available</p>
      </div>
    );
  }

  const chartData = {
    labels: data.map(item => item.competitor_name),
    datasets: [
      {
        label: 'Current Price',
        data: data.map(item => item.latest_price),
        backgroundColor: [
          'rgba(245,158,11,0.7)',
          'rgba(52,211,153,0.7)',
          'rgba(249,115,22,0.7)',
          'rgba(248,113,113,0.7)',
          'rgba(167,139,250,0.7)',
        ],
        borderColor: [
          '#f59e0b',
          '#34d399',
          '#f97316',
          '#f87171',
          '#a78bfa',
        ],
        borderWidth: 1,
        borderRadius: 6,
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: DARK_TOOLTIP_BG,
        borderColor: DARK_TOOLTIP_BORDER,
        borderWidth: 1,
        titleColor: '#f1f5f9',
        bodyColor: '#9ca3af',
        padding: 12,
        callbacks: {
          label: function(context) { return `Price: $${context.parsed.y.toFixed(2)}`; }
        }
      }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { font: { size: 11 }, color: DARK_TICK },
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
    <div className="h-80">
      <Bar data={chartData} options={options} />
    </div>
  );
}

export function TrendIndicator({ current, previous }) {
  if (!previous) return null;

  const change = (current - previous) / previous * 100;
  const isIncrease = current > previous;

  if (current === previous) return <span className="text-white/50 text-sm">0.0%</span>;

  return (
    <div className={`flex items-center gap-1 text-sm font-medium ${
      isIncrease ? 'text-red-400' : 'text-emerald-400'
    }`}>
      {isIncrease ? (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
        </svg>
      ) : (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      )}
      <span>{Math.abs(change).toFixed(1)}%</span>
    </div>
  );
}
