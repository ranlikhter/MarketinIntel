import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import { withAuth } from '../../context/AuthContext';
import { useToast } from '../../components/Toast';
import api from '../../lib/api';

const WIDGET_ICONS = {
  bubble_chart:     '🔵',
  price_history:    '📈',
  radar:            '🕸️',
  calendar_heatmap: '📅',
  momentum_scatter: '🚀',
  kpi_cards:        '📊',
  pie_chart:        '🥧',
  bar_chart:        '📉',
};

function DashboardCard({ dashboard, onDelete, onSetDefault }) {
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div
      className="bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer group relative overflow-hidden"
      onClick={() => router.push(`/dashboards/${dashboard.id}`)}
    >
      {/* Colour accent strip */}
      <div className="h-1.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />

      <div className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-gray-900 truncate text-base">{dashboard.name}</h3>
              {dashboard.is_default && (
                <span className="flex-shrink-0 text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium">
                  Default
                </span>
              )}
            </div>
            {dashboard.description && (
              <p className="text-sm text-gray-500 truncate">{dashboard.description}</p>
            )}
          </div>

          {/* Three-dot menu */}
          <div className="relative ml-2 flex-shrink-0" onClick={e => e.stopPropagation()}>
            <button
              className="p-1.5 text-gray-400 hover:text-gray-700 rounded-lg hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={() => setMenuOpen(v => !v)}
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4z" />
              </svg>
            </button>
            {menuOpen && (
              <div className="absolute right-0 top-8 w-44 bg-white border border-gray-200 rounded-xl shadow-lg z-20 py-1">
                <button
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                  onClick={() => { setMenuOpen(false); onSetDefault(dashboard.id); }}
                >
                  Set as Default
                </button>
                <button
                  className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                  onClick={() => { setMenuOpen(false); onDelete(dashboard.id); }}
                >
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Widget count pill */}
        <div className="mt-4 flex items-center gap-2">
          <div className="flex -space-x-1">
            {Array.from({ length: Math.min(5, dashboard.widget_count) }).map((_, i) => (
              <div key={i} className="w-5 h-5 rounded bg-gradient-to-br from-indigo-400 to-purple-500 border border-white" />
            ))}
          </div>
          <span className="text-xs text-gray-500">
            {dashboard.widget_count} widget{dashboard.widget_count !== 1 ? 's' : ''}
          </span>
        </div>
      </div>
    </div>
  );
}

function CreateDashboardModal({ onClose, onCreate }) {
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    try {
      await onCreate({ name: name.trim(), description: desc.trim() || null });
      onClose();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="p-6 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">New Dashboard</h2>
          <p className="text-sm text-gray-500 mt-1">Create a canvas for your custom metrics</p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              autoFocus
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. Price War Watch"
              className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={desc}
              onChange={e => setDesc(e.target.value)}
              placeholder="Optional description…"
              rows={2}
              className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || loading}
              className="flex-1 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? 'Creating…' : 'Create Dashboard'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DashboardsPage() {
  const [dashboards, setDashboards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const router = useRouter();
  const { addToast } = useToast();

  useEffect(() => { load(); }, []);

  async function load() {
    try {
      const data = await api.getDashboards();
      setDashboards(data);
    } catch (e) {
      addToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(data) {
    try {
      const created = await api.createDashboard(data);
      router.push(`/dashboards/${created.id}`);
    } catch (e) {
      addToast(e.message, 'error');
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this dashboard?')) return;
    try {
      await api.deleteDashboard(id);
      setDashboards(ds => ds.filter(d => d.id !== id));
      addToast('Dashboard deleted', 'success');
    } catch (e) {
      addToast(e.message, 'error');
    }
  }

  async function handleSetDefault(id) {
    try {
      await api.updateDashboard(id, { is_default: true });
      setDashboards(ds => ds.map(d => ({ ...d, is_default: d.id === id })));
      addToast('Default dashboard updated', 'success');
    } catch (e) {
      addToast(e.message, 'error');
    }
  }

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Custom Dashboards</h1>
            <p className="text-gray-500 mt-1 text-sm">
              Build your own views from any metric — drag widgets, pick chart types, configure data sources
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium hover:bg-indigo-700 shadow-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Dashboard
          </button>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1,2,3].map(i => (
              <div key={i} className="bg-gray-100 rounded-2xl h-36 animate-pulse" />
            ))}
          </div>
        ) : dashboards.length === 0 ? (
          <div className="text-center py-24 border-2 border-dashed border-gray-200 rounded-2xl">
            <div className="text-5xl mb-4">📊</div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">No dashboards yet</h3>
            <p className="text-gray-500 text-sm mb-6 max-w-sm mx-auto">
              Create your first dashboard and add charts for prices, competitor positioning, listing quality, and more.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="bg-indigo-600 text-white px-6 py-2.5 rounded-xl text-sm font-medium hover:bg-indigo-700"
            >
              Create Your First Dashboard
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {dashboards.map(d => (
              <DashboardCard
                key={d.id}
                dashboard={d}
                onDelete={handleDelete}
                onSetDefault={handleSetDefault}
              />
            ))}
            {/* Add new card */}
            <button
              onClick={() => setShowCreate(true)}
              className="border-2 border-dashed border-gray-200 rounded-2xl h-36 flex flex-col items-center justify-center gap-2 text-gray-400 hover:border-indigo-400 hover:text-indigo-500 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
              </svg>
              <span className="text-sm font-medium">New Dashboard</span>
            </button>
          </div>
        )}
      </div>

      {showCreate && (
        <CreateDashboardModal onClose={() => setShowCreate(false)} onCreate={handleCreate} />
      )}
    </Layout>
  );
}

export default withAuth(DashboardsPage);
