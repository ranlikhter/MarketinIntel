import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import ImportWizard from '../../components/ImportWizard';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';
import api from '../../lib/api';

const Ico = {
  xml:    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>,
  store:  <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" /></svg>,
  cart:   <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" /></svg>,
  check:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>,
  plus:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  bolt:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  shield: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
  sync:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  syncSm: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  doc:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>,
  link:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>,
  trash:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>,
  clock:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
};

const INTEGRATIONS = [
  { icon: Ico.xml,   iconBg: 'bg-orange-50 text-orange-600',   title: 'XML Feed',    desc: 'Upload a product catalog XML file. Supports Google Shopping Feed, WooCommerce exports, and custom formats.', features: ['Auto-detect format', 'Google Shopping Feed', 'WooCommerce XML', 'Custom XML formats'],   button: 'Import from XML',      btnClass: 'bg-orange-600 hover:bg-orange-700' },
  { icon: Ico.store, iconBg: 'bg-violet-50 text-violet-600',   title: 'WooCommerce', desc: 'Connect to your WooCommerce store via REST API and automatically sync all published products.',              features: ['Direct API connection', 'Bulk import', 'Filter by category', 'Sync product status'],  button: 'Connect WooCommerce', btnClass: 'bg-violet-600 hover:bg-violet-700' },
  { icon: Ico.cart,  iconBg: 'bg-emerald-50 text-emerald-600', title: 'Shopify',     desc: 'Connect to your Shopify store using the Admin API. Import products, variants, and collections.',             features: ['Admin API integration', 'Import all products', 'Variant support', 'Collection filtering'], button: 'Connect Shopify',    btnClass: 'bg-emerald-600 hover:bg-emerald-700' },
];

const FEATURES = [
  { icon: Ico.bolt,   iconBg: 'bg-blue-50 text-blue-600',      title: 'Fast Import',         desc: 'Import hundreds of products in seconds with optimised batch processing.' },
  { icon: Ico.shield, iconBg: 'bg-emerald-50 text-emerald-600', title: 'Duplicate Detection', desc: 'Automatically skips products that already exist in your catalogue.' },
  { icon: Ico.sync,   iconBg: 'bg-violet-50 text-violet-600',   title: 'Automatic Sync',      desc: 'Inventory and prices sync from connected stores every 4 hours automatically.' },
  { icon: Ico.doc,    iconBg: 'bg-orange-50 text-orange-600',   title: 'Flexible Formats',    desc: 'Support for multiple XML formats with automatic field detection.' },
];

const STEPS = [
  { n: '1', title: 'Choose Source', desc: 'Select XML, WooCommerce, or Shopify' },
  { n: '2', title: 'Configure',     desc: 'Upload file or enter API credentials' },
  { n: '3', title: 'Import',        desc: 'Products are validated and imported'  },
  { n: '4', title: 'Monitor',       desc: 'Start tracking competitor prices'     },
];

const inputCls = 'w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-shadow';

// ─── Helpers ──────────────────────────────────────────────────────────────────
function platformMeta(platform) {
  if (platform === 'shopify')     return { label: 'Shopify',     cls: 'bg-emerald-50 text-emerald-600 border-emerald-100' };
  if (platform === 'woocommerce') return { label: 'WooCommerce', cls: 'bg-violet-50  text-violet-600  border-violet-100'  };
  return { label: platform, cls: 'bg-gray-50 text-gray-600 border-gray-100' };
}

