import { useEffect, useRef } from 'react';
import { Chart, ScatterController, LinearScale, PointElement, Tooltip, Legend } from 'chart.js';

Chart.register(ScatterController, LinearScale, PointElement, Tooltip, Legend);

// Custom quadrant background plugin
const quadrantPlugin = {
  id: 'quadrant',
  beforeDraw(chart) {
    const { ctx, chartArea, scales } = chart;
    if (!chartArea) return;
    const { left, right, top, bottom } = chartArea;
    const xZero = scales.x.getPixelForValue(0);
    const yZero = scales.y.getPixelForValue(0);

    const quads = [
      { x: left,   y: top,    w: xZero - left,  h: yZero - top,    color: '#EFF6FF' }, // top-left: discounting & growing
      { x: xZero,  y: top,    w: right - xZero, h: yZero - top,    color: '#F0FDF4' }, // top-right: premium & growing
      { x: left,   y: yZero,  w: xZero - left,  h: bottom - yZero, color: '#FEF9C3' }, // bottom-left: losing ground
      { x: xZero,  y: yZero,  w: right - xZero, h: bottom - yZero, color: '#FFF1F2' }, // bottom-right: expensive & stagnant
    ];
    ctx.save();
    quads.forEach(q => { ctx.fillStyle = q.color; ctx.fillRect(q.x, q.y, q.w, q.h); });
    ctx.restore();
  },
};
Chart.register(quadrantPlugin);

export default function MomentumWidget({ data }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !data?.competitors) return;
    chartRef.current?.destroy();

    const datasets = (data.competitors || []).map(c => ({
      label: c.name,
      data: [{ x: c.x, y: c.y }],
      pointRadius: c.r,
      pointHoverRadius: c.r + 3,
      backgroundColor: c.color + 'cc',
      borderColor: c.color,
      borderWidth: 2,
    }));

    chartRef.current = new Chart(canvasRef.current, {
      type: 'scatter',
      data: { datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            title: { display: true, text: 'Price Change % (30d)', font: { size: 11 } },
            grid: { color: '#e2e8f0' },
            ticks: { callback: v => `${v > 0 ? '+' : ''}${v}%` },
          },
          y: {
            title: { display: true, text: 'Review Velocity (new reviews)', font: { size: 11 } },
            grid: { color: '#e2e8f0' },
          },
        },
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 10, padding: 10, font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const c = data.competitors.find(x => x.name === ctx.dataset.label);
                if (!c) return ctx.dataset.label;
                const qLabel = data.quadrant_labels?.[c.quadrant] || c.quadrant;
                return [
                  c.name,
                  `Price Δ: ${c.x > 0 ? '+' : ''}${c.x}%`,
                  `Review velocity: +${c.y}`,
                  c.bsr ? `BSR: #${c.bsr}` : '',
                  qLabel,
                ].filter(Boolean);
              },
            },
          },
        },
      },
    });
    return () => chartRef.current?.destroy();
  }, [data]);

  // Quadrant labels overlay
  const labels = data?.quadrant_labels;
  return (
    <div className="relative w-full h-full">
      <canvas ref={canvasRef} />
      {labels && (
        <div className="absolute inset-0 pointer-events-none" style={{ padding: '30px 10px 40px 50px' }}>
          <div className="relative w-full h-full">
            <span className="absolute top-1 left-1 text-xs text-blue-400 font-medium opacity-70">{labels.discounting_growing}</span>
            <span className="absolute top-1 right-1 text-xs text-green-500 font-medium opacity-70 text-right">{labels.premium_growing}</span>
            <span className="absolute bottom-1 left-1 text-xs text-yellow-500 font-medium opacity-70">{labels.losing_ground}</span>
            <span className="absolute bottom-1 right-1 text-xs text-red-400 font-medium opacity-70 text-right">{labels.expensive_stagnant}</span>
          </div>
        </div>
      )}
    </div>
  );
}
