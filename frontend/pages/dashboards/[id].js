import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import { withAuth } from '../../context/AuthContext';
import { useToast } from '../../components/Toast';
import DashboardGrid from '../../components/dashboard/DashboardGrid';
import WidgetGallery from '../../components/dashboard/WidgetGallery';
import WidgetConfigPanel from '../../components/dashboard/WidgetConfigPanel';
import api from '../../lib/api';

// Debounce helper
function debounce(fn, ms) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

function DashboardPage() {
  const router = useRouter();
  const { id } = router.query;
  const { addToast } = useToast();

  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [showGallery, setShowGallery] = useState(false);
  const [configWidget, setConfigWidget] = useState(null);

  // Per-widget data, loading flags, and error states
  const [widgetData, setWidgetData] = useState({});
  const [widgetLoading, setWidgetLoading] = useState({});
  const [widgetErrors, setWidgetErrors] = useState({});

  // Dashboard name editing
  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState('');
  const nameInputRef = useRef(null);

  useEffect(() => {
    if (!id) return;
    loadDashboard();
  }, [id]);

  async function loadDashboard() {
    try {
      const data = await api.getDashboard(id);
      setDashboard(data);
      setNameValue(data.name);
      // Load data for all widgets
      data.widgets.forEach(w => fetchWidgetData(w));
    } catch (e) {
      addToast(e.message, 'error');
      router.push('/dashboards');
    } finally {
      setLoading(false);
    }
  }

  async function fetchWidgetData(widget) {
    const cfg = widget.config || {};
    if (!cfg.product_id) return;

    setWidgetLoading(prev => ({ ...prev, [widget.id]: true }));
    setWidgetErrors(prev => ({ ...prev, [widget.id]: null }));
    try {
      const data = await api.getWidgetData(widget.widget_type, {
        product_id: cfg.product_id,
        days: cfg.days || 30,
        metric: cfg.metric || 'price',
        color_scheme: cfg.color_scheme || 'rainbow',
        pie_metric: cfg.pie_metric || 'fulfillment_type',
        competitors: cfg.competitors?.join(',') || undefined,
      });
      setWidgetData(prev => ({ ...prev, [widget.id]: data }));
    } catch (e) {
      setWidgetErrors(prev => ({ ...prev, [widget.id]: e.message }));
    } finally {
      setWidgetLoading(prev => ({ ...prev, [widget.id]: false }));
    }
  }

  async function handleAddWidget(widgetDef) {
    setShowGallery(false);
    try {
      const updated = await api.addWidget(id, widgetDef);
      setDashboard(d => ({ ...d, widgets: [...d.widgets, updated] }));
      fetchWidgetData(updated);
      addToast('Widget added', 'success');
    } catch (e) {
      addToast(e.message, 'error');
    }
  }

  async function handleUpdateWidget(widgetId, changes) {
    try {
      const updated = await api.updateWidget(id, widgetId, changes);
      setDashboard(d => ({
        ...d,
        widgets: d.widgets.map(w => w.id === widgetId ? updated : w),
      }));
      setConfigWidget(updated);
      fetchWidgetData(updated);
      addToast('Widget updated', 'success');
    } catch (e) {
      addToast(e.message, 'error');
    }
  }

  async function handleDeleteWidget(widgetId) {
    if (!confirm('Remove this widget?')) return;
    try {
      await api.deleteWidget(id, widgetId);
      setDashboard(d => ({ ...d, widgets: d.widgets.filter(w => w.id !== widgetId) }));
      setConfigWidget(null);
      addToast('Widget removed', 'success');
    } catch (e) {
      addToast(e.message, 'error');
    }
  }

  // Debounced layout save — fires 600ms after last drag drop
  const saveLayout = useCallback(
    debounce(async (layout) => {
      try {
        await api.saveDashboardLayout(id, layout);
      } catch (e) {
        addToast('Failed to save layout', 'error');
      }
    }, 600),
    [id]
  );

  async function handleSaveName() {
    if (!nameValue.trim() || nameValue === dashboard.name) {
      setEditingName(false);
      return;
    }
    try {
      await api.updateDashboard(id, { name: nameValue.trim() });
      setDashboard(d => ({ ...d, name: nameValue.trim() }));
    } catch (e) {
      addToast(e.message, 'error');
    } finally {
      setEditingName(false);
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </Layout>
    );
  }

  if (!dashboard) return null;

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50">
        {/* Top bar */}
        <div className="sticky top-0 z-30 bg-white border-b border-gray-200 px-6 py-3">
          <div className="max-w-screen-xl mx-auto flex items-center gap-4">
            {/* Back */}
            <button
              onClick={() => router.push('/dashboards')}
              className="text-gray-400 hover:text-gray-700 p-1.5 rounded-lg hover:bg-gray-100 flex-shrink-0"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>

            {/* Editable dashboard name */}
            <div className="flex items-center gap-2 flex-1 min-w-0">
              {editingName ? (
                <input
                  ref={nameInputRef}
                  value={nameValue}
                  onChange={e => setNameValue(e.target.value)}
                  onBlur={handleSaveName}
                  onKeyDown={e => { if (e.key === 'Enter') nameInputRef.current?.blur(); if (e.key === 'Escape') { setNameValue(dashboard.name); setEditingName(false); } }}
                  autoFocus
                  className="text-xl font-bold text-gray-900 bg-transparent border-b-2 border-indigo-500 outline-none min-w-0 flex-1"
                />
              ) : (
                <button
                  onClick={() => setEditingName(true)}
                  className="text-xl font-bold text-gray-900 hover:text-indigo-600 truncate text-left"
                >
                  {dashboard.name}
                </button>
              )}
              {dashboard.is_default && (
                <span className="flex-shrink-0 text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium">Default</span>
              )}
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 flex-shrink-0">
              {/* Refresh all */}
              <button
                onClick={() => dashboard.widgets.forEach(fetchWidgetData)}
                className="text-gray-500 hover:text-gray-800 p-2 rounded-lg hover:bg-gray-100"
                title="Refresh all widgets"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>

              {/* Edit toggle */}
              <button
                onClick={() => { setIsEditing(v => !v); setConfigWidget(null); }}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                  isEditing
                    ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                    : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                {isEditing ? 'Done Editing' : 'Edit Layout'}
              </button>

              {/* Add widget (only in edit mode) */}
              {isEditing && (
                <button
                  onClick={() => setShowGallery(true)}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium bg-green-600 text-white hover:bg-green-700"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add Widget
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Canvas */}
        <div className="max-w-screen-xl mx-auto px-4 py-6">
          {dashboard.widgets.length === 0 ? (
            <div
              className="border-2 border-dashed border-gray-200 rounded-2xl flex flex-col items-center justify-center py-32 gap-4 cursor-pointer hover:border-indigo-400 transition-colors"
              onClick={() => { setIsEditing(true); setShowGallery(true); }}
            >
              <div className="text-5xl">✨</div>
              <h3 className="text-lg font-semibold text-gray-600">This dashboard is empty</h3>
              <p className="text-sm text-gray-400 max-w-xs text-center">
                Click to add your first widget — bubble charts, price history, KPI cards and more
              </p>
              <button className="mt-2 bg-indigo-600 text-white px-6 py-2.5 rounded-xl text-sm font-medium hover:bg-indigo-700">
                Add First Widget
              </button>
            </div>
          ) : (
            <DashboardGrid
              widgets={dashboard.widgets}
              widgetData={widgetData}
              widgetLoading={widgetLoading}
              widgetErrors={widgetErrors}
              isEditing={isEditing}
              onEditWidget={setConfigWidget}
              onLayoutChange={saveLayout}
            />
          )}
        </div>
      </div>

      {/* Modals / panels */}
      {showGallery && (
        <WidgetGallery
          onAdd={handleAddWidget}
          onClose={() => setShowGallery(false)}
        />
      )}

      {configWidget && (
        <WidgetConfigPanel
          widget={configWidget}
          onSave={handleUpdateWidget}
          onDelete={handleDeleteWidget}
          onClose={() => setConfigWidget(null)}
        />
      )}
    </Layout>
  );
}

export default withAuth(DashboardPage);
