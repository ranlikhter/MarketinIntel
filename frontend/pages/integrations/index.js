import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import ImportWizard from '../../components/ImportWizard';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';

const CONN_KEY = 'marketintel_store_connection';

const Ico = {
  xml:      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>,
  store:    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" /></svg>,
  cart:     <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" /></svg>,
  check:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>,
  plus:     <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  bolt:     <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  shield:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
  sync:     <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  doc:      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>,
  link:     <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>,
};

const INTEGRATIONS = [
  {
    icon: Ico.xml,
    iconBg: 'bg-orange-50 text-orange-600',
    title: 'XML Feed',
    desc: 'Upload a product catalog XML file. Supports Google Shopping Feed, WooCommerce exports, and custom formats.',
    features: ['Auto-detect format', 'Google Shopping Feed', 'WooCommerce XML', 'Custom XML formats'],
    button: 'Import from XML',
    btnClass: 'bg-orange-600 hover:bg-orange-700',
  },
  {
    icon: Ico.store,
    iconBg: 'bg-violet-50 text-violet-600',
    title: 'WooCommerce',
    desc: 'Connect to your WooCommerce store via REST API and automatically sync all published products.',
    features: ['Direct API connection', 'Bulk import', 'Filter by category', 'Sync product status'],
    button: 'Connect WooCommerce',
    btnClass: 'bg-violet-600 hover:bg-violet-700',
  },
  {
    icon: Ico.cart,
    iconBg: 'bg-emerald-50 text-emerald-600',
    title: 'Shopify',
    desc: 'Connect to your Shopify store using the Admin API. Import products, variants, and collections.',
    features: ['Admin API integration', 'Import all products', 'Variant support', 'Collection filtering'],
    button: 'Connect Shopify',
    btnClass: 'bg-emerald-600 hover:bg-emerald-700',
  },
];

const FEATURES = [
  { icon: Ico.bolt,   iconBg: 'bg-blue-50 text-blue-600',    title: 'Fast Import',          desc: 'Import hundreds of products in seconds with optimised batch processing.' },
  { icon: Ico.shield, iconBg: 'bg-emerald-50 text-emerald-600', title: 'Duplicate Detection', desc: 'Automatically skips products that already exist in your catalogue.' },
  { icon: Ico.sync,   iconBg: 'bg-violet-50 text-violet-600',  title: 'Automatic Sync',      desc: 'Keep products up-to-date with scheduled imports (coming soon).' },
  { icon: Ico.doc,    iconBg: 'bg-orange-50 text-orange-600',  title: 'Flexible Formats',    desc: 'Support for multiple XML formats with automatic field detection.' },
];

const STEPS = [
  { n: '1', title: 'Choose Source',  desc: 'Select XML, WooCommerce, or Shopify' },
  { n: '2', title: 'Configure',      desc: 'Upload file or enter API credentials' },
  { n: '3', title: 'Import',         desc: 'Products are validated and imported' },
  { n: '4', title: 'Monitor',        desc: 'Start tracking competitor prices' },
];

const inputCls = 'w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-shadow';

