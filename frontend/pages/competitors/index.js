import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
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
  const bg = { blue: 'bg-blue-50 text-blue-600', emerald: 'bg-emerald-50 text-emerald-600', gray: 'bg-gray-100 text-gray-500' }[color];
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${bg}`}>{icon}</div>
      <div>
        <p className="text-2xl font-bold text-gray-900 leading-none">{value}</p>
        <p className="text-xs text-gray-500 mt-1">{label}</p>
      </div>
    </div>
  );
}

function CompetitorCard({ competitor, onToggle, onDelete }) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Delete "${competitor.name}"? This will remove all associated data.`)) return;
    setDeleting(true);
    await onDelete(competitor.id);
  };

  return (
    <div className={`bg-white rounded-2xl border shadow-sm overflow-hidden transition-opacity ${deleting ? 'opacity-50' : ''} ${competitor.is_active ? 'border-gray-100' : 'border-gray-100 opacity-75'}`}>
      {/* Top stripe */}
      <div className={`h-1 ${competitor.is_active ? 'bg-emerald-400' : 'bg-gray-200'}`} />

      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-gray-900 truncate">{competitor.name}</h3>
            <a
              href={competitor.base_url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline mt-0.5 truncate max-w-full"
            >
              {competitor.base_url} {Ico.ext}
            </a>
          </div>
          <span className={`shrink-0 px-2.5 py-0.5 rounded-full text-xs font-medium ${competitor.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
            {competitor.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>

        {/* Type + date */}
        <div className="flex items-center gap-3 mb-4 text-xs text-gray-500">
          <span className="capitalize">{competitor.website_type || 'Custom'}</span>
          <span>·</span>
          <span>Added {new Date(competitor.created_at).toLocaleDateString()}</span>
        </div>

        {/* Selectors */}
        {(competitor.price_selector || competitor.title_selector) && (
          <div className="space-y-1.5 mb-4">
            {competitor.price_selector && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-400 w-8 shrink-0">Price</span>
                <code className="bg-gray-50 border border-gray-100 px-2 py-0.5 rounded-lg text-gray-600 truncate">{competitor.price_selector}</code>
              </div>
            )}
            {competitor.title_selector && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-400 w-8 shrink-0">Title</span>
                <code className="bg-gray-50 border border-gray-100 px-2 py-0.5 rounded-lg text-gray-600 truncate">{competitor.title_selector}</code>
              </div>
            )}
          </div>
        )}

        {/* Notes */}
        {competitor.notes && (
          <p className="text-xs text-gray-500 line-clamp-2 mb-4">{competitor.notes}</p>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-50">
          <button
            onClick={() => onToggle(competitor.id, competitor.is_active)}
            className={`text-xs font-medium transition-colors ${competitor.is_active ? 'text-gray-500 hover:text-gray-900' : 'text-emerald-600 hover:text-emerald-700'}`}
          >
            {competitor.is_active ? 'Deactivate' : 'Activate'}
          </button>
          <div className="flex items-center gap-3">
            <Link href={`/competitors/${competitor.id}/edit`} className="text-gray-400 hover:text-gray-600 transition-colors">{Ico.edit}</Link>
            <button onClick={handleDelete} disabled={deleting} className="text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50">{Ico.trash}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CompetitorsPage() {
  const [competitors, setCompetitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('All');

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
    } catch { alert('Failed to update competitor status'); }
  };

  const handleDelete = async (id) => {
    try {
      await api.deleteCompetitor(id);
      setCompetitors(cs => cs.filter(c => c.id !== id));
    } catch { alert('Failed to delete competitor'); }
  };

  const active = competitors.filter(c => c.is_active);
  const inactive = competitors.filter(c => !c.is_active);
  const filtered = tab === 'Active' ? active : tab === 'Inactive' ? inactive : competitors;

  if (loading) return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">
        <div className="grid grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-white rounded-2xl border border-gray-100 animate-pulse" />)}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <div key={i} className="h-48 bg-white rounded-2xl border border-gray-100 animate-pulse" />)}
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
            <h1 className="text-xl font-bold text-gray-900">Competitors</h1>
            <p className="text-sm text-gray-500 mt-0.5">Custom websites to monitor with CSS selectors</p>
          </div>
          <Link
            href="/competitors/add"
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors"
          >
            {Ico.plus} Add Competitor
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <StatCard label="Total" value={competitors.length} color="blue" icon={Ico.globe} />
          <StatCard label="Active" value={active.length} color="emerald" icon={Ico.check} />
          <StatCard label="Inactive" value={inactive.length} color="gray" icon={Ico.pause} />
        </div>

        {/* Filter tabs */}
        <div className="flex items-center gap-2">
          {TABS.map(t => (
            <button
              key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                tab === t ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              {t}
              {t !== 'All' && (
                <span className={`ml-1.5 text-xs ${tab === t ? 'opacity-70' : 'text-gray-400'}`}>
                  ({t === 'Active' ? active.length : inactive.length})
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Grid */}
        {filtered.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-16 text-center">
            <div className="w-14 h-14 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4 text-gray-300">{Ico.globe}</div>
            <p className="text-sm font-medium text-gray-900">
              {tab === 'All' ? 'No competitors yet' : `No ${tab.toLowerCase()} competitors`}
            </p>
            <p className="text-xs text-gray-400 mt-1 mb-5">
              {tab === 'All' ? 'Add a competitor website to start tracking prices' : 'Change the filter to see other competitors'}
            </p>
            {tab === 'All' && (
              <Link href="/competitors/add" className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors">
                {Ico.plus} Add Competitor
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {filtered.map(c => (
              <CompetitorCard key={c.id} competitor={c} onToggle={handleToggle} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
