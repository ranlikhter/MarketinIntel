import { useEffect, useRef } from 'react';
import { Chart, RadarController, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend } from 'chart.js';

Chart.register(RadarController, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

export default function RadarWidget({ data }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !data?.axes) return;
    chartRef.current?.destroy();

    const datasets = (data.datasets || []).map(ds => ({
      label: ds.label,
      data: ds.data,
      borderColor: ds.color,
      backgroundColor: ds.color + '30',
      borderWidth: 2,
      pointRadius: 3,
      pointBackgroundColor: ds.color,
    }));

    chartRef.current = new Chart(canvasRef.current, {
      type: 'radar',
      data: { labels: data.axes, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            min: 0,
            max: 100,
            ticks: { stepSize: 25, font: { size: 9 } },
            grid: { color: '#e2e8f0' },
            pointLabels: { font: { size: 11 } },
          },
        },
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 10, padding: 10, font: { size: 11 } } },
          tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.r}/100` } },
        },
      },
    });
    return () => chartRef.current?.destroy();
  }, [data]);

  return <canvas ref={canvasRef} />;
}
