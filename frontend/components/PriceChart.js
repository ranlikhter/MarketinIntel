/**
 * Simple Price Chart Component
 *
 * For MVP, we'll use a simple SVG-based line chart.
 * Can be replaced with Chart.js or Recharts later for more features.
 */

export default function PriceChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-12" style={{ color: 'var(--text-muted)' }}>
        No price history data available yet
      </div>
    );
  }

  // Group data by competitor
  const competitors = {};
  data.forEach(item => {
    if (!competitors[item.competitor_name]) {
      competitors[item.competitor_name] = [];
    }
    competitors[item.competitor_name].push(item);
  });

  // Find min/max prices for scaling
  const allPrices = data.map(d => d.price);
  const minPrice = Math.min(...allPrices) * 0.95;
  const maxPrice = Math.max(...allPrices) * 1.05;

  // Chart dimensions
  const width = 800;
  const height = 400;
  const padding = {top: 20, right: 20, bottom: 40, left: 60};
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Colors for different competitors
  const colors = ['#f59e0b', '#10b981', '#3b82f6', '#ef4444', '#8b5cf6'];

  // Scale functions
  const scaleX = (index, total) => {
    return padding.left + (index / Math.max(total - 1, 1)) * chartWidth;
  };

  const scaleY = (price) => {
    return padding.top + chartHeight - ((price - minPrice) / (maxPrice - minPrice)) * chartHeight;
  };

  return (
    <div className="p-6" style={{ background: 'var(--bg-surface)' }}>
      <svg width={width} height={height} className="mx-auto">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = padding.top + chartHeight * (1 - ratio);
          const price = minPrice + (maxPrice - minPrice) * ratio;
          return (
            <g key={ratio}>
              <line
                x1={padding.left}
                y1={y}
                x2={width - padding.right}
                y2={y}
                stroke="rgba(255,255,255,0.07)"
                strokeWidth="1"
              />
              <text
                x={padding.left - 10}
                y={y + 4}
                textAnchor="end"
                className="text-xs"
                fill="rgba(255,255,255,0.4)"
              >
                ${price.toFixed(2)}
              </text>
            </g>
          );
        })}

        {/* X-axis */}
        <line
          x1={padding.left}
          y1={height - padding.bottom}
          x2={width - padding.right}
          y2={height - padding.bottom}
          stroke="rgba(255,255,255,0.2)"
          strokeWidth="2"
        />

        {/* Y-axis */}
        <line
          x1={padding.left}
          y1={padding.top}
          x2={padding.left}
          y2={height - padding.bottom}
          stroke="rgba(255,255,255,0.2)"
          strokeWidth="2"
        />

        {/* Plot lines for each competitor */}
        {Object.entries(competitors).map(([competitorName, points], index) => {
          const color = colors[index % colors.length];

          // Sort by timestamp
          const sortedPoints = [...points].sort((a, b) =>
            new Date(a.timestamp) - new Date(b.timestamp)
          );

          // Create path
          const pathData = sortedPoints.map((point, i) => {
            const x = scaleX(i, sortedPoints.length);
            const y = scaleY(point.price);
            return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
          }).join(' ');

          return (
            <g key={competitorName}>
              <path
                d={pathData}
                fill="none"
                stroke={color}
                strokeWidth="2"
              />
              {/* Data points */}
              {sortedPoints.map((point, i) => (
                <circle
                  key={i}
                  cx={scaleX(i, sortedPoints.length)}
                  cy={scaleY(point.price)}
                  r="4"
                  fill={color}
                >
                  <title>${point.price} on {new Date(point.timestamp).toLocaleDateString()}</title>
                </circle>
              ))}
            </g>
          );
        })}

        {/* Axis labels */}
        <text
          x={width / 2}
          y={height - 5}
          textAnchor="middle"
          className="text-sm font-medium"
          fill="rgba(255,255,255,0.5)"
        >
          Time
        </text>
        <text
          x={-(height / 2)}
          y={15}
          textAnchor="middle"
          transform={`rotate(-90 0 0)`}
          className="text-sm font-medium"
          fill="rgba(255,255,255,0.5)"
        >
          Price (USD)
        </text>
      </svg>

      {/* Legend */}
      <div className="flex justify-center space-x-4 mt-4">
        {Object.keys(competitors).map((name, index) => (
          <div key={name} className="flex items-center">
            <div
              className="w-4 h-4 rounded mr-2"
              style={{ backgroundColor: colors[index % colors.length] }}
            />
            <span className="text-sm text-white/70">{name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
