import { useEffect, useRef } from 'react';
import { Chart, LineController, LinearScale, CategoryScale, PointElement, LineElement, Tooltip, Legend, Filler } from 'chart.js';

Chart.register(LineController, LinearScale, CategoryScale, PointElement, LineElement, Tooltip, Legend, Filler);

export default function PriceHistoryWidget({ data }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !data?.dates) return;
    chartRef.current?.destroy();

    const datasets = (data.datasets || []).map((ds, i) => ({
      label: ds.label,
      data: ds.data,
      borderColor: ds.color,
      backgroundColor: ds.color + '18',
      borderWidth: 2,
      pointRadius: 2,
      pointHoverRadius: 5,
      tension: 0.35,
      fill: i === 0 && data.datasets.length === 1,
      spanGaps: true,
    }));

    chartRef.current = new Chart(canvasRef.current, {
      type: 'line',
      data: { labels: data.dates, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: {
            ticks: { maxTicksLimit: 8, font: { size: 10 } },
            grid: { display: false },
          },
          y: {
            ticks: { callback: v => `$${v}`, font: { size: 10 } },
            grid: { color: '#f1f5f9' },
          },
        },
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12, font: { size: 11 } } },
          tooltip: {
            callbacks: { label: ctx => `${ctx.dataset.label}: $${ctx.parsed.y?.toFixed(2) ?? '—'}` },
          },
        },
      },
    });
    return () => chartRef.current?.destroy();
  }, [data]);

  return <canvas ref={canvasRef} />;
}
