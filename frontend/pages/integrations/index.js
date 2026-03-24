import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import ImportWizard from '../../components/ImportWizard';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';
import api from '../../lib/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  { icon: Ico.xml,   iconBg: { background: 'rgba(234,88,12,0.15)', color: '#f97316' },   title: 'XML Feed',    desc: 'Upload a product catalog XML file. Supports Google Shopping Feed, WooCommerce exports, and custom formats.', features: ['Auto-detect format', 'Google Shopping Feed', 'WooCommerce XML', 'Custom XML formats'],   button: 'Import from XML',      btnClass: 'bg-orange-600 hover:bg-orange-700' },
  { icon: Ico.store, iconBg: { background: 'rgba(124,58,237,0.15)', color: '#8b5cf6' },  title: 'WooCommerce', desc: 'Connect to your WooCommerce store via REST API and automatically sync all published products.',              features: ['Direct API connection', 'Bulk import', 'Filter by category', 'Sync product status'],  button: 'Connect WooCommerce', btnClass: 'bg-violet-600 hover:bg-violet-700' },
  { icon: Ico.cart,  iconBg: { background: 'rgba(16,185,129,0.15)', color: '#10b981' },  title: 'Shopify',     desc: 'Connect to your Shopify store using the Admin API. Import products, variants, and collections.',             features: ['Admin API integration', 'Import all products', 'Variant support', 'Collection filtering'], button: 'Connect Shopify',    btnClass: 'bg-emerald-600 hover:bg-emerald-700' },
];

const FEATURES = [
  { icon: Ico.bolt,   iconBg: { background: 'rgba(245,158,11,0.15)', color: '#f59e0b' },  title: 'Fast Import',         desc: 'Import hundreds of products in seconds with optimised batch processing.' },
  { icon: Ico.shield, iconBg: { background: 'rgba(16,185,129,0.15)', color: '#10b981' },  title: 'Duplicate Detection', desc: 'Automatically skips products that already exist in your catalogue.' },
  { icon: Ico.sync,   iconBg: { background: 'rgba(124,58,237,0.15)', color: '#8b5cf6' },  title: 'Automatic Sync',      desc: 'Inventory and prices sync from connected stores every 4 hours automatically.' },
  { icon: Ico.doc,    iconBg: { background: 'rgba(234,88,12,0.15)', color: '#f97316' },   title: 'Flexible Formats',    desc: 'Support for multiple XML formats with automatic field detection.' },
];

const STEPS = [
  { n: '1', title: 'Choose Source', desc: 'Select XML, WooCommerce, or Shopify' },
  { n: '2', title: 'Configure',     desc: 'Upload file or enter API credentials' },
  { n: '3', title: 'Import',        desc: 'Products are validated and imported'  },
  { n: '4', title: 'Monitor',       desc: 'Start tracking competitor prices'     },
];

const inputCls = 'w-full px-3.5 py-2.5 rounded-xl text-sm placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-amber-500/20 transition-shadow glass-input';

