import { useEffect, useRef } from 'react';
import { Chart, BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend } from 'chart.js';

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

export default function BarChartWidget({ data }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !data?.bars) return;
    chartRef.current?.destroy();

    const unit = data.unit || '$';
    chartRef.current = new Chart(canvasRef.current, {
      type: 'bar',
      data: {
        labels: data.bars.map(b => b.label),
        datasets: [{
          label: data.metric || 'Price',
          data: data.bars.map(b => b.value),
          backgroundColor: data.bars.map(b => b.color + 'cc'),
          borderColor: data.bars.map(b => b.color),
          borderWidth: 2,
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        scales: {
          x: {
            ticks: { callback: v => `${unit}${v}`, font: { size: 10 } },
            grid: { color: '#f1f5f9' },
          },
          y: { ticks: { font: { size: 11 } }, grid: { display: false } },
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => ` ${unit}${ctx.parsed.x?.toFixed(2)}` } },
        },
      },
    });
    return () => chartRef.current?.destroy();
  }, [data]);

  return <canvas ref={canvasRef} />;
}
