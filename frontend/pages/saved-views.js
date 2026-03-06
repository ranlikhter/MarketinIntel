import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../components/Layout';
import { useToast } from '../components/Toast';
import api from '../lib/api';

// ─── Icons ────────────────────────────────────────────────────────────────────
const Ico = {
  bookmark: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" /></svg>,
  plus:     <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  trash:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>,
  copy:     <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>,
  play:     <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M5 3l14 9-14 9V3z" /></svg>,
  filter:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>,
};

const PRICE_POSITIONS = ['cheapest', 'mid_range', 'most_expensive'];
const COMPETITION_LEVELS = ['none', 'low', 'medium', 'high'];
const ACTIVITIES = ['price_dropped', 'new_competitor', 'out_of_stock', 'trending'];
const SORT_OPTIONS = [
  { value: 'created_at', label: 'Date Added' },
  { value: 'title', label: 'Title' },
  { value: 'my_price', label: 'My Price' },
  { value: 'opportunity_score', label: 'Opportunity Score' },
];

// ─── Create View Modal ────────────────────────────────────────────────────────
function CreateViewModal({ onClose, onCreate }) {
  const [form, setForm] = useState({
    name: '',
    icon: '',
    description: '',
    price_position: '',
    competition_level: '',
    activity: '',
    sort_by: 'created_at',
    sort_order: 'desc',
    is_default: false,
  });
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();

  const set = (key, val) => setForm((f) => ({ ...f, [key]: val }));

  async function submit(e) {
    e.preventDefault();
    if (!form.name.trim()) return;
    setLoading(true);

    const filters = {};
    if (form.price_position) filters.price_position = form.price_position;
    if (form.competition_level) filters.competition_level = form.competition_level;
    if (form.activity) filters.activity = form.activity;

    try {
      const view = await api.createSavedView({
        name: form.name.trim(),
        icon: form.icon || null,
        description: form.description || null,
        filters,
        sort_by: form.sort_by || null,
        sort_order: form.sort_order,
        is_default: form.is_default,
      });
      onCreate(view);
      onClose();
      addToast('View saved!', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to save view', 'error');
    } finally {
      setLoading(false);
    }
  }

  const EMOJIS = ['📊', '🎯', '🚨', '💰', '📈', '📉', '⚡', '🏆', '🔥', '👀', '💡', '🛒'];

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div
        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
        className="rounded-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto"
      >
        <h3 className="text-lg font-semibold text-white mb-5">Create Saved View</h3>
        <form onSubmit={submit} className="space-y-4">

          {/* Name + icon */}
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-white/70 mb-1">View Name *</label>
              <input autoFocus value={form.name} onChange={(e) => set('name', e.target.value)}
                placeholder="e.g. Problem Products"
                className="w-full glass-input rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400/50" />
            </div>
            <div className="w-28">
              <label className="block text-sm font-medium text-white/70 mb-1">Icon</label>
              <input value={form.icon} onChange={(e) => set('icon', e.target.value)}
                placeholder="🎯"
                className="w-full glass-input rounded-lg px-3 py-2 text-sm text-center focus:outline-none focus:ring-2 focus:ring-amber-400/50" />
            </div>
          </div>

          {/* Emoji picker */}
          <div className="flex flex-wrap gap-1.5">
            {EMOJIS.map((e) => (
              <button key={e} type="button" onClick={() => set('icon', e)}
                className={`w-8 h-8 rounded-lg text-base hover:bg-white/5 transition-colors ${form.icon === e ? 'bg-amber-900/40 ring-1 ring-amber-400/50' : ''}`}>
                {e}
              </button>
            ))}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1">Description (optional)</label>
            <input value={form.description} onChange={(e) => set('description', e.target.value)}
              placeholder="Products where we're most expensive and competition is high"
              className="w-full glass-input rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400/50" />
          </div>

          {/* Filters section */}
          <div className="rounded-xl p-4 space-y-3" style={{ background: 'var(--bg-surface)' }}>
            <p className="text-xs font-semibold text-white/40 uppercase tracking-wider flex items-center gap-1.5">
              {Ico.filter} Filters
            </p>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div>
                <label className="block text-xs font-medium text-white/50 mb-1">Price Position</label>
                <select value={form.price_position} onChange={(e) => set('price_position', e.target.value)}
                  className="w-full glass-input rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-400/50">
                  <option value="">Any</option>
                  {PRICE_POSITIONS.map((p) => (
                    <option key={p} value={p}>{p.replaceAll('_', ' ')}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-white/50 mb-1">Competition Level</label>
                <select value={form.competition_level} onChange={(e) => set('competition_level', e.target.value)}
                  className="w-full glass-input rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-400/50">
                  <option value="">Any</option>
                  {COMPETITION_LEVELS.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-white/50 mb-1">Activity</label>
                <select value={form.activity} onChange={(e) => set('activity', e.target.value)}
                  className="w-full glass-input rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-400/50">
                  <option value="">Any</option>
                  {ACTIVITIES.map((a) => (
                    <option key={a} value={a}>{a.replaceAll('_', ' ')}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Sort */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-white/70 mb-1">Sort By</label>
              <select value={form.sort_by} onChange={(e) => set('sort_by', e.target.value)}
                className="w-full glass-input rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400/50">
                {SORT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-white/70 mb-1">Order</label>
              <select value={form.sort_order} onChange={(e) => set('sort_order', e.target.value)}
                className="w-full glass-input rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400/50">
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </div>
          </div>

          {/* Default toggle */}
          <button type="button" onClick={() => set('is_default', !form.is_default)} className="flex items-center gap-3 cursor-pointer select-none">
            <div
              className={`w-11 h-6 rounded-full flex items-center px-0.5 transition-colors ${form.is_default ? 'bg-amber-500' : 'bg-white/20'}`}>
              <div className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${form.is_default ? 'translate-x-5' : 'translate-x-0'}`} />
            </div>
            <span className="text-sm text-white/60">Set as default view on the Products page</span>
          </button>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              style={{ border: '1px solid var(--border)' }}
              className="flex-1 px-4 py-2 text-white/60 rounded-lg text-sm font-medium hover:bg-white/5 transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={loading || !form.name.trim()}
              className="flex-1 px-4 py-2 gradient-brand text-white rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity">
              {loading ? 'Saving…' : 'Save View'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── View Card ────────────────────────────────────────────────────────────────
function ViewCard({ view, onDelete, onDuplicate }) {
  const router = useRouter();
  const { addToast } = useToast();
  const [deleting, setDeleting] = useState(false);
  const [duping, setDuping] = useState(false);

  const filters = view.filters || {};
  const filterTags = [
    filters.price_position && `Price: ${filters.price_position.replaceAll('_', ' ')}`,
    filters.competition_level && `Competition: ${filters.competition_level}`,
    filters.activity && `Activity: ${filters.activity.replaceAll('_', ' ')}`,
  ].filter(Boolean);

  function loadView() {
    const params = new URLSearchParams();
    if (filters.price_position) params.set('price_position', filters.price_position);
    if (filters.competition_level) params.set('competition_level', filters.competition_level);
    if (filters.activity) params.set('activity', filters.activity);
    if (view.sort_by) params.set('sort_by', view.sort_by);
    if (view.sort_order) params.set('sort_order', view.sort_order);
    router.push(`/products?${params.toString()}`);
  }

  async function deleteView() {
    if (!confirm(`Delete "${view.name}"?`)) return;
    setDeleting(true);
    try {
      await api.deleteSavedView(view.id);
      onDelete(view.id);
      addToast('View deleted', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to delete view', 'error');
      setDeleting(false);
    }
  }

  async function duplicate() {
    setDuping(true);
    try {
      const copy = await api.duplicateSavedView(view.id);
      onDuplicate(copy);
      addToast(`"${copy.name}" created`, 'success');
    } catch (err) {
      addToast(err.message || 'Failed to duplicate view', 'error');
    } finally {
      setDuping(false);
    }
  }

  const sortLabel = SORT_OPTIONS.find((o) => o.value === view.sort_by)?.label || view.sort_by;

  return (
    <div
      style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
      className="rounded-2xl hover:shadow-md transition-shadow p-5"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          {view.icon && (
            <span className="text-2xl shrink-0">{view.icon}</span>
          )}
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-white truncate">{view.name}</h3>
              {view.is_default && (
                <span className="shrink-0 px-1.5 py-0.5 bg-amber-900/40 text-amber-400 text-xs font-medium rounded">
                  Default
                </span>
              )}
              {view.is_shared && (
                <span className="shrink-0 px-1.5 py-0.5 bg-violet-900/40 text-violet-400 text-xs font-medium rounded">
                  Shared
                </span>
              )}
            </div>
            {view.description && (
              <p className="text-sm mt-0.5 line-clamp-2" style={{ color: 'var(--text-muted)' }}>{view.description}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button onClick={duplicate} disabled={duping} title="Duplicate"
            className="p-1.5 text-white/30 hover:text-amber-400 hover:bg-amber-900/20 rounded-lg transition-colors disabled:opacity-50">
            {Ico.copy}
          </button>
          <button onClick={deleteView} disabled={deleting} title="Delete"
            className="p-1.5 text-white/30 hover:text-red-400 hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50">
            {Ico.trash}
          </button>
        </div>
      </div>

      {/* Filter tags */}
      {filterTags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {filterTags.map((tag) => (
            <span key={tag} className="px-2 py-0.5 text-xs rounded-full" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>{tag}</span>
          ))}
        </div>
      )}

      {/* Sort */}
      {view.sort_by && (
        <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
          Sort by <span className="font-medium text-white/50">{sortLabel}</span> ({view.sort_order})
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-4 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="flex items-center gap-3 text-xs" style={{ color: 'var(--text-muted)' }}>
          <span>Used {view.use_count || 0}×</span>
          {view.last_used_at && (
            <span>· Last: {new Date(view.last_used_at).toLocaleDateString()}</span>
          )}
        </div>
        <button onClick={loadView}
          className="flex items-center gap-1.5 px-3 py-1.5 gradient-brand text-white rounded-lg text-xs font-medium hover:opacity-90 transition-opacity">
          {Ico.play} Load View
        </button>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function SavedViewsPage() {
  const [views, setViews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    api.getSavedViews()
      .then((data) => setViews(Array.isArray(data) ? data : []))
      .catch(() => addToast('Failed to load saved views', 'error'))
      .finally(() => setLoading(false));
  }, []);

  function handleCreated(view) {
    setViews((prev) => [view, ...prev]);
  }

  function handleDeleted(id) {
    setViews((prev) => prev.filter((v) => v.id !== id));
  }

  function handleDuplicated(copy) {
    setViews((prev) => [...prev, copy]);
  }

  return (
    <Layout>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Saved Views</h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
              Save your favourite filter combinations and jump back in instantly.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 gradient-brand text-white rounded-xl text-sm font-medium hover:opacity-90 transition-opacity shadow-gradient"
          >
            {Ico.plus} New View
          </button>
        </div>

        {/* Suggested starter views */}
        {!loading && views.length === 0 && (
          <div className="rounded-2xl p-6 mb-6" style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.18)' }}>
            <h3 className="font-semibold text-amber-400 mb-3">Quick-start templates</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {[
                { icon: '🚨', name: 'Problem Products', desc: 'Most expensive + high competition', filters: { price_position: 'most_expensive', competition_level: 'high' } },
                { icon: '💰', name: 'Quick Wins',       desc: 'Competitors are out of stock',      filters: { activity: 'out_of_stock' } },
                { icon: '📈', name: 'Price War Watch',  desc: 'Recent price drops detected',       filters: { activity: 'price_dropped' } },
              ].map((t) => (
                <button key={t.name}
                  onClick={async () => {
                    try {
                      const v = await api.createSavedView({ name: t.name, icon: t.icon, description: t.desc, filters: t.filters, sort_by: 'created_at', sort_order: 'desc' });
                      setViews(prev => [v, ...prev]);
                      addToast(`"${t.name}" saved!`, 'success');
                    } catch {}
                  }}
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
                  className="text-left p-3 rounded-xl hover:border-amber-400/30 hover:shadow-sm transition-all">
                  <span className="text-xl">{t.icon}</span>
                  <p className="text-sm font-semibold text-white mt-1.5">{t.name}</p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{t.desc}</p>
                  <span className="text-xs text-amber-400 font-medium mt-2 inline-block">+ Add this view</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {loading ? (
          <div className="text-center py-20" style={{ color: 'var(--text-muted)' }}>Loading…</div>
        ) : views.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4 text-white/20" style={{ background: 'var(--bg-elevated)' }}>
              {Ico.bookmark}
            </div>
            <p className="text-white/50 font-medium">No saved views yet</p>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>Create a view to save your filter and sort preferences.</p>
            <button onClick={() => setShowCreate(true)}
              className="mt-4 px-4 py-2 gradient-brand text-white rounded-xl text-sm font-medium hover:opacity-90 transition-opacity">
              Create first view
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {views.map((v) => (
              <ViewCard
                key={v.id}
                view={v}
                onDelete={handleDeleted}
                onDuplicate={handleDuplicated}
              />
            ))}
          </div>
        )}
      </div>

      {showCreate && (
        <CreateViewModal
          onClose={() => setShowCreate(false)}
          onCreate={handleCreated}
        />
      )}
    </Layout>
  );
}