// ─── Add Connection Modal ──────────────────────────────────────────────────────
function AddConnectionModal({ isOpen, onClose, onSaved }) {
  const { addToast } = useToast();
  const [platform, setPlatform] = useState('woocommerce');
  const [form, setForm] = useState({ store_url: '', consumer_key: '', consumer_secret: '', api_key: '' });
  const [saving, setSaving] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const isWC = platform === 'woocommerce';
  const canSubmit = isWC
    ? (form.store_url && form.consumer_key && form.consumer_secret)
    : (form.store_url && form.api_key);

  async function handleSave() {
    if (!canSubmit) return;
    setSaving(true);
    try {
      const payload = isWC
        ? { platform: 'woocommerce', store_url: form.store_url, api_key: form.consumer_key, api_secret: form.consumer_secret }
        : { platform: 'shopify',     store_url: form.store_url, api_key: form.api_key };
      const conn = await api.saveStoreConnection(payload);
      onSaved(conn);
      onClose();
      addToast(`${platformMeta(conn.platform).label} connection saved`, 'success');
    } catch (err) {
      addToast(err.message || 'Failed to save connection', 'error');
    } finally {
      setSaving(false);
    }
  }

  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-base font-bold text-gray-900">Add Store Connection</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-xs text-gray-500">
            Saved credentials enable automatic inventory syncing every 4 hours and instant price push-back.
          </p>

          <div className="flex gap-2 p-1 bg-gray-100 rounded-xl">
            {[['woocommerce', 'WooCommerce'], ['shopify', 'Shopify']].map(([val, lbl]) => (
              <button key={val} onClick={() => setPlatform(val)}
                className={`flex-1 py-1.5 rounded-lg text-sm font-medium transition-colors ${platform === val ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
                {lbl}
              </button>
            ))}
          </div>

          {isWC ? (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Store URL</label>
                <input type="url" value={form.store_url} onChange={(e) => set('store_url', e.target.value)} placeholder="https://yourstore.com" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Consumer Key</label>
                <input type="text" value={form.consumer_key} onChange={(e) => set('consumer_key', e.target.value)} placeholder="ck_xxxxxxxxxxxxxxxx" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Consumer Secret</label>
                <input type="password" value={form.consumer_secret} onChange={(e) => set('consumer_secret', e.target.value)} placeholder="cs_xxxxxxxxxxxxxxxx" className={inputCls} />
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Shop URL</label>
                <input type="text" value={form.store_url} onChange={(e) => set('store_url', e.target.value)} placeholder="yourstore.myshopify.com" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Admin API Access Token</label>
                <input type="password" value={form.api_key} onChange={(e) => set('api_key', e.target.value)} placeholder="shpat_xxxxxxxxxxxxxxxx" className={inputCls} />
              </div>
            </>
          )}
        </div>

        <div className="flex items-center justify-between px-5 py-4 border-t border-gray-50">
          <button onClick={onClose} className="text-sm text-gray-500 hover:text-gray-700 font-medium">Cancel</button>
          <button onClick={handleSave} disabled={!canSubmit || saving}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
            {saving && <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>}
            Save Connection
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Connection Row ────────────────────────────────────────────────────────────
function ConnectionRow({ conn, onRemove }) {
  const { addToast } = useToast();
  const [syncing, setSyncing]   = useState(false);
  const [removing, setRemoving] = useState(false);
  const { label, cls } = platformMeta(conn.platform);

  async function sync() {
    setSyncing(true);
    try {
      await api.syncStoreInventory(conn.id);
      addToast(`Inventory sync queued for ${conn.store_url}`, 'success');
    } catch (err) {
      addToast(err.message || 'Sync failed', 'error');
    } finally {
      setSyncing(false);
    }
  }

  async function remove() {
    if (!confirm(`Remove connection to ${conn.store_url}?`)) return;
    setRemoving(true);
    try {
      await api.deleteStoreConnection(conn.id);
      onRemove(conn.id);
      addToast('Store connection removed', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to remove', 'error');
      setRemoving(false);
    }
  }

  const lastSync = conn.last_synced_at
    ? new Date(conn.last_synced_at).toLocaleString()
    : 'Never';

  return (
    <div className="flex items-center gap-4 py-3 border-b border-gray-50 last:border-0">
      <div className={`w-9 h-9 rounded-xl border flex items-center justify-center shrink-0 ${cls}`}>
        {Ico.link}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${cls}`}>{label}</span>
          <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Active
          </span>
        </div>
        <p className="text-sm font-medium text-gray-800 truncate mt-0.5">{conn.store_url}</p>
        <p className="text-xs text-gray-400 flex items-center gap-1 mt-0.5">
          <span className="inline-block">{Ico.clock}</span> Last sync: {lastSync}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <button onClick={sync} disabled={syncing}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors disabled:opacity-50">
          <span className={syncing ? 'animate-spin inline-block' : 'inline-block'}>{Ico.syncSm}</span>
          {syncing ? 'Queued' : 'Sync Now'}
        </button>
        <button onClick={remove} disabled={removing} title="Remove connection"
          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50">
          {Ico.trash}
        </button>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function IntegrationsPage() {
  const { addToast } = useToast();
  const [showWizard, setShowWizard]       = useState(false);
  const [importResult, setImportResult]   = useState(null);
  const [showConnModal, setShowConnModal] = useState(false);
  const [connections, setConnections]     = useState([]);
  const [loadingConns, setLoadingConns]   = useState(true);

  useEffect(() => {
    api.getStoreConnections()
      .then(setConnections)
      .catch(() => setConnections([]))
      .finally(() => setLoadingConns(false));
  }, []);

  return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">

        {/* Header */}
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Integrations</h1>
            <p className="text-sm text-gray-500 mt-0.5">Import products and sync inventory with your e-commerce platform</p>
          </div>
          <button onClick={() => { setShowWizard(true); setImportResult(null); }}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors">
            {Ico.plus} Start Import
          </button>
        </div>

        {/* Connected Stores */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-50">
            <div>
              <h2 className="text-sm font-semibold text-gray-900">Connected Stores</h2>
              <p className="text-xs text-gray-400 mt-0.5">Inventory syncs automatically every 4 hours. Trigger a manual sync anytime.</p>
            </div>
            <button onClick={() => setShowConnModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 hover:bg-gray-800 text-white text-xs font-medium rounded-lg transition-colors">
              {Ico.plus} Add Store
            </button>
          </div>

          <div className="px-5">
            {loadingConns ? (
              <p className="text-sm text-gray-400 py-6 text-center">Loading connections…</p>
            ) : connections.length === 0 ? (
              <div className="py-8 text-center">
                <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3 text-gray-400">
                  {Ico.link}
                </div>
                <p className="text-sm text-gray-500 font-medium">No stores connected</p>
                <p className="text-xs text-gray-400 mt-1 mb-4">
                  Add a store to enable automatic inventory sync and price push-back.
                </p>
                <button onClick={() => setShowConnModal(true)}
                  className="px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white text-sm font-medium rounded-xl transition-colors">
                  Connect your store
                </button>
              </div>
            ) : (
              connections.map((conn) => (
                <ConnectionRow key={conn.id} conn={conn}
                  onRemove={(id) => setConnections((prev) => prev.filter((c) => c.id !== id))} />
              ))
            )}
          </div>
        </div>

        {/* Import result banner */}
        {importResult && (
          <div className="bg-emerald-50 border border-emerald-100 rounded-2xl p-4 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-emerald-100 rounded-xl flex items-center justify-center text-emerald-600 shrink-0">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
              </div>
              <div>
                <p className="text-sm font-semibold text-emerald-900">
                  Import complete — {importResult.products_imported} product{importResult.products_imported !== 1 ? 's' : ''} added
                </p>
                {importResult.products_skipped > 0 && (
                  <p className="text-xs text-emerald-600">{importResult.products_skipped} duplicate{importResult.products_skipped !== 1 ? 's' : ''} skipped</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Link href="/products" className="text-xs font-medium text-emerald-700 hover:underline">View products →</Link>
              <button onClick={() => setImportResult(null)} className="text-emerald-400 hover:text-emerald-600 p-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
          </div>
        )}

        {/* Integration Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {INTEGRATIONS.map((intg, i) => (
            <div key={i} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${intg.iconBg}`}>{intg.icon}</div>
                <h3 className="text-base font-bold text-gray-900">{intg.title}</h3>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed">{intg.desc}</p>
              <ul className="space-y-1.5">
                {intg.features.map((f, j) => (
                  <li key={j} className="flex items-center gap-2 text-xs text-gray-700">
                    <span className="text-emerald-500 shrink-0">{Ico.check}</span>{f}
                  </li>
                ))}
              </ul>
              <button onClick={() => setShowWizard(true)}
                className={`mt-auto w-full py-2.5 text-white text-sm font-medium rounded-xl transition-colors ${intg.btnClass}`}>
                {intg.button}
              </button>
            </div>
          ))}
        </div>

        {/* How It Works */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-50">
            <h2 className="text-sm font-semibold text-gray-900">How It Works</h2>
          </div>
          <div className="p-5 grid grid-cols-2 lg:grid-cols-4 gap-4">
            {STEPS.map((s, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-8 h-8 bg-blue-600 text-white rounded-xl flex items-center justify-center text-sm font-bold shrink-0">{s.n}</div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{s.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Feature Highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {FEATURES.map((f, i) => (
            <div key={i} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex items-start gap-4">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${f.iconBg}`}>{f.icon}</div>
              <div>
                <p className="text-sm font-semibold text-gray-900">{f.title}</p>
                <p className="text-xs text-gray-500 mt-1">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>

      </div>

      <Modal isOpen={showWizard} onClose={() => setShowWizard(false)} title="Import Products" size="xl">
        <ImportWizard onComplete={(result) => { setShowWizard(false); if (result?.products_imported > 0) setImportResult(result); }} />
      </Modal>

      <AddConnectionModal
        isOpen={showConnModal}
        onClose={() => setShowConnModal(false)}
        onSaved={(conn) => setConnections((prev) => [conn, ...prev])}
      />
    </Layout>
  );
}
