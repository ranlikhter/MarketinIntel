import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../lib/api';

const EMPTY_ROW = { category_name: '', default_cogs_pct: '', default_target_margin_pct: '' };

function ProfileRow({ profile, onSave, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    default_cogs_pct: profile.default_cogs_pct != null ? String(profile.default_cogs_pct) : '',
    default_target_margin_pct: profile.default_target_margin_pct != null ? String(profile.default_target_margin_pct) : '',
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const floor = (() => {
    const cogs = parseFloat(form.default_cogs_pct);
    const margin = parseFloat(form.default_target_margin_pct);
    if (!isNaN(cogs) && !isNaN(margin) && margin > 0 && margin < 100 && cogs > 0) {
      const estimatedCost = (cogs / 100) * 100; // relative to $100 price
      return (estimatedCost / (1 - margin / 100)).toFixed(0);
    }
    return null;
  })();

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(profile.id, {
        default_cogs_pct: form.default_cogs_pct ? parseFloat(form.default_cogs_pct) : null,
        default_target_margin_pct: form.default_target_margin_pct ? parseFloat(form.default_target_margin_pct) : null,
      });
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Delete defaults for "${profile.category_name}"?`)) return;
    setDeleting(true);
    try { await onDelete(profile.id); }
    finally { setDeleting(false); }
  };

  return (
    <tr style={{ borderBottom: '1px solid var(--border)', opacity: deleting ? 0.4 : 1 }}>
      <td className="px-4 py-3 text-sm font-medium text-white">{profile.category_name}</td>
      <td className="px-4 py-3">
        {editing ? (
          <input
            type="number" min="0" max="100" step="0.1"
            value={form.default_cogs_pct}
            onChange={e => setForm(f => ({ ...f, default_cogs_pct: e.target.value }))}
            className="w-20 px-2 py-1 rounded text-sm text-white"
            style={{ background: 'var(--bg-input, #1a1a2e)', border: '1px solid var(--border)' }}
          />
        ) : (
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {profile.default_cogs_pct != null ? `${profile.default_cogs_pct}%` : '—'}
          </span>
        )}
      </td>
      <td className="px-4 py-3">
        {editing ? (
          <input
            type="number" min="0" max="100" step="0.1"
            value={form.default_target_margin_pct}
            onChange={e => setForm(f => ({ ...f, default_target_margin_pct: e.target.value }))}
            className="w-20 px-2 py-1 rounded text-sm text-white"
            style={{ background: 'var(--bg-input, #1a1a2e)', border: '1px solid var(--border)' }}
          />
        ) : (
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {profile.default_target_margin_pct != null ? `${profile.default_target_margin_pct}%` : '—'}
          </span>
        )}
      </td>
      <td className="px-4 py-3 text-xs" style={{ color: 'var(--text-muted)' }}>
        {floor && editing ? (
          <span className="text-amber-400">Floor ~{floor}% of price</span>
        ) : '—'}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          {editing ? (
            <>
              <button
                onClick={handleSave}
                disabled={saving}
                className="text-xs font-medium text-emerald-400 hover:text-emerald-300 disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button onClick={() => setEditing(false)} className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Cancel
              </button>
            </>
          ) : (
            <>
              <button onClick={() => setEditing(true)} className="text-xs text-amber-400 hover:text-amber-300 font-medium">
                Edit
              </button>
              <button onClick={handleDelete} disabled={deleting} className="text-xs text-red-400/60 hover:text-red-400 disabled:opacity-50">
                ×
              </button>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}

function AddRow({ onAdd }) {
  const [form, setForm] = useState(EMPTY_ROW);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleAdd = async () => {
    if (!form.category_name.trim()) { setError('Category name is required'); return; }
    setSaving(true);
    setError('');
    try {
      await onAdd({
        category_name: form.category_name.trim(),
        default_cogs_pct: form.default_cogs_pct ? parseFloat(form.default_cogs_pct) : null,
        default_target_margin_pct: form.default_target_margin_pct ? parseFloat(form.default_target_margin_pct) : null,
      });
      setForm(EMPTY_ROW);
    } catch (e) {
      setError(e.message || 'Failed to add profile');
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr style={{ borderBottom: '1px solid var(--border)', background: 'rgba(245,158,11,0.03)' }}>
      <td className="px-4 py-3">
        <input
          type="text"
          placeholder="e.g. Footwear"
          value={form.category_name}
          onChange={e => setForm(f => ({ ...f, category_name: e.target.value }))}
          className="w-full px-2 py-1 rounded text-sm text-white"
          style={{ background: 'var(--bg-input, #1a1a2e)', border: '1px solid var(--border)' }}
          onKeyDown={e => e.key === 'Enter' && handleAdd()}
        />
        {error && <p className="text-xs text-red-400 mt-1">{error}</p>}
      </td>
      <td className="px-4 py-3">
        <input
          type="number" min="0" max="100" step="0.1" placeholder="35"
          value={form.default_cogs_pct}
          onChange={e => setForm(f => ({ ...f, default_cogs_pct: e.target.value }))}
          className="w-20 px-2 py-1 rounded text-sm text-white"
          style={{ background: 'var(--bg-input, #1a1a2e)', border: '1px solid var(--border)' }}
        />
      </td>
      <td className="px-4 py-3">
        <input
          type="number" min="0" max="100" step="0.1" placeholder="25"
          value={form.default_target_margin_pct}
          onChange={e => setForm(f => ({ ...f, default_target_margin_pct: e.target.value }))}
          className="w-20 px-2 py-1 rounded text-sm text-white"
          style={{ background: 'var(--bg-input, #1a1a2e)', border: '1px solid var(--border)' }}
        />
      </td>
      <td className="px-4 py-3" />
      <td className="px-4 py-3">
        <button
          onClick={handleAdd}
          disabled={saving}
          className="text-xs font-semibold px-3 py-1.5 rounded-lg disabled:opacity-50"
          style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b', border: '1px solid rgba(245,158,11,0.3)' }}
        >
          {saving ? 'Adding…' : '+ Add'}
        </button>
      </td>
    </tr>
  );
}

export default function CategoryDefaults() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCategoryProfiles()
      .then(setProfiles)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleAdd = async (data) => {
    const result = await api.createCategoryProfile(data);
    setProfiles(ps => [...ps, { ...data, id: result.id, created_at: new Date().toISOString() }].sort((a, b) => a.category_name.localeCompare(b.category_name)));
  };

  const handleSave = async (id, data) => {
    await api.updateCategoryProfile(id, data);
    setProfiles(ps => ps.map(p => p.id === id ? { ...p, ...data } : p));
  };

  const handleDelete = async (id) => {
    await api.deleteCategoryProfile(id);
    setProfiles(ps => ps.filter(p => p.id !== id));
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white mb-1">Margin Defaults</h1>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Set default COGS % and target margin by product category. Applied automatically
            when a product has no individual cost price set.
          </p>
        </div>

        {/* Info banner */}
        <div className="rounded-xl p-4 mb-6 flex items-start gap-3" style={{ background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.2)' }}>
          <svg className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            <span className="text-amber-400 font-medium">How it works: </span>
            When MarketIntel suggests a price for a product in "Footwear" that has no COGS set,
            it uses the Footwear default (e.g., 35% COGS, 25% target margin) to compute the floor price.
            The actual product's cost price always takes priority.
          </p>
        </div>

        {/* Table */}
        <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          {loading ? (
            <div className="p-12 text-center text-sm" style={{ color: 'var(--text-muted)' }}>Loading…</div>
          ) : (
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'rgba(255,255,255,0.03)' }}>
                  <th className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>Category</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>COGS %</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>Target margin</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>Floor preview</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                <AddRow onAdd={handleAdd} />
                {profiles.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                      No category defaults yet. Add one above.
                    </td>
                  </tr>
                )}
                {profiles.map(p => (
                  <ProfileRow key={p.id} profile={p} onSave={handleSave} onDelete={handleDelete} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </Layout>
  );
}
