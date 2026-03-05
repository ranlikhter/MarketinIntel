import { useEffect, useRef } from 'react';
import { Chart, DoughnutController, ArcElement, Tooltip, Legend } from 'chart.js';

Chart.register(DoughnutController, ArcElement, Tooltip, Legend);

export default function PieChartWidget({ data }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !data?.slices) return;
    chartRef.current?.destroy();

    chartRef.current = new Chart(canvasRef.current, {
      type: 'doughnut',
      data: {
        labels: data.slices.map(s => s.label),
        datasets: [{
          data: data.slices.map(s => s.value),
          backgroundColor: data.slices.map(s => s.color + 'dd'),
          borderColor: data.slices.map(s => s.color),
          borderWidth: 2,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '60%',
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 10, padding: 10, font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: ctx => {
                const pct = ((ctx.parsed / (data.total || 1)) * 100).toFixed(1);
                return ` ${ctx.label}: ${ctx.parsed} (${pct}%)`;
              },
            },
          },
        },
      },
    });
    return () => chartRef.current?.destroy();
  }, [data]);

  return (
    <div className="flex flex-col h-full">
      {data?.title && <p className="text-xs text-gray-500 mb-2 font-medium">{data.title}</p>}
      <div className="flex-1"><canvas ref={canvasRef} /></div>
    </div>
  );
}
