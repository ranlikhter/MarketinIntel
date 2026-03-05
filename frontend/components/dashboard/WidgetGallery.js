/**
 * WidgetGallery — modal for adding a new widget to a dashboard.
 * Shows all 8 widget types with description, lets user pick a product,
 * configure basic options, and select the size before adding.
 */
import { useState, useEffect } from 'react';
import api from '../../lib/api';

const WIDGET_TYPES = [
  {
    type: 'bubble_chart',
    icon: '🔵',
    name: 'Competitive Positioning',
    desc: 'Price vs. Rating bubble chart — spot the market gaps at a glance',
    sizes: ['medium', 'large'],
    defaultSize: 'large',
  },
  {
    type: 'price_history',
    icon: '📈',
    name: 'Price Trendlines',
    desc: 'Multi-line chart showing competitor price movements over time',
    sizes: ['medium', 'large', 'tall-large'],
    defaultSize: 'large',
  },
  {
    type: 'radar',
    icon: '🕸️',
    name: 'Listing Quality Radar',
    desc: 'Spider chart comparing images, video, A+, bullets and more',
    sizes: ['small', 'medium', 'large'],
    defaultSize: 'medium',
  },
  {
    type: 'calendar_heatmap',
    icon: '📅',
    name: 'Price Calendar',
    desc: 'GitHub-style heatmap of daily price changes — reveals patterns instantly',
    sizes: ['large', 'tall-large'],
    defaultSize: 'large',
  },
  {
    type: 'momentum_scatter',
    icon: '🚀',
    name: 'Market Momentum',
    desc: 'Price Δ% vs review velocity scatter — who's gaining ground?',
    sizes: ['medium', 'large'],
    defaultSize: 'large',
  },
  {
    type: 'kpi_cards',
    icon: '📊',
    name: 'KPI Summary',
    desc: 'Row of headline numbers: lowest price, avg market, your position',
    sizes: ['medium', 'large'],
    defaultSize: 'large',
  },
  {
    type: 'pie_chart',
    icon: '🥧',
    name: 'Distribution Pie',
    desc: 'Doughnut chart: fulfillment type, price ranges, badges, stock status',
    sizes: ['small', 'medium'],
    defaultSize: 'medium',
  },
  {
    type: 'bar_chart',
    icon: '📉',
    name: 'Price Comparison Bar',
    desc: 'Horizontal bar chart comparing every competitor price at a glance',
    sizes: ['small', 'medium', 'large'],
    defaultSize: 'medium',
  },
];

const SIZE_LABELS = {
  small:        'Small (1/3)',
  medium:       'Medium (1/2)',
  large:        'Full Width',
  'tall-medium':'Tall Medium',
  'tall-large': 'Tall Full Width',
};

const METRIC_OPTIONS = [
  { value: 'price',           label: 'Price ($)' },
  { value: 'effective_price', label: 'Effective Price (after coupon)' },
  { value: 'bsr',             label: 'Best Seller Rank' },
  { value: 'rating',          label: 'Star Rating' },
  { value: 'review_count',    label: 'Review Count' },
];

const COLOR_SCHEMES = ['rainbow','blue','green','purple','orange'];
const PIE_METRICS = [
  { value: 'fulfillment_type', label: 'Fulfillment Type' },
  { value: 'price_range',      label: 'Price Range Buckets' },
  { value: 'stock_status',     label: 'Stock Status' },
  { value: 'badges',           label: 'Badge Distribution' },
];

