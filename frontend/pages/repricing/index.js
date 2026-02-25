import { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import api from '../../lib/api';

const STRATEGIES = [
  { value: 'match_lowest',   label: 'Match Lowest',    desc: 'Match cheapest competitor ± margin',     color: 'blue' },
  { value: 'undercut',       label: 'Undercut',         desc: 'Price below all competitors by amount or %', color: 'amber' },
  { value: 'margin_based',   label: 'Margin Based',     desc: 'Cost + desired markup',                  color: 'emerald' },
  { value: 'dynamic',        label: 'Dynamic',          desc: 'Multi-factor: stock, competition, demand', color: 'violet' },
  { value: 'map_protected',  label: 'MAP Protected',    desc: 'Never below Minimum Advertised Price',   color: 'red' },
];

const STRATEGY_COLOR = {
  match_lowest:  'bg-blue-900/40 text-blue-400',
  undercut:      'bg-amber-900/40 text-amber-400',
  margin_based:  'bg-emerald-900/40 text-emerald-400',
  dynamic:       'bg-violet-900/40 text-violet-400',
  map_protected: 'bg-red-900/40 text-red-400',
};

const Ico = {
  rules:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>,
  check:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  pause:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  plus:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  trash:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>,
  bolt:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  x:      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>,
};

const EMPTY_FORM = { name: '', strategy: 'match_lowest', adjustment_value: '', adjustment_type: 'percentage', min_price: '', max_price: '', priority: 1 };

function RuleCard({ rule, onToggle, onDelete, onApply }) {
  const [deleting, setDeleting] = useState(false);
  const [applying, setApplying] = useState(false);
  const stratLabel = STRATEGIES.find(s => s.value === rule.strategy)?.label || rule.strategy;
  const stratStyle = STRATEGY_COLOR[rule.strategy] || 'bg-white/10 text-white/40';

  const handleDelete = async () => {
    if (!confirm(`Delete rule "${rule.name}"?`)) return;
    setDeleting(true);
    try {
      await onDelete(rule.id);
    } catch {
      setDeleting(false);
    }
  };

  const handleApply = async () => {
    setApplying(true);
    try {
      await onApply(rule.id);
    } catch {
      // parent handles error
    } finally {
      setApplying(false);
    }
  };

  return (
    <div
      style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
      className={`rounded-2xl overflow-hidden transition-opacity ${deleting ? 'opacity-50' : ''} ${!rule.is_active ? 'opacity-75' : ''}`}
    >
      <div className={`h-1 ${rule.is_active ? 'bg-amber-500' : 'bg-white/10'}`} />
      <div className="p-5">
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-white truncate">{rule.name}</h3>
            <span className={`inline-block mt-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${stratStyle}`}>
              {stratLabel}
            </span>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>P{rule.priority || 1}</span>
            <span className={`ml-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${rule.is_active ? 'bg-emerald-900/40 text-emerald-400' : 'bg-white/10 text-white/40'}`}>
              {rule.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>

        {/* Adjustment */}
        {rule.adjustment_value != null && (
          <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>
            Adjust by: <span className="font-medium text-white/70">
              {rule.adjustment_type === 'percentage' ? `${rule.adjustment_value}%` : `$${rule.adjustment_value}`}
            </span>
          </p>
        )}

        {/* Price bounds */}
        {(rule.min_price != null || rule.max_price != null) && (
          <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
            {rule.min_price != null && <>Min: <span className="font-medium text-white/70">${rule.min_price}</span> </>}
            {rule.max_price != null && <>Max: <span className="font-medium text-white/70">${rule.max_price}</span></>}
          </p>
        )}

        {/* Approval status */}
        {rule.needs_approval && (
          <span className="inline-block mb-3 px-2.5 py-0.5 bg-amber-900/40 text-amber-400 rounded-full text-xs font-medium">
            Pending Approval
          </span>
        )}

        <div className="flex items-center justify-between pt-3" style={{ borderTop: '1px solid var(--border)' }}>
          <button
            onClick={() => onToggle(rule.id)}
            className={`text-xs font-medium transition-colors ${rule.is_active ? 'text-white/40 hover:text-white' : 'text-amber-400 hover:text-amber-300'}`}
          >
            {rule.is_active ? 'Deactivate' : 'Activate'}
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={handleApply}
              disabled={applying || !rule.is_active}
              className="inline-flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 disabled:opacity-40 font-medium"
            >
              {Ico.bolt} Apply
            </button>
            <button onClick={handleDelete} disabled={deleting} className="text-white/30 hover:text-red-400 transition-colors disabled:opacity-50">
              {Ico.trash}
            </button>
          </div>
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
    if (!form.name.trim()) { setError('Rule name is required'); return; }
    setSaving(true);
    setError('');
    try {
      const payload = {
        name: form.name.trim(),
        strategy: form.strategy,
        priority: parseInt(form.priority) || 1,
        adjustment_type: form.adjustment_type,
      };
      if (form.adjustment_value) payload.adjustment_value = parseFloat(form.adjustment_value);
      if (form.min_price) payload.min_price = parseFloat(form.min_price);
      if (form.max_price) payload.max_price = parseFloat(form.max_price);
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
      <div
        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
        className="relative rounded-2xl w-full max-w-md p-6 space-y-4"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white">New Repricing Rule</h2>
          <button onClick={onClose} className="text-white/40 hover:text-white/70">{Ico.x}</button>
        </div>
        {error && <p className="text-xs text-red-400 bg-red-900/30 rounded-lg px-3 py-2">{error}</p>}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-white/70 mb-1.5">Rule Name</label>
            <input value={form.name} onChange={e => set('name', e.target.value)} placeholder="e.g. Undercut competitors by 5%" className="w-full px-3 py-2.5 glass-input rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-400/50" />
          </div>
          <div>
            <label className="block text-xs font-medium text-white/70 mb-1.5">Strategy</label>
            <select value={form.strategy} onChange={e => set('strategy', e.target.value)} className="w-full px-3 py-2.5 glass-input rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-400/50">
              {STRATEGIES.map(s => <option key={s.value} value={s.value}>{s.label} — {s.desc}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-white/70 mb-1.5">Adjustment</label>
              <input type="number" step="0.01" value={form.adjustment_value} onChange={e => set('adjustment_value', e.target.value)} placeholder="5" className="w-full px-3 py-2.5 glass-input rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-400/50" />
            </div>
            <div>
              <label className="block text-xs font-medium text-white/70 mb-1.5">Type</label>
              <select value={form.adjustment_type} onChange={e => set('adjustment_type', e.target.value)} className="w-full px-3 py-2.5 glass-input rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-400/50">
                <option value="percentage">Percentage %</option>
                <option value="fixed">Fixed $</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-white/70 mb-1.5">Min Price ($)</label>
              <input type="number" step="0.01" value={form.min_price} onChange={e => set('min_price', e.target.value)} placeholder="Optional" className="w-full px-3 py-2.5 glass-input rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-400/50" />
            </div>
            <div>
              <label className="block text-xs font-medium text-white/70 mb-1.5">Max Price ($)</label>
              <input type="number" step="0.01" value={form.max_price} onChange={e => set('max_price', e.target.value)} placeholder="Optional" className="w-full px-3 py-2.5 glass-input rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-400/50" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-white/70 mb-1.5">Priority (1 = highest)</label>
            <input type="number" min="1" value={form.priority} onChange={e => set('priority', e.target.value)} className="w-full px-3 py-2.5 glass-input rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-400/50" />
          </div>
          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }} className="flex-1 py-2.5 rounded-xl text-sm font-medium text-white/70 hover:bg-white/5 transition-colors">Cancel</button>
            <button type="submit" disabled={saving} className="flex-1 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90 shadow-gradient disabled:opacity-50">
              {saving ? 'Creating…' : 'Create Rule'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Apply Results Modal ───────────────────────────────────────────────────────
function ApplyResultsModal({ result, onClose }) {
  const storeConn = (() => {
    try { return JSON.parse(localStorage.getItem('marketintel_store_connection') || 'null'); }
    catch { return null; }
  })();

  const suggestions = result?.suggestions || result?.products || [];
  const [pushing, setPushing] = useState({});
  const [pushed, setPushed] = useState({});

  const pushOne = async (suggestion) => {
    if (!storeConn) return;
    setPushing(p => ({ ...p, [suggestion.product_id]: true }));
    try {
      if (storeConn.type === 'woocommerce') {
        await api.pushPriceToWooCommerce(
          storeConn.credentials?.store_url || storeConn.storeUrl, storeConn.credentials?.consumer_key || storeConn.consumerKey, storeConn.credentials?.consumer_secret || storeConn.consumerSecret,
          suggestion.sku || '', suggestion.title || '', suggestion.suggested_price
        );
      } else if (storeConn.type === 'shopify') {
        await api.pushPriceToShopify(
          storeConn.credentials?.shop_url || storeConn.shopUrl, storeConn.credentials?.access_token || storeConn.accessToken,
          suggestion.sku || '', suggestion.title || '', suggestion.suggested_price
        );
      }
      setPushed(p => ({ ...p, [suggestion.product_id]: true }));
    } catch (e) {
      alert('Push failed: ' + e.message);
    } finally {
      setPushing(p => ({ ...p, [suggestion.product_id]: false }));
    }
  };

  const pushAll = async () => {
    for (const s of suggestions) {
      if (!pushed[s.product_id]) await pushOne(s);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div
        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
        className="relative rounded-2xl w-full max-w-lg max-h-[80vh] flex flex-col"
      >
        {/* Header */}
        <div className="px-5 py-4 flex items-center justify-between shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
          <div>
            <h2 className="font-bold text-white">Rule Applied</h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {suggestions.length} suggested price{suggestions.length !== 1 ? 's' : ''} calculated
            </p>
          </div>
          <button onClick={onClose} className="text-white/40 hover:text-white/70">{Ico.x}</button>
        </div>

        {/* Results table */}
        <div className="overflow-y-auto flex-1 p-5">
          {suggestions.length === 0 ? (
            <p className="text-sm text-center py-8" style={{ color: 'var(--text-muted)' }}>No suggestions generated — add products and competitors first.</p>
          ) : (
            <div className="space-y-2">
              {suggestions.map((s) => (
                <div key={s.product_id ?? s.title} className="flex items-center gap-3 rounded-xl px-4 py-3" style={{ background: 'var(--bg-surface)' }}>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{s.title || s.product_title}</p>
                    {s.current_price != null && (
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                        Current: <span className="line-through">${s.current_price?.toFixed(2)}</span>
                        {' → '}
                        <span className="font-semibold text-amber-400">${s.suggested_price?.toFixed(2)}</span>
                      </p>
                    )}
                  </div>
                  {storeConn && (
                    pushed[s.product_id] ? (
                      <span className="text-xs text-emerald-400 font-medium shrink-0">Pushed ✓</span>
                    ) : (
                      <button
                        onClick={() => pushOne(s)}
                        disabled={!!pushing[s.product_id]}
                        className="shrink-0 inline-flex items-center gap-1 px-3 py-1.5 gradient-brand text-white text-xs font-semibold rounded-lg transition-opacity hover:opacity-90 shadow-gradient disabled:opacity-50"
                      >
                        {pushing[s.product_id] ? '…' : `Push to ${storeConn.type === 'shopify' ? 'Shopify' : 'WooCommerce'}`}
                      </button>
                    )
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 flex gap-3 shrink-0" style={{ borderTop: '1px solid var(--border)' }}>
          {storeConn && suggestions.length > 0 && (
            <button
              onClick={pushAll}
              className="flex-1 py-2.5 gradient-brand text-white rounded-xl text-sm font-semibold transition-opacity hover:opacity-90 shadow-gradient"
            >
              Push All to {storeConn.type === 'shopify' ? 'Shopify' : 'WooCommerce'}
            </button>
          )}
          <button onClick={onClose} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }} className={`${storeConn && suggestions.length > 0 ? '' : 'flex-1'} py-2.5 rounded-xl text-sm font-medium text-white/70 hover:bg-white/5 transition-colors px-6`}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

export default function RepricingPage() {
  const [rules, setRules] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [applyResult, setApplyResult] = useState(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [rulesData, productsData] = await Promise.all([
        api.request('/api/repricing/rules'),
        api.getProducts(),
      ]);
      setRules(rulesData?.rules || rulesData || []);
      setProducts(productsData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (id) => {
    try {
      await api.request(`/api/repricing/rules/${id}/toggle`, { method: 'POST' });
      setRules(rs => rs.map(r => r.id === id ? { ...r, is_active: !r.is_active } : r));
    } catch { alert('Failed to update rule'); }
  };

  const handleDelete = async (id) => {
    try {
      await api.request(`/api/repricing/rules/${id}`, { method: 'DELETE' });
      setRules(rs => rs.filter(r => r.id !== id));
    } catch { alert('Failed to delete rule'); }
  };

  const handleApply = async (id) => {
    try {
      const result = await api.request(`/api/repricing/rules/${id}/apply`, { method: 'POST' });
      setApplyResult(result ?? {});
    } catch (e) { alert(e.message || 'Failed to apply rule'); }
  };

  const handleCreate = async (data) => {
    const created = await api.request('/api/repricing/rules', { method: 'POST', body: JSON.stringify(data) });
    setRules(rs => [created, ...rs]);
  };

  const active   = rules.filter(r => r.is_active);
  const inactive = rules.filter(r => !r.is_active);

  if (loading) return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">
        <div className="grid grid-cols-3 gap-4">{[...Array(3)].map((_, i) => <div key={i} className="h-24 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)' }} />)}</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{[...Array(3)].map((_, i) => <div key={i} className="h-48 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)' }} />)}</div>
      </div>
    </Layout>
  );

  return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">

        {/* Header */}
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-white">Repricing</h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>Automated pricing rules with 5 strategies and approval workflows</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90 shadow-gradient"
          >
            {Ico.plus} New Rule
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-2xl p-5 flex items-center gap-4" style={{ background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.25)' }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 bg-blue-500/20 text-blue-400">{Ico.rules}</div>
            <div><p className="text-2xl font-bold text-white leading-none">{rules.length}</p><p className="text-xs text-white/50 mt-1">Total Rules</p></div>
          </div>
          <div className="rounded-2xl p-5 flex items-center gap-4" style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.25)' }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 bg-emerald-500/20 text-emerald-400">{Ico.check}</div>
            <div><p className="text-2xl font-bold text-white leading-none">{active.length}</p><p className="text-xs text-white/50 mt-1">Active</p></div>
          </div>
          <div className="rounded-2xl p-5 flex items-center gap-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 bg-white/10 text-white/40">{Ico.pause}</div>
            <div><p className="text-2xl font-bold text-white leading-none">{inactive.length}</p><p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Inactive</p></div>
          </div>
        </div>

        {/* Rules grid */}
        {rules.length === 0 ? (
          <div className="rounded-2xl p-16 text-center" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <div className="w-14 h-14 bg-white/10 rounded-2xl flex items-center justify-center mx-auto mb-4 text-white/20">{Ico.rules}</div>
            <p className="text-sm font-medium text-white">No repricing rules yet</p>
            <p className="text-xs mt-1 mb-5" style={{ color: 'var(--text-muted)' }}>Create a rule to automate your pricing strategy</p>
            <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90 shadow-gradient">
              {Ico.plus} New Rule
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {rules.map(r => (
              <RuleCard key={r.id} rule={r} onToggle={handleToggle} onDelete={handleDelete} onApply={handleApply} />
            ))}
          </div>
        )}

        {/* Strategies reference */}
        <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <h2 className="text-sm font-semibold text-white">Available Strategies</h2>
          </div>
          <div className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {STRATEGIES.map(s => (
              <div key={s.value} className="flex items-start gap-3 p-3 rounded-xl" style={{ background: 'var(--bg-elevated)' }}>
                <span className={`shrink-0 px-2.5 py-0.5 rounded-full text-xs font-medium ${STRATEGY_COLOR[s.value]}`}>{s.label}</span>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{s.desc}</p>
              </div>
            ))}
          </div>
        </div>

      </div>

      {showCreate && <CreateModal products={products} onClose={() => setShowCreate(false)} onCreate={handleCreate} />}
      {applyResult && <ApplyResultsModal result={applyResult} onClose={() => setApplyResult(null)} />}
    </Layout>
  );
}
