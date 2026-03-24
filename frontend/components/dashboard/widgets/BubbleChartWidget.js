import { useEffect, useRef } from 'react';
import { Chart, BubbleController, LinearScale, PointElement, Tooltip, Legend } from 'chart.js';

Chart.register(BubbleController, LinearScale, PointElement, Tooltip, Legend);

export default function BubbleChartWidget({ data }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !data?.competitors) return;
    chartRef.current?.destroy();

    const datasets = data.competitors.map(c => ({
      label: c.name,
      data: [{ x: c.x, y: c.y, r: c.r }],
      backgroundColor: c.color + 'cc',
      borderColor: c.color,
      borderWidth: 2,
    }));

    // Add "your product" as a distinct point
    if (data.your_product?.price != null) {
      datasets.push({
        label: data.your_product.name || 'Your Product',
        data: [{ x: data.your_product.price, y: data.your_product.rating || 0, r: 14 }],
        backgroundColor: '#F59E0Bcc',
        borderColor: '#F59E0B',
        borderWidth: 3,
        borderDash: [4, 2],
      });
    }

    chartRef.current = new Chart(canvasRef.current, {
      type: 'bubble',
      data: { datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            title: { display: true, text: data.axes?.x || 'Price ($)', font: { size: 11 } },
            grid: { color: '#f1f5f9' },
          },
          y: {
            title: { display: true, text: data.axes?.y || 'Rating (0–5)', font: { size: 11 } },
            min: 0,
            max: 5,
            grid: { color: '#f1f5f9' },
          },
        },
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12, font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const c = data.competitors.find(x => x.name === ctx.dataset.label);
                if (!c) return ctx.dataset.label;
                return [
                  `${c.name}`,
                  `Price: $${c.x}`,
                  `Rating: ${c.y}★`,
                  `Reviews: ${c.review_count?.toLocaleString() || '—'}`,
                  c.is_prime ? '✓ Prime' : '',
                ].filter(Boolean);
              },
            },
          },
        },
      },
    });
    return () => chartRef.current?.destroy();
  }, [data]);

  return <canvas ref={canvasRef} />;
}
