/**
 * WidgetConfigPanel — right-side slide-in panel for editing a widget's config.
 */
import { useState, useEffect } from 'react';

const METRIC_OPTIONS = [
  { value: 'price',           label: 'Price ($)' },
  { value: 'effective_price', label: 'Effective Price' },
  { value: 'bsr',             label: 'Best Seller Rank' },
  { value: 'rating',          label: 'Star Rating' },
  { value: 'review_count',    label: 'Review Count' },
];

const SIZE_OPTIONS = [
  { value: 'small',        label: 'Small (1/3 width)' },
  { value: 'medium',       label: 'Medium (1/2 width)' },
  { value: 'large',        label: 'Full Width' },
  { value: 'tall-medium',  label: 'Tall Medium' },
  { value: 'tall-large',   label: 'Tall Full Width' },
];

const PIE_METRICS = [
  { value: 'fulfillment_type', label: 'Fulfillment Type' },
  { value: 'price_range',      label: 'Price Range Buckets' },
  { value: 'stock_status',     label: 'Stock Status' },
  { value: 'badges',           label: 'Badge Distribution' },
];

export default function WidgetConfigPanel({ widget, onSave, onDelete, onClose }) {
  const [title, setTitle] = useState(widget.title || '');
  const [size, setSize] = useState(widget.size || 'medium');
  const [cfg, setCfg] = useState({ ...widget.config });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setTitle(widget.title || '');
    setSize(widget.size || 'medium');
    setCfg({ ...widget.config });
  }, [widget.id]);

  const set = (k, v) => setCfg(c => ({ ...c, [k]: v }));

  async function handleSave() {
    setSaving(true);
    try {
      await onSave(widget.id, { title, size, config: cfg });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-y-0 right-0 w-80 bg-white border-l border-gray-200 shadow-2xl z-40 flex flex-col">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between flex-shrink-0">
        <h3 className="font-semibold text-gray-900 text-sm">Widget Settings</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-700 p-1 rounded">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">Title</label>
          <input value={title} onChange={e => setTitle(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">Size</label>
          <select value={size} onChange={e => setSize(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
            {SIZE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">Time Window</label>
          <select value={cfg.days || 30} onChange={e => set('days', Number(e.target.value))}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
            {[7,14,30,60,90,180,365].map(d => <option key={d} value={d}>{d} days</option>)}
          </select>
        </div>

        {!['pie_chart','kpi_cards','calendar_heatmap','radar'].includes(widget.widget_type) && (
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">Metric</label>
            <select value={cfg.metric || 'price'} onChange={e => set('metric', e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
              {METRIC_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
        )}

        {widget.widget_type === 'pie_chart' && (
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">Distribution Of</label>
            <select value={cfg.pie_metric || 'fulfillment_type'} onChange={e => set('pie_metric', e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
              {PIE_METRICS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
        )}

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">Colour Scheme</label>
          <div className="flex gap-2 flex-wrap">
            {['rainbow','blue','green','purple','orange'].map(s => {
              const COLORS = { rainbow:'bg-gradient-to-r from-red-400 via-green-400 to-blue-500', blue:'bg-blue-500', green:'bg-green-500', purple:'bg-purple-500', orange:'bg-orange-400' };
              return (
                <button key={s} onClick={() => set('color_scheme', s)}
                  className={`w-8 h-8 rounded-full ${COLORS[s]} border-2 transition-all ${cfg.color_scheme === s ? 'border-gray-800 scale-110' : 'border-transparent'}`}
                  title={s}
                />
              );
            })}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5 uppercase tracking-wide">
            Filter Competitors
          </label>
          <input
            value={(cfg.competitors || []).join(', ')}
            onChange={e => set('competitors', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
            placeholder="Amazon, Walmart (empty = all)"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <p className="text-xs text-gray-400 mt-1">Comma-separated. Leave empty to show all.</p>
        </div>
      </div>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-gray-100 space-y-2 flex-shrink-0">
        <button onClick={handleSave} disabled={saving}
          className="w-full py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
          {saving ? 'Saving…' : 'Save Changes'}
        </button>
        <button onClick={() => onDelete(widget.id)}
          className="w-full py-2.5 border border-red-200 text-red-600 rounded-xl text-sm font-medium hover:bg-red-50">
          Remove Widget
        </button>
      </div>
    </div>
  );
}
