import { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import api from '../../lib/api';

const Ico = {
  search:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>,
  check:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  pending: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  plus:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  ext:     <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>,
  spin:    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>,
};

function ConfidenceBadge({ score }) {
  const pct = Math.round((score || 0) * 100);
  const color = pct >= 80 ? 'bg-emerald-50 text-emerald-700' : pct >= 50 ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700';
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${color}`}>{pct}% match</span>;
}

function SuggestionCard({ suggestion, onApprove, onReject }) {
  const [actioning, setActioning] = useState(false);

  const act = async (fn) => {
    setActioning(true);
    await fn();
    setActioning(false);
  };

  return (
    <div className="glass-card rounded-2xl shadow-glass overflow-hidden">
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-900 truncate">{suggestion.product_title || suggestion.title}</h3>
            {suggestion.competitor_name && (
              <p className="text-xs text-slate-500 mt-0.5">{suggestion.competitor_name}</p>
            )}
          </div>
          <ConfidenceBadge score={suggestion.confidence_score} />
        </div>

        {/* URL */}
        {suggestion.url && (
          <a
            href={suggestion.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline mb-3 max-w-full truncate"
          >
            {suggestion.url} {Ico.ext}
          </a>
        )}

        {/* Price */}
        {suggestion.price != null && (
          <p className="text-sm font-bold text-slate-900 mb-1">${suggestion.price.toFixed(2)}</p>
        )}

        {/* Reason */}
        {suggestion.match_reason && (
          <p className="text-xs text-slate-400 line-clamp-2 mb-4">{suggestion.match_reason}</p>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 pt-3 border-t border-white/40">
          <button
            onClick={() => act(() => onApprove(suggestion.id))}
            disabled={actioning}
            className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold transition-colors disabled:opacity-50"
          >
            {actioning ? Ico.spin : 'Approve'}
          </button>
          <button
            onClick={() => act(() => onReject(suggestion.id))}
            disabled={actioning}
            className="flex-1 py-2 glass border border-white/60 hover:bg-white/40 text-slate-600 hover:text-slate-900 rounded-xl text-xs font-semibold transition-colors disabled:opacity-50"
          >
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}

export default function DiscoveryPage() {
  const [products, setProducts] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [keyword, setKeyword] = useState('');
  const [stats, setStats] = useState({ total: 0, pending: 0, approved: 0 });

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [productsData, suggestionsData] = await Promise.all([
        api.getProducts(),
        api.request('/api/discovery/suggestions'),
      ]);
      setProducts(productsData);
      const suggestions = suggestionsData?.suggestions || suggestionsData || [];
      setSuggestions(suggestions);
      setStats({
        total:    suggestions.length,
        pending:  suggestions.filter(s => s.status === 'pending').length,
        approved: suggestions.filter(s => s.status === 'approved').length,
      });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!selectedProductId && !keyword.trim()) return;
    setSearching(true);
    try {
      const payload = {};
      if (selectedProductId) payload.product_id = parseInt(selectedProductId);
      if (keyword.trim()) payload.keyword = keyword.trim();
      const result = await api.request('/api/discovery/search', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      const newSuggestions = result?.suggestions || result || [];
      setSuggestions(prev => {
        const existing = new Set(prev.map(s => s.id));
        return [...prev, ...newSuggestions.filter(s => !existing.has(s.id))];
      });
    } catch (e) {
      alert(e.message || 'Search failed');
    } finally {
      setSearching(false);
    }
  };

  const handleApprove = async (id) => {
    try {
      await api.request(`/api/discovery/suggestions/${id}/approve`, { method: 'POST' });
      setSuggestions(ss => ss.map(s => s.id === id ? { ...s, status: 'approved' } : s));
    } catch (e) { alert(e.message || 'Failed to approve'); }
  };

  const handleReject = async (id) => {
    try {
      await api.request(`/api/discovery/suggestions/${id}/reject`, { method: 'POST' });
      setSuggestions(ss => ss.filter(s => s.id !== id));
    } catch (e) { alert(e.message || 'Failed to reject'); }
  };

  const pending   = suggestions.filter(s => !s.status || s.status === 'pending');
  const approved  = suggestions.filter(s => s.status === 'approved');

  if (loading) return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">
        <div className="grid grid-cols-3 gap-4">{[...Array(3)].map((_, i) => <div key={i} className="h-24 glass-card rounded-2xl animate-pulse" />)}</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{[...Array(6)].map((_, i) => <div key={i} className="h-44 glass-card rounded-2xl animate-pulse" />)}</div>
      </div>
    </Layout>
  );

  return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">

        {/* Header */}
        <div>
          <h1 className="text-xl font-bold text-slate-900">Auto Discovery</h1>
          <p className="text-sm text-slate-500 mt-0.5">Find competitor listings automatically with confidence-scored matching</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <div className="stat-blue rounded-2xl shadow-gradient p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 bg-white/20 text-white">{Ico.search}</div>
            <div><p className="text-2xl font-bold text-white leading-none">{suggestions.length}</p><p className="text-xs text-white/80 mt-1">Total Suggestions</p></div>
          </div>
          <div className="stat-amber rounded-2xl shadow-gradient p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 bg-white/20 text-white">{Ico.pending}</div>
            <div><p className="text-2xl font-bold text-white leading-none">{pending.length}</p><p className="text-xs text-white/80 mt-1">Pending Review</p></div>
          </div>
          <div className="stat-emerald rounded-2xl shadow-gradient p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 bg-white/20 text-white">{Ico.check}</div>
            <div><p className="text-2xl font-bold text-white leading-none">{approved.length}</p><p className="text-xs text-white/80 mt-1">Approved</p></div>
          </div>
        </div>

        {/* Search panel */}
        <div className="glass-card rounded-2xl shadow-glass overflow-hidden">
          <div className="px-5 py-4 border-b border-white/40">
            <h2 className="text-sm font-semibold text-slate-900">Discover Competitors</h2>
            <p className="text-xs text-slate-500 mt-0.5">Search by product or keyword to find matching competitor listings</p>
          </div>
          <div className="p-5 flex flex-wrap gap-3">
            <div className="flex-1 min-w-48">
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Product</label>
              <select
                value={selectedProductId}
                onChange={e => setSelectedProductId(e.target.value)}
                className="w-full px-3 py-2.5 glass-input rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
              >
                <option value="">All products</option>
                {products.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
              </select>
            </div>
            <div className="flex-1 min-w-48">
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Keyword (optional)</label>
              <input
                value={keyword}
                onChange={e => setKeyword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
                placeholder="e.g. gaming mouse wireless"
                className="w-full px-3 py-2.5 glass-input rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleSearch}
                disabled={searching}
                className="inline-flex items-center gap-2 px-5 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90 shadow-gradient disabled:opacity-50"
              >
                {searching ? Ico.spin : Ico.search}
                {searching ? 'Searching…' : 'Search'}
              </button>
            </div>
          </div>
        </div>

        {/* Pending suggestions */}
        {pending.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-slate-700 mb-3">
              Pending Review <span className="text-slate-400 font-normal">({pending.length})</span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {pending.map(s => (
                <SuggestionCard key={s.id} suggestion={s} onApprove={handleApprove} onReject={handleReject} />
              ))}
            </div>
          </div>
        )}

        {/* Approved */}
        {approved.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-slate-700 mb-3">
              Approved <span className="text-slate-400 font-normal">({approved.length})</span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {approved.map(s => (
                <div key={s.id} className="glass-card rounded-2xl shadow-glass p-4 flex items-start gap-3 opacity-75">
                  <div className="w-8 h-8 bg-emerald-100/40 rounded-xl flex items-center justify-center text-emerald-600 shrink-0">{Ico.check}</div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">{s.product_title || s.title}</p>
                    {s.competitor_name && <p className="text-xs text-slate-500">{s.competitor_name}</p>}
                    <ConfidenceBadge score={s.confidence_score} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {suggestions.length === 0 && (
          <div className="glass-card rounded-2xl shadow-glass p-16 text-center">
            <div className="w-14 h-14 bg-white/40 rounded-2xl flex items-center justify-center mx-auto mb-4 text-slate-300">{Ico.search}</div>
            <p className="text-sm font-medium text-slate-900">No suggestions yet</p>
            <p className="text-xs text-slate-400 mt-1">Use the search panel above to discover competitor listings</p>
          </div>
        )}

      </div>
    </Layout>
  );
}