// ─── Save Connection Modal ────────────────────────────────────────────────────
function SaveConnectionModal({ isOpen, onClose, onSave }) {
  const [connType, setConnType] = useState('woocommerce');
  const [form, setForm] = useState({
    store_url: '', consumer_key: '', consumer_secret: '',
    shop_url: '', access_token: '',
  });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSave = () => {
    if (connType === 'woocommerce') {
      if (!form.store_url || !form.consumer_key || !form.consumer_secret) return;
      onSave({
        type: 'woocommerce',
        label: form.store_url,
        credentials: {
          store_url: form.store_url,
          consumer_key: form.consumer_key,
          consumer_secret: form.consumer_secret,
        },
      });
    } else {
      if (!form.shop_url || !form.access_token) return;
      onSave({
        type: 'shopify',
        label: form.shop_url,
        credentials: {
          shop_url: form.shop_url,
          access_token: form.access_token,
        },
      });
    }
  };

  if (!isOpen) return null;

  const wc = connType === 'woocommerce';

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-base font-bold text-gray-900">Save Store Connection</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-xs text-gray-500">
            Saved credentials let you push updated prices directly to your store whenever you change a product price in MarketIntel.
          </p>

          {/* Type tabs */}
          <div className="flex gap-2 p-1 bg-gray-100 rounded-xl">
            {[['woocommerce', 'WooCommerce'], ['shopify', 'Shopify']].map(([val, lbl]) => (
              <button
                key={val}
                onClick={() => setConnType(val)}
                className={`flex-1 py-1.5 rounded-lg text-sm font-medium transition-colors ${connType === val ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
              >
                {lbl}
              </button>
            ))}
          </div>

          {wc ? (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Store URL</label>
                <input type="url" value={form.store_url} onChange={e => set('store_url', e.target.value)}
                  placeholder="https://yourstore.com" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Consumer Key</label>
                <input type="text" value={form.consumer_key} onChange={e => set('consumer_key', e.target.value)}
                  placeholder="ck_xxxxxxxxxxxxxxxx" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Consumer Secret</label>
                <input type="password" value={form.consumer_secret} onChange={e => set('consumer_secret', e.target.value)}
                  placeholder="cs_xxxxxxxxxxxxxxxx" className={inputCls} />
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Shop URL</label>
                <input type="text" value={form.shop_url} onChange={e => set('shop_url', e.target.value)}
                  placeholder="yourstore.myshopify.com" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Admin API Access Token</label>
                <input type="password" value={form.access_token} onChange={e => set('access_token', e.target.value)}
                  placeholder="shpat_xxxxxxxxxxxxxxxx" className={inputCls} />
              </div>
            </>
          )}

          <p className="text-[11px] text-amber-600 bg-amber-50 border border-amber-100 rounded-xl px-3 py-2">
            Credentials are stored locally in your browser only and never sent to our servers except when syncing prices.
          </p>
        </div>

        <div className="flex items-center justify-between px-5 py-4 border-t border-gray-50">
          <button onClick={onClose} className="text-sm text-gray-500 hover:text-gray-700 font-medium">Cancel</button>
          <button
            onClick={handleSave}
            disabled={wc ? (!form.store_url || !form.consumer_key || !form.consumer_secret) : (!form.shop_url || !form.access_token)}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Save Connection
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function IntegrationsPage() {
  const { addToast } = useToast();
  const [showWizard, setShowWizard]     = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [savedConn, setSavedConn]       = useState(null);
  const [showConnModal, setShowConnModal] = useState(false);

  // Load saved connection from localStorage
  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(CONN_KEY) || 'null');
      if (stored) setSavedConn(stored);
    } catch {}
  }, []);

  const handleSaveConn = (conn) => {
    localStorage.setItem(CONN_KEY, JSON.stringify(conn));
    setSavedConn(conn);
    setShowConnModal(false);
    addToast(`${conn.type === 'woocommerce' ? 'WooCommerce' : 'Shopify'} connection saved`, 'success');
  };

  const handleDisconnect = () => {
    localStorage.removeItem(CONN_KEY);
    setSavedConn(null);
    addToast('Store connection removed', 'success');
  };

  const storeLabel = savedConn?.type === 'woocommerce' ? 'WooCommerce' : 'Shopify';
  const storeBg    = savedConn?.type === 'woocommerce' ? 'bg-violet-50 text-violet-600 border-violet-100' : 'bg-emerald-50 text-emerald-600 border-emerald-100';

  return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">

        {/* Header */}
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Integrations</h1>
            <p className="text-sm text-gray-500 mt-0.5">Import products and sync prices with your e-commerce platform</p>
          </div>
          <button
            onClick={() => { setShowWizard(true); setImportResult(null); }}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors"
          >
            {Ico.plus} Start Import
          </button>
        </div>

        {/* Active Store Connection */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <div className={`w-10 h-10 rounded-xl border flex items-center justify-center shrink-0 ${savedConn ? storeBg : 'bg-gray-50 text-gray-400 border-gray-100'}`}>
                {Ico.link}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-gray-900">
                  {savedConn ? `${storeLabel} Connected` : 'No Active Store Connection'}
                </p>
                {savedConn ? (
                  <p className="text-xs text-gray-500 truncate mt-0.5">{savedConn.label}</p>
                ) : (
                  <p className="text-xs text-gray-400 mt-0.5">
                    Save credentials to push price changes directly to your store
                  </p>
                )}
              </div>
            </div>
            <div className="shrink-0 flex items-center gap-2">
              {savedConn ? (
                <>
                  <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    Active
                  </span>
                  <button
                    onClick={() => setShowConnModal(true)}
                    className="px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Replace
                  </button>
                  <button
                    onClick={handleDisconnect}
                    className="px-3 py-1.5 text-xs font-medium text-red-500 border border-red-100 rounded-lg hover:bg-red-50 transition-colors"
                  >
                    Disconnect
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setShowConnModal(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white text-sm font-medium rounded-xl transition-colors"
                >
                  {Ico.link} Save Connection
                </button>
              )}
            </div>
          </div>

          {savedConn && (
            <div className="mt-4 pt-4 border-t border-gray-50">
              <p className="text-xs text-gray-500 flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                Price changes you make in MarketIntel will automatically sync to your {storeLabel} store. Products are matched by SKU.
              </p>
            </div>
          )}
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
              <Link href="/products" className="text-xs font-medium text-emerald-700 hover:underline">
                View products →
              </Link>
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
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${intg.iconBg}`}>
                  {intg.icon}
                </div>
                <h3 className="text-base font-bold text-gray-900">{intg.title}</h3>
              </div>

              <p className="text-xs text-gray-500 leading-relaxed">{intg.desc}</p>

              <ul className="space-y-1.5">
                {intg.features.map((f, j) => (
                  <li key={j} className="flex items-center gap-2 text-xs text-gray-700">
                    <span className="text-emerald-500 shrink-0">{Ico.check}</span>
                    {f}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => setShowWizard(true)}
                className={`mt-auto w-full py-2.5 text-white text-sm font-medium rounded-xl transition-colors ${intg.btnClass}`}
              >
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
                <div className="w-8 h-8 bg-blue-600 text-white rounded-xl flex items-center justify-center text-sm font-bold shrink-0">
                  {s.n}
                </div>
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

      {/* Import Wizard Modal */}
      <Modal isOpen={showWizard} onClose={() => setShowWizard(false)} title="Import Products" size="xl">
        <ImportWizard
          onComplete={(result) => {
            setShowWizard(false);
            if (result?.products_imported > 0) setImportResult(result);
          }}
        />
      </Modal>

      {/* Save Connection Modal */}
      <SaveConnectionModal
        isOpen={showConnModal}
        onClose={() => setShowConnModal(false)}
        onSave={handleSaveConn}
      />
    </Layout>
  );
}
