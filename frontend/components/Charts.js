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

/**
 * Unified price timeline — one line per competitor + a "My Price" step‑line.
 *
 * Props:
 *   priceHistory  – array from GET /products/:id/price-history
 *   myPriceHistory – array from GET /products/:id/my-price-history
 *   myCurrentPrice – product.my_price (used as fallback when history is empty)
 */
export function PriceTimelineChart({ priceHistory = [], myPriceHistory = [], myCurrentPrice }) {
  const hasCompetitor = priceHistory.length > 0;
  const hasMy = myPriceHistory.length > 0 || myCurrentPrice != null;

  if (!hasCompetitor && !hasMy) {
    return (
      <div className="flex items-center justify-center h-64 rounded-xl" style={{ background: 'var(--bg-elevated)' }}>
        <p style={{ color: 'var(--text-muted)' }}>No price data available</p>
      </div>
    );
  }

  // ── helpers ────────────────────────────────────────────────────────────────
  const toDateKey = (d) => {
    const dt = new Date(d);
    return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
  };
  const formatLabel = (key) => {
    const [y, m, d] = key.split('-');
    return `${m}/${d}`;
  };

  // ── 1. Group competitor data by name, keep last price per date ────────────
  const competitorMap = {};
  priceHistory.forEach((item) => {
    const name = item.competitor_name || 'Unknown';
    if (!competitorMap[name]) competitorMap[name] = {};
    const dk = toDateKey(item.timestamp);
    // Keep the latest reading per day
    competitorMap[name][dk] = item.price;
  });

  // ── 2. Build sorted my‑price change list ─────────────────────────────────
  const myChanges = [...myPriceHistory]
    .sort((a, b) => new Date(a.changed_at) - new Date(b.changed_at));
  const myChangeDates = new Set(myChanges.map((e) => toDateKey(e.changed_at)));

  // ── 3. Collect ALL unique date keys ───────────────────────────────────────
  const allDatesSet = new Set();
  priceHistory.forEach((item) => allDatesSet.add(toDateKey(item.timestamp)));
  myChanges.forEach((entry) => allDatesSet.add(toDateKey(entry.changed_at)));
  const allDates = [...allDatesSet].sort();

  // ── 4. Forward‑fill "My Price" across the timeline ────────────────────────
  const myPriceByDate = {};
  let carry = null;

  // If there are changes, initialise carry from the first entry's old_price
  if (myChanges.length > 0 && myChanges[0].old_price != null) {
    carry = myChanges[0].old_price;
  }

  // Index for walking through myChanges in order
  let changeIdx = 0;
  for (const dk of allDates) {
    // Apply any changes on this date (there could be multiple)
    while (changeIdx < myChanges.length && toDateKey(myChanges[changeIdx].changed_at) === dk) {
      carry = myChanges[changeIdx].new_price;
      changeIdx++;
    }
    if (carry != null) myPriceByDate[dk] = carry;
  }

  // If we have a current price but zero history, show a flat line
  if (Object.keys(myPriceByDate).length === 0 && myCurrentPrice != null && allDates.length > 0) {
    allDates.forEach((dk) => { myPriceByDate[dk] = myCurrentPrice; });
  }

  // ── 5. Build chart labels ─────────────────────────────────────────────────
  const labels = allDates.map(formatLabel);

  // ── 6. Competitor datasets ────────────────────────────────────────────────
  const palette = [
    { border: '#f59e0b', bg: 'rgba(245,158,11,0.08)' },
    { border: '#34d399', bg: 'rgba(52,211,153,0.08)' },
    { border: '#f97316', bg: 'rgba(249,115,22,0.08)' },
    { border: '#f87171', bg: 'rgba(248,113,113,0.08)' },
    { border: '#a78bfa', bg: 'rgba(167,139,250,0.08)' },
  ];

  const datasets = Object.entries(competitorMap).map(([name, byDate], idx) => {
    const color = palette[idx % palette.length];
    const dataArr = allDates.map((dk) => byDate[dk] ?? null);

    // Highlight days where the competitor's price changed vs the previous value
    let prev = null;
    const pointRadii = dataArr.map((v) => {
      if (v == null) { return 0; }
      const changed = prev != null && v !== prev;
      prev = v;
      return changed ? 5 : 2;
    });

    return {
      label: name,
      data: dataArr,
      borderColor: color.border,
      backgroundColor: color.bg,
      borderWidth: 2,
      tension: 0.35,
      fill: false,
      pointRadius: pointRadii,
      pointHoverRadius: 6,
      pointBackgroundColor: color.border,
      spanGaps: true,
    };
  });

  // ── 7. "My Price" step‑line ───────────────────────────────────────────────
  if (Object.keys(myPriceByDate).length > 0) {
    const myDataArr = allDates.map((dk) => myPriceByDate[dk] ?? null);
    datasets.unshift({
      label: 'My Price',
      data: myDataArr,
      borderColor: '#38bdf8',
      backgroundColor: 'rgba(56,189,248,0.06)',
      borderWidth: 2.5,
      borderDash: [6, 3],
      stepped: 'before',
      fill: true,
      pointRadius: allDates.map((dk) => (myChangeDates.has(dk) ? 7 : 0)),
      pointHoverRadius: 8,
      pointBackgroundColor: '#38bdf8',
      pointBorderColor: '#0e0e1a',
      pointBorderWidth: 2,
      pointStyle: allDates.map((dk) => (myChangeDates.has(dk) ? 'rectRot' : 'circle')),
      spanGaps: true,
      order: -1, // draw on top
    });
  }

  // ── 8. Options ────────────────────────────────────────────────────────────
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
        },
      },
      tooltip: {
        backgroundColor: DARK_TOOLTIP_BG,
        borderColor: DARK_TOOLTIP_BORDER,
        borderWidth: 1,
        titleColor: '#f1f5f9',
        bodyColor: '#9ca3af',
        padding: 12,
        callbacks: {
          label(ctx) {
            if (ctx.parsed.y == null) return null;
            const val = `$${ctx.parsed.y.toFixed(2)}`;
            // Show delta vs previous point for this series
            const arr = ctx.dataset.data;
            let prev = null;
            for (let i = ctx.dataIndex - 1; i >= 0; i--) {
              if (arr[i] != null) { prev = arr[i]; break; }
            }
            if (prev != null && prev !== ctx.parsed.y) {
              const delta = ctx.parsed.y - prev;
              const pct = ((delta / prev) * 100).toFixed(1);
              const sign = delta > 0 ? '+' : '';
              return `${ctx.dataset.label}: ${val}  (${sign}$${delta.toFixed(2)} / ${sign}${pct}%)`;
            }
            return `${ctx.dataset.label}: ${val}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { font: { size: 11 }, color: DARK_TICK, maxRotation: 45 },
        border: { color: 'rgba(255,255,255,0.07)' },
      },
      y: {
        beginAtZero: false,
        grid: { color: DARK_GRID },
        border: { color: 'rgba(255,255,255,0.07)' },
        ticks: {
          callback(value) { return '$' + value.toFixed(0); },
          font: { size: 11 },
          color: DARK_TICK,
        },
      },
    },
  };

  return (
    <div className="h-96">
      <Line data={{ labels, datasets }} options={options} />
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