export default function WidgetGallery({ onAdd, onClose }) {
  const [step, setStep] = useState('pick');       // pick | configure
  const [selected, setSelected] = useState(null);
  const [products, setProducts] = useState([]);
  const [config, setConfig] = useState({
    product_id: '',
    days: 30,
    metric: 'price',
    color_scheme: 'rainbow',
    pie_metric: 'fulfillment_type',
    size: 'medium',
    title: '',
  });

  useEffect(() => {
    api.getProducts().then(data => setProducts(data?.products || data || [])).catch(() => {});
  }, []);

  function pickWidget(wt) {
    setSelected(wt);
    setConfig(c => ({ ...c, size: wt.defaultSize }));
    setStep('configure');
  }

  function handleAdd() {
    if (!config.product_id) return;
    const { size, title, product_id, ...rest } = config;
    onAdd({
      widget_type: selected.type,
      title: title || selected.name,
      size,
      config: { product_id: Number(product_id), ...rest },
    });
  }

  const set = (k, v) => setConfig(c => ({ ...c, [k]: v }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between flex-shrink-0">
          <div>
            {step === 'configure' && (
              <button onClick={() => setStep('pick')} className="text-indigo-600 text-sm font-medium mb-1 flex items-center gap-1">
                ← Back
              </button>
            )}
            <h2 className="text-lg font-semibold text-gray-900">
              {step === 'pick' ? 'Add Widget' : `Configure: ${selected?.name}`}
            </h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 p-1.5 rounded-lg hover:bg-gray-100">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {step === 'pick' ? (
            <div className="grid grid-cols-2 gap-3">
              {WIDGET_TYPES.map(wt => (
                <button
                  key={wt.type}
                  onClick={() => pickWidget(wt)}
                  className="text-left p-4 rounded-xl border-2 border-gray-100 hover:border-indigo-400 hover:bg-indigo-50/40 transition-all group"
                >
                  <div className="text-2xl mb-2">{wt.icon}</div>
                  <div className="font-semibold text-gray-900 text-sm group-hover:text-indigo-700">{wt.name}</div>
                  <div className="text-xs text-gray-500 mt-1 leading-relaxed">{wt.desc}</div>
                </button>
              ))}
            </div>
          ) : (
            <div className="space-y-5">
              {/* Product selector */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Product *</label>
                <select
                  value={config.product_id}
                  onChange={e => set('product_id', e.target.value)}
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Select a product…</option>
                  {products.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
                </select>
              </div>

              {/* Widget title */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Widget Title</label>
                <input
                  value={config.title}
                  onChange={e => set('title', e.target.value)}
                  placeholder={selected?.name}
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {/* Two-column options */}
              <div className="grid grid-cols-2 gap-4">
                {/* Size */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Size</label>
                  <select value={config.size} onChange={e => set('size', e.target.value)}
                    className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                    {(selected?.sizes || ['medium','large']).map(s => (
                      <option key={s} value={s}>{SIZE_LABELS[s] || s}</option>
                    ))}
                  </select>
                </div>

                {/* Time window */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Time Window</label>
                  <select value={config.days} onChange={e => set('days', Number(e.target.value))}
                    className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                    {[7,14,30,60,90,180,365].map(d => <option key={d} value={d}>{d} days</option>)}
                  </select>
                </div>

                {/* Metric (not for pie, KPI, or calendar) */}
                {!['pie_chart','kpi_cards','calendar_heatmap','radar'].includes(selected?.type) && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Metric</label>
                    <select value={config.metric} onChange={e => set('metric', e.target.value)}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                      {METRIC_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </div>
                )}

                {/* Pie metric */}
                {selected?.type === 'pie_chart' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Show Distribution Of</label>
                    <select value={config.pie_metric} onChange={e => set('pie_metric', e.target.value)}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                      {PIE_METRICS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </div>
                )}

                {/* Colour scheme */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Colour Scheme</label>
                  <select value={config.color_scheme} onChange={e => set('color_scheme', e.target.value)}
                    className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                    {COLOR_SCHEMES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                  </select>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        {step === 'configure' && (
          <div className="px-6 py-4 border-t border-gray-100 flex gap-3 flex-shrink-0">
            <button onClick={onClose}
              className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50">
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={!config.product_id}
              className="flex-1 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
              Add Widget
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
