import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { ConfirmModal } from '../../components/Modal';
import { useToast } from '../../components/Toast';
import api from '../../lib/api';

const Ico = {
  globe:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>,
  check:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  pause:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  plus:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  ext:    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>,
  trash:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>,
  edit:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>,
};

const TABS = ['All', 'Active', 'Inactive'];

function StatCard({ label, value, color, icon }) {
  const bg = {
    amber:   { background: 'rgba(245,158,11,0.15)', color: '#f59e0b' },
    emerald: { background: 'rgba(16,185,129,0.15)', color: '#10b981' },
    gray:    { background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)' },
  }[color];
  return (
    <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }} className="rounded-2xl shadow-sm p-5 flex items-center gap-4">
      <div style={{ background: bg.background, color: bg.color }} className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0">{icon}</div>
      <div>
        <p className="text-2xl font-bold text-white leading-none">{value}</p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
      </div>
    </div>
  );
}

function CompetitorCard({ competitor, onToggle, onDelete }) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    setDeleting(true);
    await onDelete(competitor.id);
  };

  return (
    <div
      style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
      className={`rounded-2xl shadow-sm overflow-hidden transition-opacity ${deleting ? 'opacity-50' : ''} ${competitor.is_active ? '' : 'opacity-75'}`}
    >
      {/* Top stripe */}
      <div className={`h-1 ${competitor.is_active ? 'bg-emerald-400' : 'bg-white/10'}`} />

      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-white truncate">{competitor.name}</h3>
            <a
              href={competitor.base_url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 mt-0.5 truncate max-w-full"
            >
              {competitor.base_url} {Ico.ext}
            </a>
          </div>
          <span
            style={competitor.is_active
              ? { background: 'rgba(16,185,129,0.15)', color: '#10b981' }
              : { background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.4)' }
            }
            className="shrink-0 px-2.5 py-0.5 rounded-full text-xs font-medium"
          >
            {competitor.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>

        {/* Type + date */}
        <div className="flex items-center gap-3 mb-4 text-xs" style={{ color: 'var(--text-muted)' }}>
          <span className="capitalize">{competitor.website_type || 'Custom'}</span>
          <span>·</span>
          <span>Added {new Date(competitor.created_at).toLocaleDateString()}</span>
        </div>

        {/* Selectors */}
        {(competitor.price_selector || competitor.title_selector) && (
          <div className="space-y-1.5 mb-4">
            {competitor.price_selector && (
              <div className="flex items-center gap-2 text-xs">
                <span className="w-8 shrink-0" style={{ color: 'var(--text-muted)' }}>Price</span>
                <code style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border)', color: 'rgba(255,255,255,0.6)' }} className="px-2 py-0.5 rounded-lg truncate">{competitor.price_selector}</code>
              </div>
            )}
            {competitor.title_selector && (
              <div className="flex items-center gap-2 text-xs">
                <span className="w-8 shrink-0" style={{ color: 'var(--text-muted)' }}>Title</span>
                <code style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border)', color: 'rgba(255,255,255,0.6)' }} className="px-2 py-0.5 rounded-lg truncate">{competitor.title_selector}</code>
              </div>
            )}
          </div>
        )}

        {/* Notes */}
        {competitor.notes && (
          <p className="text-xs line-clamp-2 mb-4" style={{ color: 'var(--text-muted)' }}>{competitor.notes}</p>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between pt-4" style={{ borderTop: '1px solid var(--border)' }}>
          <button
            onClick={() => onToggle(competitor.id, competitor.is_active)}
            className={`text-xs font-medium transition-colors ${competitor.is_active ? 'hover:text-white' : 'text-emerald-500 hover:text-emerald-400'}`}
            style={competitor.is_active ? { color: 'var(--text-muted)' } : {}}
          >
            {competitor.is_active ? 'Deactivate' : 'Activate'}
          </button>
          <div className="flex items-center gap-3">
            <Link href={`/competitors/${competitor.id}/edit`} className="transition-colors hover:text-white/60" style={{ color: 'var(--text-muted)' }}>{Ico.edit}</Link>
            <button onClick={handleDelete} disabled={deleting} className="transition-colors hover:text-red-500 disabled:opacity-50" style={{ color: 'var(--text-muted)' }}>{Ico.trash}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CompetitorsPage() {
  const { addToast } = useToast();
  const [competitors, setCompetitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('All');
  const [deleteModal, setDeleteModal] = useState({ open: false, competitor: null });

  useEffect(() => { loadCompetitors(); }, []);

  const loadCompetitors = async () => {
    try {
      setLoading(true);
      const data = await api.getCompetitors();
      setCompetitors(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (id, currentStatus) => {
    try {
      await api.toggleCompetitorStatus(id);
      setCompetitors(cs => cs.map(c => c.id === id ? { ...c, is_active: !currentStatus } : c));
    } catch { addToast('Failed to update competitor status', 'error'); }
  };

  const handleDelete = async (id) => {
    try {
      await api.deleteCompetitor(id);
      setCompetitors(cs => cs.filter(c => c.id !== id));
      addToast('Competitor removed', 'success');
    } catch { addToast('Failed to delete competitor', 'error'); }
  };

  const active = competitors.filter(c => c.is_active);
  const inactive = competitors.filter(c => !c.is_active);
  const filtered = tab === 'Active' ? active : tab === 'Inactive' ? inactive : competitors;

  if (loading) return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">
        <div className="grid grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <div key={i} className="h-24 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }} />)}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <div key={i} className="h-48 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }} />)}
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
            <h1 className="text-xl font-bold text-white">Competitors</h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>Custom websites to monitor with CSS selectors</p>
          </div>
          <Link
            href="/competitors/add"
            className="inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90"
          >
            {Ico.plus} Add Competitor
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <StatCard label="Total" value={competitors.length} color="amber" icon={Ico.globe} />
          <StatCard label="Active" value={active.length} color="emerald" icon={Ico.check} />
          <StatCard label="Inactive" value={inactive.length} color="gray" icon={Ico.pause} />
        </div>

        {/* Filter tabs */}
        <div className="flex items-center gap-2">
          {TABS.map(t => (
            <button
              key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                tab === t ? 'bg-white/10 text-white' : 'hover:bg-white/5'
              }`}
              style={tab !== t ? { color: 'var(--text-muted)' } : {}}
            >
              {t}
              {t !== 'All' && (
                <span className={`ml-1.5 text-xs ${tab === t ? 'opacity-70' : ''}`} style={tab !== t ? { color: 'var(--text-muted)' } : {}}>
                  ({t === 'Active' ? active.length : inactive.length})
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Grid */}
        {filtered.length === 0 ? (
          <div className="rounded-2xl shadow-sm p-16 text-center" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.2)' }}>{Ico.globe}</div>
            <p className="text-sm font-medium text-white">
              {tab === 'All' ? 'No competitors yet' : `No ${tab.toLowerCase()} competitors`}
            </p>
            <p className="text-xs mt-1 mb-5" style={{ color: 'var(--text-muted)' }}>
              {tab === 'All' ? 'Add a competitor website to start tracking prices' : 'Change the filter to see other competitors'}
            </p>
            {tab === 'All' && (
              <Link href="/competitors/add" className="inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90">
                {Ico.plus} Add Competitor
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {filtered.map(c => (
              <CompetitorCard key={c.id} competitor={c} onToggle={handleToggle} onDelete={() => setDeleteModal({ open: true, competitor: c })} />
            ))}
          </div>
        )}
      </div>
      <ConfirmModal
        isOpen={deleteModal.open}
        onClose={() => setDeleteModal({ open: false, competitor: null })}
        onConfirm={() => handleDelete(deleteModal.competitor?.id)}
        title="Delete Competitor"
        message={`Delete "${deleteModal.competitor?.name}"? This will remove all associated data.`}
        confirmText="Delete"
        cancelText="Cancel"
        type="danger"
      />
    </Layout>
  );
}
