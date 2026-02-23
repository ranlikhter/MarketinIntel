import { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import api from '../../lib/api';

const ALERT_TYPES = [
  { value: 'price_drop',         label: 'Price Drop' },
  { value: 'price_increase',     label: 'Price Increase' },
  { value: 'any_change',         label: 'Any Change' },
  { value: 'out_of_stock',       label: 'Out of Stock' },
  { value: 'price_war',          label: 'Price War' },
  { value: 'new_competitor',     label: 'New Competitor' },
  { value: 'most_expensive',     label: "You're Most Expensive" },
  { value: 'competitor_raised',  label: 'Competitor Raised Price' },
  { value: 'back_in_stock',      label: 'Back In Stock' },
  { value: 'market_trend',       label: 'Market Trend' },
];

const TYPE_COLOR = {
  price_drop:        { text: 'text-red-400',     style: { background: 'rgba(239,68,68,0.12)',   border: '1px solid rgba(239,68,68,0.2)' } },
  price_increase:    { text: 'text-amber-400',   style: { background: 'rgba(245,158,11,0.12)',  border: '1px solid rgba(245,158,11,0.2)' } },
  any_change:        { text: 'text-blue-400',    style: { background: 'rgba(37,99,235,0.12)',   border: '1px solid rgba(37,99,235,0.2)' } },
  out_of_stock:      { text: 'text-orange-400',  style: { background: 'rgba(234,88,12,0.12)',   border: '1px solid rgba(234,88,12,0.2)' } },
  price_war:         { text: 'text-red-400',     style: { background: 'rgba(239,68,68,0.12)',   border: '1px solid rgba(239,68,68,0.2)' } },
  new_competitor:    { text: 'text-violet-400',  style: { background: 'rgba(124,58,237,0.12)',  border: '1px solid rgba(124,58,237,0.2)' } },
  most_expensive:    { text: 'text-red-400',     style: { background: 'rgba(239,68,68,0.12)',   border: '1px solid rgba(239,68,68,0.2)' } },
  competitor_raised: { text: 'text-emerald-400', style: { background: 'rgba(5,150,105,0.12)',   border: '1px solid rgba(5,150,105,0.2)' } },
  back_in_stock:     { text: 'text-emerald-400', style: { background: 'rgba(5,150,105,0.12)',   border: '1px solid rgba(5,150,105,0.2)' } },
  market_trend:      { text: 'text-blue-400',    style: { background: 'rgba(37,99,235,0.12)',   border: '1px solid rgba(37,99,235,0.2)' } },
};

const Ico = {
  bell:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>,
  check:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  pause:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  plus:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  trash:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>,
  x:      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>,
};

const TABS = ['All', 'Active', 'Inactive'];

const EMPTY_FORM = { alert_type: 'price_drop', threshold_value: '', product_id: '', notes: '' };

function AlertCard({ alert, onToggle, onDelete }) {
  const [deleting, setDeleting] = useState(false);
  const typeLabel = ALERT_TYPES.find(t => t.value === alert.alert_type)?.label || alert.alert_type;
  const typeStyle = TYPE_COLOR[alert.alert_type] || { text: 'text-white', style: { background: 'var(--bg-elevated)', border: '1px solid var(--border)' } };

  const handleDelete = async () => {
    if (!confirm('Delete this alert?')) return;
    setDeleting(true);
    await onDelete(alert.id);
  };

  return (
    <div
      className={`rounded-2xl overflow-hidden transition-opacity ${deleting ? 'opacity-50' : ''} ${!alert.is_active ? 'opacity-75' : ''}`}
      style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
    >
      <div className={`h-1 ${alert.is_active ? 'bg-amber-500' : 'bg-white/10'}`} />
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="min-w-0">
            <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium mb-1 ${typeStyle.text}`} style={typeStyle.style}>
              {typeLabel}
            </span>
            {alert.product_title && (
              <p className="text-sm font-semibold text-white truncate">{alert.product_title}</p>
            )}
          </div>
          {alert.is_active ? (
            <span className="shrink-0 px-2.5 py-0.5 rounded-full text-xs font-medium text-emerald-400" style={{ background: 'rgba(5,150,105,0.12)', border: '1px solid rgba(5,150,105,0.2)' }}>
              Active
            </span>
          ) : (
            <span className="shrink-0 px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ color: 'var(--text-muted)', background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
              Inactive
            </span>
          )}
        </div>

        {/* Threshold */}
        {alert.threshold_value != null && (
          <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>
            Threshold: <span className="font-medium text-white">{alert.threshold_value}%</span>
          </p>
        )}

        {/* Notes */}
        {alert.notes && (
          <p className="text-xs line-clamp-2 mb-3" style={{ color: 'var(--text-muted)' }}>{alert.notes}</p>
        )}

        {/* Last triggered */}
        {alert.last_triggered_at && (
          <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
            Last triggered: {new Date(alert.last_triggered_at).toLocaleDateString()}
          </p>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between pt-3" style={{ borderTop: '1px solid var(--border)' }}>
          <button
            onClick={() => onToggle(alert.id)}
            className={`text-xs font-medium transition-colors ${alert.is_active ? 'hover:text-white' : 'text-amber-400 hover:text-amber-300'}`}
            style={alert.is_active ? { color: 'var(--text-muted)' } : undefined}
          >
            {alert.is_active ? 'Deactivate' : 'Activate'}
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="hover:text-red-400 transition-colors disabled:opacity-50"
            style={{ color: 'var(--text-muted)' }}
          >
            {Ico.trash}
          </button>
        </div>
      </div>
    </div>
  );
}

function CreateModal({ products, onClose, onCreate }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = { alert_type: form.alert_type, notes: form.notes };
      if (form.product_id) payload.product_id = parseInt(form.product_id);
      if (form.threshold_value) payload.threshold_value = parseFloat(form.threshold_value);
      await onCreate(payload);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative rounded-2xl w-full max-w-md p-6 space-y-4" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-md)' }}>
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white">New Alert</h2>
          <button onClick={onClose} className="hover:text-white transition-colors" style={{ color: 'var(--text-muted)' }}>{Ico.x}</button>
        </div>

        {error && (
          <p className="text-xs text-red-400 rounded-lg px-3 py-2" style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.2)' }}>{error}</p>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Alert type */}
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>Alert Type</label>
            <select
              value={form.alert_type}
              onChange={e => set('alert_type', e.target.value)}
              className="w-full px-3 py-2.5 glass-input rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            >
              {ALERT_TYPES.map(t => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          {/* Product */}
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>Product (optional)</label>
            <select
              value={form.product_id}
              onChange={e => set('product_id', e.target.value)}
              className="w-full px-3 py-2.5 glass-input rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            >
              <option value="">All products</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
          </div>

          {/* Threshold */}
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>Threshold % (optional)</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={form.threshold_value}
              onChange={e => set('threshold_value', e.target.value)}
              placeholder="e.g. 5 for 5% change"
              className="w-full px-3 py-2.5 glass-input rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>Notes (optional)</label>
            <input
              type="text"
              value={form.notes}
              onChange={e => set('notes', e.target.value)}
              placeholder="Internal note…"
              className="w-full px-3 py-2.5 glass-input rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            />
          </div>

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors text-white hover:bg-white/5"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
            >
              Cancel
            </button>
            <button type="submit" disabled={saving} className="flex-1 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90 shadow-gradient disabled:opacity-50">
              {saving ? 'Creating…' : 'Create Alert'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('All');
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [alertData, productData] = await Promise.all([
        api.getAlerts(),
        api.getProducts(),
      ]);
      setAlerts(alertData);
      setProducts(productData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (id) => {
    try {
      await api.toggleAlert(id);
      setAlerts(as => as.map(a => a.id === id ? { ...a, is_active: !a.is_active } : a));
    } catch { alert('Failed to update alert'); }
  };

  const handleDelete = async (id) => {
    try {
      await api.deleteAlert(id);
      setAlerts(as => as.filter(a => a.id !== id));
    } catch { alert('Failed to delete alert'); }
  };

  const handleCreate = async (data) => {
    const created = await api.createAlert(data);
    setAlerts(as => [created, ...as]);
  };

  const active   = alerts.filter(a => a.is_active);
  const inactive = alerts.filter(a => !a.is_active);
  const filtered = tab === 'Active' ? active : tab === 'Inactive' ? inactive : alerts;

  if (loading) return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">
        <div className="grid grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <div key={i} className="h-24 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)' }} />)}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <div key={i} className="h-44 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)' }} />)}
        </div>
      </div>
    </Layout>
  );

  return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">

        {/* Header */}
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-white">Alerts</h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>Price alerts across 10 types, delivered by email, SMS, Slack and more</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90 shadow-gradient"
          >
            {Ico.plus} New Alert
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-2xl p-5 flex items-center gap-4" style={{ background: 'rgba(37,99,235,0.15)', border: '1px solid rgba(37,99,235,0.25)' }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-white" style={{ background: 'rgba(37,99,235,0.3)' }}>{Ico.bell}</div>
            <div>
              <p className="text-2xl font-bold text-white leading-none">{alerts.length}</p>
              <p className="text-xs text-white/80 mt-1">Total</p>
            </div>
          </div>
          <div className="rounded-2xl p-5 flex items-center gap-4" style={{ background: 'rgba(5,150,105,0.15)', border: '1px solid rgba(5,150,105,0.25)' }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-white" style={{ background: 'rgba(5,150,105,0.3)' }}>{Ico.check}</div>
            <div>
              <p className="text-2xl font-bold text-white leading-none">{active.length}</p>
              <p className="text-xs text-white/80 mt-1">Active</p>
            </div>
          </div>
          <div className="rounded-2xl p-5 flex items-center gap-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>{Ico.pause}</div>
            <div>
              <p className="text-2xl font-bold text-white leading-none">{inactive.length}</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Inactive</p>
            </div>
          </div>
        </div>

        {/* Filter tabs */}
        <div className="flex items-center gap-2">
          {TABS.map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                tab === t ? 'gradient-brand text-white shadow-gradient' : 'hover:bg-white/5'
              }`}
              style={tab !== t ? { color: 'var(--text-muted)' } : undefined}
            >
              {t}
              {t !== 'All' && (
                <span className={`ml-1.5 text-xs ${tab === t ? 'opacity-70' : ''}`} style={tab !== t ? { color: 'var(--text-muted)' } : undefined}>
                  ({t === 'Active' ? active.length : inactive.length})
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Grid */}
        {filtered.length === 0 ? (
          <div className="rounded-2xl p-16 text-center" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>{Ico.bell}</div>
            <p className="text-sm font-medium text-white">
              {tab === 'All' ? 'No alerts yet' : `No ${tab.toLowerCase()} alerts`}
            </p>
            <p className="text-xs mt-1 mb-5" style={{ color: 'var(--text-muted)' }}>
              {tab === 'All' ? 'Create an alert to get notified of price changes' : 'Change the filter to see other alerts'}
            </p>
            {tab === 'All' && (
              <button
                onClick={() => setShowCreate(true)}
                className="inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90 shadow-gradient"
              >
                {Ico.plus} New Alert
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {filtered.map(a => (
              <AlertCard key={a.id} alert={a} onToggle={handleToggle} onDelete={handleDelete} />
            ))}
          </div>
        )}

        {/* Alert types reference */}
        <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <h2 className="text-sm font-semibold text-white">Available Alert Types</h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>10 trigger types to keep you ahead of the market</p>
          </div>
          <div className="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            {ALERT_TYPES.map(t => {
              const ts = TYPE_COLOR[t.value] || { text: 'text-white', style: { background: 'var(--bg-elevated)', border: '1px solid var(--border)' } };
              return (
                <span key={t.value} className={`px-3 py-1.5 rounded-xl text-xs font-medium text-center ${ts.text}`} style={ts.style}>
                  {t.label}
                </span>
              );
            })}
          </div>
        </div>

      </div>

      {showCreate && (
        <CreateModal
          products={products}
          onClose={() => setShowCreate(false)}
          onCreate={handleCreate}
        />
      )}
    </Layout>
  );
}
