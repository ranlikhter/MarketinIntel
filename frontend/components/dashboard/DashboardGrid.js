/**
 * DashboardGrid
 *
 * Renders the drag-to-reorder widget grid.
 * Uses HTML5 Drag API + a flex-wrap layout.
 * Widget sizes map to Tailwind width classes.
 *
 * Drag model:
 *   - dragSrc  = index of the widget being dragged
 *   - On dragOver: swap positions in local state for live preview
 *   - On drop: commit to parent + API (debounced via onLayoutChange)
 */
import { useState, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';

// Dynamically import chart widgets to avoid SSR issues with Chart.js
const WIDGET_COMPONENTS = {
  bubble_chart:     dynamic(() => import('./widgets/BubbleChartWidget'),    { ssr: false }),
  price_history:    dynamic(() => import('./widgets/PriceHistoryWidget'),   { ssr: false }),
  radar:            dynamic(() => import('./widgets/RadarWidget'),           { ssr: false }),
  calendar_heatmap: dynamic(() => import('./widgets/CalendarHeatmapWidget'),{ ssr: false }),
  momentum_scatter: dynamic(() => import('./widgets/MomentumWidget'),       { ssr: false }),
  kpi_cards:        dynamic(() => import('./widgets/KpiCardWidget'),         { ssr: false }),
  pie_chart:        dynamic(() => import('./widgets/PieChartWidget'),        { ssr: false }),
  bar_chart:        dynamic(() => import('./widgets/BarChartWidget'),        { ssr: false }),
};

const SIZE_CLASSES = {
  small:        'w-full sm:w-1/3',
  medium:       'w-full sm:w-1/2',
  large:        'w-full',
  'tall-medium':'w-full sm:w-1/2',
  'tall-large': 'w-full',
};
const HEIGHT_CLASSES = {
  small:        'h-56',
  medium:       'h-72',
  large:        'h-72',
  'tall-medium':'h-96',
  'tall-large': 'h-[28rem]',
};

const WIDGET_ICONS = {
  bubble_chart:'🔵', price_history:'📈', radar:'🕸️',
  calendar_heatmap:'📅', momentum_scatter:'🚀',
  kpi_cards:'📊', pie_chart:'🥧', bar_chart:'📉',
};

function WidgetShell({ widget, data, isLoading, error, isEditing, onEdit, onDragStart, onDragOver, onDrop, isDragOver }) {
  const Component = WIDGET_COMPONENTS[widget.widget_type];
  const heightCls = HEIGHT_CLASSES[widget.size] || 'h-72';
  const widthCls = SIZE_CLASSES[widget.size] || 'w-full sm:w-1/2';

  return (
    <div
      className={`${widthCls} p-2 flex-shrink-0`}
      draggable={isEditing}
      onDragStart={onDragStart}
      onDragOver={e => { e.preventDefault(); onDragOver(); }}
      onDrop={onDrop}
    >
      <div className={`bg-white rounded-2xl border-2 transition-all h-full flex flex-col overflow-hidden
        ${isDragOver ? 'border-indigo-400 shadow-lg scale-[1.01]' : 'border-gray-100 shadow-sm'}
        ${isEditing ? 'cursor-grab active:cursor-grabbing' : ''}
      `}>
        {/* Widget header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-50 flex-shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            {isEditing && (
              <span className="text-gray-300 cursor-grab flex-shrink-0">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 6a2 2 0 100-4 2 2 0 000 4zm8 0a2 2 0 100-4 2 2 0 000 4zM8 14a2 2 0 100-4 2 2 0 000 4zm8 0a2 2 0 100-4 2 2 0 000 4zM8 22a2 2 0 100-4 2 2 0 000 4zm8 0a2 2 0 100-4 2 2 0 000 4z" />
                </svg>
              </span>
            )}
            <span className="text-base leading-none">{WIDGET_ICONS[widget.widget_type]}</span>
            <span className="text-sm font-semibold text-gray-800 truncate">
              {widget.title || widget.widget_type.replace(/_/g, ' ')}
            </span>
          </div>
          {isEditing && (
            <button
              onClick={() => onEdit(widget)}
              className="text-gray-400 hover:text-indigo-600 p-1.5 rounded-lg hover:bg-indigo-50 flex-shrink-0"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          )}
        </div>

        {/* Chart area */}
        <div className={`flex-1 p-3 ${heightCls} min-h-0`}>
          {isLoading ? (
            <div className="w-full h-full flex items-center justify-center">
              <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : error ? (
            <div className="w-full h-full flex flex-col items-center justify-center gap-2 text-gray-400">
              <span className="text-3xl">⚠️</span>
              <p className="text-xs text-center">{error}</p>
            </div>
          ) : !data ? (
            <div className="w-full h-full flex items-center justify-center text-gray-300 text-xs">No data yet</div>
          ) : Component ? (
            <div className="w-full h-full">
              <Component data={data} widget={widget} />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function DashboardGrid({ widgets, widgetData, widgetLoading, widgetErrors, isEditing, onEditWidget, onLayoutChange }) {
  const [ordered, setOrdered] = useState(() => [...widgets].sort((a, b) => a.position - b.position));
  const [dragOver, setDragOver] = useState(null);
  const dragSrc = useRef(null);

  // Keep ordered in sync with external widget changes
  const widgetIds = widgets.map(w => w.id).join(',');
  useState(() => {
    setOrdered([...widgets].sort((a, b) => a.position - b.position));
  }, [widgetIds]);

  const handleDragStart = useCallback((idx) => {
    dragSrc.current = idx;
  }, []);

  const handleDragOver = useCallback((idx) => {
    if (dragSrc.current === null || dragSrc.current === idx) return;
    setDragOver(idx);
    setOrdered(prev => {
      const next = [...prev];
      const [moved] = next.splice(dragSrc.current, 1);
      next.splice(idx, 0, moved);
      dragSrc.current = idx;
      return next;
    });
  }, []);

  const handleDrop = useCallback(() => {
    setDragOver(null);
    dragSrc.current = null;
    const layout = ordered.map((w, i) => ({ widget_id: w.id, position: i }));
    onLayoutChange(layout);
  }, [ordered, onLayoutChange]);

  // Sync ordered when widgets prop changes (e.g. after add/delete)
  const stableOrdered = widgets.length !== ordered.length
    ? [...widgets].sort((a, b) => a.position - b.position)
    : ordered;

  return (
    <div className="flex flex-wrap -m-2">
      {stableOrdered.map((widget, idx) => (
        <WidgetShell
          key={widget.id}
          widget={widget}
          data={widgetData[widget.id]}
          isLoading={widgetLoading[widget.id]}
          error={widgetErrors[widget.id]}
          isEditing={isEditing}
          onEdit={onEditWidget}
          onDragStart={() => handleDragStart(idx)}
          onDragOver={() => handleDragOver(idx)}
          onDrop={handleDrop}
          isDragOver={dragOver === idx}
        />
      ))}
    </div>
  );
}