// ─── Helpers ──────────────────────────────────────────────────────────────────
function platformMeta(platform) {
  if (platform === 'shopify')     return { label: 'Shopify',     style: { background: 'rgba(16,185,129,0.15)', color: '#10b981', borderColor: 'rgba(16,185,129,0.3)' } };
  if (platform === 'woocommerce') return { label: 'WooCommerce', style: { background: 'rgba(124,58,237,0.15)', color: '#8b5cf6', borderColor: 'rgba(124,58,237,0.3)' } };
  return { label: platform, style: { background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.6)', borderColor: 'var(--border)' } };
}

// ─── Add Connection Modal ──────────────────────────────────────────────────────
function AddConnectionModal({ isOpen, onClose, onSaved }) {
  const { addToast } = useToast();
  const [platform, setPlatform] = useState('shopify');
  const [form, setForm] = useState({ store_url: '', consumer_key: '', consumer_secret: '', api_key: '' });
  const [saving, setSaving] = useState(false);
  const [oauthConnecting, setOauthConnecting] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const isWC = platform === 'woocommerce';
  const canSubmitWC = form.store_url && form.consumer_key && form.consumer_secret;
  const canOAuth = !!form.store_url;

  // WooCommerce — manual save
  async function handleSaveWC() {
    if (!canSubmitWC) return;
    setSaving(true);
    try {
      const payload = { platform: 'woocommerce', store_url: form.store_url, api_key: form.consumer_key, api_secret: form.consumer_secret };
      const conn = await api.saveStoreConnection(payload);
      onSaved(conn);
      onClose();
      addToast('WooCommerce connection saved', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to save connection', 'error');
    } finally {
      setSaving(false);
    }
  }

  // Shopify — OAuth redirect
  async function handleShopifyOAuth() {
    if (!canOAuth) return;
    setOauthConnecting(true);
    try {
      const token = typeof window !== 'undefined'
        ? (localStorage.getItem('access_token') || '')
        : '';
      const res = await fetch(
        `${API_URL}/api/integrations/shopify/oauth/start?shop=${encodeURIComponent(form.store_url)}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to start Shopify OAuth');
      }
      const { auth_url } = await res.json();
      window.location.href = auth_url;
    } catch (err) {
      addToast(err.message, 'error');
      setOauthConnecting(false);
    }
  }

  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="rounded-2xl shadow-xl w-full max-w-md" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
          <h2 className="text-base font-bold text-white">Add Store Connection</h2>
          <button onClick={onClose} className="hover:text-white p-1 transition-colors" style={{ color: 'var(--text-muted)' }}>
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Saved connections enable automatic inventory syncing every 4 hours and instant price push-back.
          </p>

          {/* Platform tabs */}
          <div className="flex gap-2 p-1 rounded-xl" style={{ background: 'rgba(255,255,255,0.06)' }}>
            {[['shopify', 'Shopify'], ['woocommerce', 'WooCommerce']].map(([val, lbl]) => (
              <button key={val} onClick={() => setPlatform(val)}
                className={`flex-1 py-1.5 rounded-lg text-sm font-medium transition-colors ${platform === val ? 'bg-white/10 text-white shadow-sm' : 'hover:text-white'}`}
                style={platform !== val ? { color: 'var(--text-muted)' } : {}}>
                {lbl}
              </button>
            ))}
          </div>

          {/* Shopify — One-Click OAuth */}
          {!isWC && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-white/70 mb-1.5">Shop URL</label>
                <input type="text" value={form.store_url} onChange={(e) => set('store_url', e.target.value)}
                  placeholder="yourstore.myshopify.com" className={inputCls} />
              </div>
              <button
                onClick={handleShopifyOAuth}
                disabled={oauthConnecting || !canOAuth}
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 text-white text-sm font-semibold rounded-xl transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: 'linear-gradient(135deg, #96bf48 0%, #5c8a1e 100%)' }}
              >
                {oauthConnecting ? (
                  <>
                    <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                    Redirecting…
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M15.337 2.094c-.07-.303-.344-.516-.653-.516h-.01c-.266 0-.5.157-.612.405l-.65 1.498A5.978 5.978 0 0012 3.375a5.978 5.978 0 00-1.412.106l-.65-1.498a.672.672 0 00-.612-.405h-.01c-.309 0-.583.213-.653.516L7.5 7.5H4.875A.875.875 0 004 8.375v.25c0 .276.101.527.267.72l1.608 9.28A1.75 1.75 0 007.594 20h8.812a1.75 1.75 0 001.719-1.375l1.608-9.28A1.12 1.12 0 0020 8.625v-.25A.875.875 0 0019.125 7.5H16.5l-1.163-5.406zM12 5.25c.357 0 .703.036 1.037.103l-.762 1.76a.375.375 0 00.344.512h2.256l.914 4.25H8.211l.914-4.25h2.256a.375.375 0 00.344-.512l-.762-1.76A5.28 5.28 0 0112 5.25z"/></svg>
                    Connect with Shopify
                  </>
                )}
              </button>
              <p className="text-xs text-center" style={{ color: 'var(--text-muted)' }}>
                You'll be redirected to Shopify to authorize access — no tokens to copy.
              </p>
            </div>
          )}

          {/* WooCommerce — manual keys */}
          {isWC && (
            <>
              <div>
                <label className="block text-xs font-medium text-white/70 mb-1.5">Store URL</label>
                <input type="url" value={form.store_url} onChange={(e) => set('store_url', e.target.value)} placeholder="https://yourstore.com" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-white/70 mb-1.5">Consumer Key</label>
                <input type="text" value={form.consumer_key} onChange={(e) => set('consumer_key', e.target.value)} placeholder="ck_xxxxxxxxxxxxxxxx" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-white/70 mb-1.5">Consumer Secret</label>
                <input type="password" value={form.consumer_secret} onChange={(e) => set('consumer_secret', e.target.value)} placeholder="cs_xxxxxxxxxxxxxxxx" className={inputCls} />
              </div>
            </>
          )}
        </div>

        {/* Footer — only show Save button for WooCommerce; Shopify uses OAuth above */}
        {isWC && (
          <div className="flex items-center justify-between px-5 py-4" style={{ borderTop: '1px solid var(--border)' }}>
            <button onClick={onClose} className="text-sm font-medium hover:text-white transition-colors" style={{ color: 'var(--text-muted)' }}>Cancel</button>
            <button onClick={handleSaveWC} disabled={!canSubmitWC || saving}
              className="px-5 py-2.5 gradient-brand text-white text-sm font-semibold rounded-xl transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
              {saving && <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>}
              Save Connection
            </button>
          </div>
        )}
        {!isWC && (
          <div className="flex justify-start px-5 py-4" style={{ borderTop: '1px solid var(--border)' }}>
            <button onClick={onClose} className="text-sm font-medium hover:text-white transition-colors" style={{ color: 'var(--text-muted)' }}>Cancel</button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Connection Row ────────────────────────────────────────────────────────────
function ConnectionRow({ conn, onRemove }) {
  const { addToast } = useToast();
  const [syncing, setSyncing]   = useState(false);
  const [removing, setRemoving] = useState(false);
  const { label, style } = platformMeta(conn.platform);

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
    <div className="flex items-center gap-4 py-3 last:border-0" style={{ borderBottom: '1px solid var(--border)' }}>
      <div className="w-9 h-9 rounded-xl border flex items-center justify-center shrink-0" style={{ ...style, borderColor: style.borderColor }}>
        {Ico.link}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded-full text-xs font-medium border" style={{ ...style, borderColor: style.borderColor }}>{label}</span>
          <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium" style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981' }}>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Active
          </span>
        </div>
        <p className="text-sm font-medium text-white truncate mt-0.5">{conn.store_url}</p>
        <p className="text-xs flex items-center gap-1 mt-0.5" style={{ color: 'var(--text-muted)' }}>
          <span className="inline-block">{Ico.clock}</span> Last sync: {lastSync}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <button onClick={sync} disabled={syncing}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors disabled:opacity-50 text-amber-400 hover:bg-white/5"
          style={{ border: '1px solid rgba(245,158,11,0.3)' }}>
          <span className={syncing ? 'animate-spin inline-block' : 'inline-block'}>{Ico.syncSm}</span>
          {syncing ? 'Queued' : 'Sync Now'}
        </button>
        <button onClick={remove} disabled={removing} title="Remove connection"
          className="p-1.5 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50" style={{ color: 'var(--text-muted)' }}>
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
            <h1 className="text-xl font-bold text-white">Integrations</h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>Import products and sync inventory with your e-commerce platform</p>
          </div>
          <button onClick={() => { setShowWizard(true); setImportResult(null); }}
            className="inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90">
            {Ico.plus} Start Import
          </button>
        </div>

        {/* Connected Stores */}
        <div className="rounded-2xl shadow-sm overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <div>
              <h2 className="text-sm font-semibold text-white">Connected Stores</h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Inventory syncs automatically every 4 hours. Trigger a manual sync anytime.</p>
            </div>
            <button onClick={() => setShowConnModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/10 hover:bg-white/15 text-white text-xs font-medium rounded-lg transition-colors">
              {Ico.plus} Add Store
            </button>
          </div>

          <div className="px-5">
            {loadingConns ? (
              <p className="text-sm py-6 text-center" style={{ color: 'var(--text-muted)' }}>Loading connections…</p>
            ) : connections.length === 0 ? (
              <div className="py-8 text-center">
                <div className="w-10 h-10 rounded-full flex items-center justify-center mx-auto mb-3" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>
                  {Ico.link}
                </div>
                <p className="text-sm font-medium text-white">No stores connected</p>
                <p className="text-xs mt-1 mb-4" style={{ color: 'var(--text-muted)' }}>
                  Add a store to enable automatic inventory sync and price push-back.
                </p>
                <button onClick={() => setShowConnModal(true)}
                  className="px-4 py-2 bg-white/10 hover:bg-white/15 text-white text-sm font-medium rounded-xl transition-colors">
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
          <div className="rounded-2xl p-4 flex items-center justify-between gap-4" style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.25)' }}>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'rgba(16,185,129,0.2)', color: '#10b981' }}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
              </div>
              <div>
                <p className="text-sm font-semibold text-emerald-400">
                  Import complete — {importResult.products_imported} product{importResult.products_imported !== 1 ? 's' : ''} added
                </p>
                {importResult.products_skipped > 0 && (
                  <p className="text-xs text-emerald-500">{importResult.products_skipped} duplicate{importResult.products_skipped !== 1 ? 's' : ''} skipped</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Link href="/products" className="text-xs font-medium text-emerald-400 hover:text-emerald-300 hover:underline">View products →</Link>
              <button onClick={() => setImportResult(null)} className="text-emerald-600 hover:text-emerald-400 p-1 transition-colors">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
          </div>
        )}

        {/* Integration Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {INTEGRATIONS.map((intg, i) => (
            <div key={i} className="rounded-2xl shadow-sm p-5 flex flex-col gap-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0" style={intg.iconBg}>{intg.icon}</div>
                <h3 className="text-base font-bold text-white">{intg.title}</h3>
              </div>
              <p className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>{intg.desc}</p>
              <ul className="space-y-1.5">
                {intg.features.map((f, j) => (
                  <li key={j} className="flex items-center gap-2 text-xs" style={{ color: 'rgba(255,255,255,0.7)' }}>
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
        <div className="rounded-2xl shadow-sm overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <h2 className="text-sm font-semibold text-white">How It Works</h2>
          </div>
          <div className="p-5 grid grid-cols-2 lg:grid-cols-4 gap-4">
            {STEPS.map((s, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-8 h-8 gradient-brand text-white rounded-xl flex items-center justify-center text-sm font-bold shrink-0">{s.n}</div>
                <div>
                  <p className="text-sm font-semibold text-white">{s.title}</p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Feature Highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {FEATURES.map((f, i) => (
            <div key={i} className="rounded-2xl shadow-sm p-5 flex items-start gap-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={f.iconBg}>{f.icon}</div>
              <div>
                <p className="text-sm font-semibold text-white">{f.title}</p>
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{f.desc}</p>
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
