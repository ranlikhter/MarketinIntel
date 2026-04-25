import { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import api from '../../lib/api';

const EMPTY = { category_name: '', default_cogs_pct: '', default_target_margin_pct: '', platform_fee_pct: '', shipping_cost: '' };
const NUM_FIELDS = ['default_cogs_pct', 'default_target_margin_pct', 'platform_fee_pct', 'shipping_cost'];

export default function CategoryProfilesPage() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // id of row being edited, or 'new'
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      setLoading(true);
      const data = await api.getCategoryProfiles();
      setProfiles(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const startNew = () => { setEditing('new'); setForm(EMPTY); setError(''); };

  const startEdit = (p) => {
    setEditing(p.id);
    setForm({
      category_name: p.category_name,
      default_cogs_pct: p.default_cogs_pct ?? '',
      default_target_margin_pct: p.default_target_margin_pct ?? '',
      platform_fee_pct: p.platform_fee_pct ?? '',
      shipping_cost: p.shipping_cost ?? '',
    });
    setError('');
  };

  const cancel = () => { setEditing(null); setForm(EMPTY); setError(''); };

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const save = async () => {
    if (!form.category_name.trim()) { setError('Category name is required'); return; }
    setSaving(true);
    setError('');
    try {
      const payload = { ...form };
      NUM_FIELDS.forEach(f => { payload[f] = payload[f] !== '' ? parseFloat(payload[f]) : null; });
      if (editing === 'new') {
        const created = await api.upsertCategoryProfile(payload);
        await load();
      } else {
        await api.updateCategoryProfile(editing, payload);
        await load();
      }
      cancel();
    } catch (e) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const del = async (id, name) => {
    if (!confirm(`Delete pricing profile for "${name}"?`)) return;
    await api.deleteCategoryProfile(id);
    setProfiles(ps => ps.filter(p => p.id !== id));
  };

  const rowStyle = { borderBottom: '1px solid var(--border)' };

  return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">

        {/* Header */}
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-white">Category Pricing Profiles</h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
              Set default cost and margin assumptions per category — used as price floors when no individual cost is set
            </p>
          </div>
          <button
            onClick={startNew}
            className="inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90 shadow-gradient"
          >
            + New Profile
          </button>
        </div>

        {/* Info card */}
        <div className="rounded-xl p-4 flex items-start gap-3" style={{ background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.2)' }}>
          <span className="text-amber-400 text-lg shrink-0">💡</span>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            When a repricing rule suggests a price, MarketIntel checks the floor:
            estimated cost ÷ (1 − target margin). If you also set <strong style={{ color: '#e5e7eb' }}>cost_price</strong> on
            individual products, that takes priority. Category profiles are the safety net.
          </p>
        </div>

        {/* New profile form */}
        {editing === 'new' && (
          <ProfileForm
            form={form} set={set} error={error}
            saving={saving} onSave={save} onCancel={cancel}
            title="New Category Profile"
          />
        )}

        {/* Table */}
        <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Category', 'Est. COGS %', 'Target Margin %', 'Platform Fee %', 'Shipping $', ''].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>Loading…</td></tr>
                )}
                {!loading && profiles.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-12 text-center">
                    <p className="text-sm font-medium text-white">No profiles yet</p>
                    <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Add a category profile to protect margins during automated repricing</p>
                  </td></tr>
                )}
                {profiles.map(p => (
                  editing === p.id ? (
                    <tr key={p.id}>
                      <td colSpan={6} className="p-0">
                        <div className="px-4 py-4" style={{ background: 'var(--bg-elevated)' }}>
                          <ProfileForm
                            form={form} set={set} error={error}
                            saving={saving} onSave={save} onCancel={cancel}
                            title={`Edit "${p.category_name}"`}
                            hideTitle
                          />
                        </div>
                      </td>
                    </tr>
                  ) : (
                    <tr key={p.id} style={rowStyle}>
                      <td className="px-4 py-3 font-medium text-white">{p.category_name}</td>
                      <td className="px-4 py-3" style={{ color: 'var(--text-muted)' }}>{p.default_cogs_pct != null ? `${p.default_cogs_pct}%` : '—'}</td>
                      <td className="px-4 py-3" style={{ color: p.default_target_margin_pct != null ? '#10b981' : 'var(--text-muted)' }}>
                        {p.default_target_margin_pct != null ? `${p.default_target_margin_pct}%` : '—'}
                      </td>
                      <td className="px-4 py-3" style={{ color: 'var(--text-muted)' }}>{p.platform_fee_pct != null ? `${p.platform_fee_pct}%` : '—'}</td>
                      <td className="px-4 py-3" style={{ color: 'var(--text-muted)' }}>{p.shipping_cost != null ? `$${p.shipping_cost}` : '—'}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2 justify-end">
                          <button onClick={() => startEdit(p)} className="text-xs px-3 py-1.5 rounded-lg transition-opacity hover:opacity-80" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>Edit</button>
                          <button onClick={() => del(p.id, p.category_name)} className="text-xs px-3 py-1.5 rounded-lg transition-opacity hover:opacity-80" style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)' }}>Delete</button>
                        </div>
                      </td>
                    </tr>
                  )
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </Layout>
  );
}

function ProfileForm({ form, set, error, saving, onSave, onCancel, title, hideTitle }) {
  return (
    <div className="rounded-2xl p-5 space-y-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
      {!hideTitle && <h3 className="text-sm font-semibold text-white">{title}</h3>}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div>
          <label className="text-xs font-medium mb-1.5 block" style={{ color: 'var(--text-muted)' }}>Category Name *</label>
          <input
            value={form.category_name}
            onChange={e => set('category_name', e.target.value)}
            placeholder="e.g. Electronics"
            className="w-full px-3 py-2 rounded-xl text-sm text-white"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
          />
        </div>
        <div>
          <label className="text-xs font-medium mb-1.5 block" style={{ color: 'var(--text-muted)' }}>Est. COGS % of price</label>
          <input
            type="number" min="0" max="100" step="0.1"
            value={form.default_cogs_pct}
            onChange={e => set('default_cogs_pct', e.target.value)}
            placeholder="e.g. 45"
            className="w-full px-3 py-2 rounded-xl text-sm text-white"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
          />
          <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Used when product has no cost set</p>
        </div>
        <div>
          <label className="text-xs font-medium mb-1.5 block" style={{ color: 'var(--text-muted)' }}>Target Margin %</label>
          <input
            type="number" min="0" max="99" step="0.1"
            value={form.default_target_margin_pct}
            onChange={e => set('default_target_margin_pct', e.target.value)}
            placeholder="e.g. 30"
            className="w-full px-3 py-2 rounded-xl text-sm text-white"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
          />
        </div>
        <div>
          <label className="text-xs font-medium mb-1.5 block" style={{ color: 'var(--text-muted)' }}>Platform Fee %</label>
          <input
            type="number" min="0" max="50" step="0.01"
            value={form.platform_fee_pct}
            onChange={e => set('platform_fee_pct', e.target.value)}
            placeholder="e.g. 8.5"
            className="w-full px-3 py-2 rounded-xl text-sm text-white"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
          />
        </div>
        <div>
          <label className="text-xs font-medium mb-1.5 block" style={{ color: 'var(--text-muted)' }}>Avg Shipping Cost $</label>
          <input
            type="number" min="0" step="0.01"
            value={form.shipping_cost}
            onChange={e => set('shipping_cost', e.target.value)}
            placeholder="e.g. 5.00"
            className="w-full px-3 py-2 rounded-xl text-sm text-white"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
          />
        </div>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="flex gap-3">
        <button
          onClick={onSave} disabled={saving}
          className="px-5 py-2 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save Profile'}
        </button>
        <button onClick={onCancel} className="px-4 py-2 rounded-xl text-sm transition-opacity hover:opacity-80" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
          Cancel
        </button>
      </div>
    </div>
  );
}
