/**
 * CalendarHeatmap — GitHub contribution-style grid.
 * Pure CSS + React, no Chart.js dependency.
 * Each cell = 1 day, colour intensity = price change magnitude.
 */
import { useMemo } from 'react';

function intensityClass(changePct, minChange, maxChange) {
  if (changePct === 0) return 'bg-gray-100';
  if (changePct > 0) {
    const t = maxChange > 0 ? changePct / maxChange : 0;
    if (t > 0.75) return 'bg-red-600';
    if (t > 0.5)  return 'bg-red-400';
    if (t > 0.25) return 'bg-red-300';
    return 'bg-red-200';
  }
  const t = minChange < 0 ? changePct / minChange : 0;
  if (t > 0.75) return 'bg-green-600';
  if (t > 0.5)  return 'bg-green-400';
  if (t > 0.25) return 'bg-green-300';
  return 'bg-green-200';
}

const DAY_NAMES = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

export default function CalendarHeatmapWidget({ data }) {
  const { cells = [], minChange = 0, maxChange = 0 } = data || {};

  // Build a map from date string → cell
  const cellMap = useMemo(() => Object.fromEntries(cells.map(c => [c.date, c])), [cells]);

  if (!cells.length) {
    return <div className="flex items-center justify-center h-full text-gray-400 text-sm">No price history data</div>;
  }

  // Build calendar weeks from the date range
  const firstDate = new Date(cells[0].date);
  const lastDate  = new Date(cells[cells.length - 1].date);

  // Pad to Sunday
  const start = new Date(firstDate);
  start.setDate(start.getDate() - start.getDay());

  const weeks = [];
  let current = new Date(start);
  while (current <= lastDate) {
    const week = [];
    for (let d = 0; d < 7; d++) {
      const key = current.toISOString().slice(0, 10);
      week.push({ date: key, data: cellMap[key] || null });
      current = new Date(current);
      current.setDate(current.getDate() + 1);
    }
    weeks.push(week);
  }

  // Month labels
  const monthLabels = [];
  weeks.forEach((week, wi) => {
    const sunday = new Date(week[0].date);
    if (wi === 0 || sunday.getDate() <= 7) {
      monthLabels.push({ weekIndex: wi, label: MONTHS[sunday.getMonth()] });
    }
  });

  return (
    <div className="overflow-x-auto">
      <div className="flex gap-1 min-w-max">
        {/* Day-name column */}
        <div className="flex flex-col gap-1 mr-1">
          <div className="h-4" /> {/* spacer for month row */}
          {DAY_NAMES.map(d => (
            <div key={d} className="h-3 w-5 flex items-center justify-end text-gray-400" style={{ fontSize: 9 }}>{d}</div>
          ))}
        </div>

        {/* Calendar grid */}
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-1">
            {/* Month label */}
            <div className="h-4 flex items-end" style={{ fontSize: 9 }}>
              {monthLabels.find(m => m.weekIndex === wi)?.label || ''}
            </div>
            {week.map(({ date, data: cell }) => (
              <div
                key={date}
                title={cell ? `${date}: avg $${cell.avg_price} (${cell.change_pct > 0 ? '+' : ''}${cell.change_pct.toFixed(1)}%)` : date}
                className={`h-3 w-3 rounded-sm transition-transform hover:scale-125 ${
                  cell ? intensityClass(cell.change_pct, minChange, maxChange) : 'bg-gray-50'
                }`}
              />
            ))}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-2 mt-3 text-xs text-gray-500">
        <span>Price dropped</span>
        {['bg-green-200','bg-green-400','bg-green-600'].map(c => (
          <div key={c} className={`w-3 h-3 rounded-sm ${c}`} />
        ))}
        <div className="w-3 h-3 rounded-sm bg-gray-100" />
        {['bg-red-200','bg-red-400','bg-red-600'].map(c => (
          <div key={c} className={`w-3 h-3 rounded-sm ${c}`} />
        ))}
        <span>Price rose</span>
      </div>
    </div>
  );
}
