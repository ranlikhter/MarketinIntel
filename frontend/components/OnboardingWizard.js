/**
 * OnboardingWizard — shown to new users with 0 products.
 *
 * Steps:
 *   0  Welcome
 *   1  Add / import first product(s)
 *   2  Add a competitor
 *   3  Set a price alert
 *   4  All done!
 *
 * Step 1 has two modes:
 *   "manual"  — simple inline form (single product)
 *   "import"  — inline XML / WooCommerce / Shopify import flow
 *
 * Progress is stored in localStorage so refreshing the page
 * doesn't reset the wizard. Users can skip individual steps
 * or dismiss the whole wizard via the × button.
 */
import { useState, useEffect } from 'react';
import Link from 'next/link';
import api from '../lib/api';

const STORAGE_KEY = 'marketintel_onboarding_v1';

const ALERT_TYPES = [
  { value: 'price_drop',       label: 'Price Drop' },
  { value: 'price_increase',   label: 'Price Increase' },
  { value: 'out_of_stock',     label: 'Out of Stock' },
  { value: 'price_war',        label: 'Price War' },
  { value: 'new_competitor',   label: 'New Competitor' },
  { value: 'back_in_stock',    label: 'Back in Stock' },
];

const COMPETITOR_TYPES = [
  { value: 'amazon',   label: 'Amazon' },
  { value: 'custom',   label: 'Custom website' },
  { value: 'ebay',     label: 'eBay' },
  { value: 'shopify',  label: 'Shopify store' },
];

const XML_FORMATS = [
  { value: 'auto',            label: 'Auto-detect' },
  { value: 'google_shopping', label: 'Google Shopping Feed' },
  { value: 'woocommerce',     label: 'WooCommerce Export' },
  { value: 'custom',          label: 'Custom Format' },
];

// ─── Icons ───────────────────────────────────────────────────────────────────
const Ico = {
  x:       <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>,
  check:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>,
  checkLg: <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>,
  arrow:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>,
  back:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>,
  box:     <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>,
  globe:   <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>,
  bell:    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>,
  rocket:  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>,
  wave:    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" /></svg>,
  upload:  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>,
  store:   <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" /></svg>,
  cart:    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" /></svg>,
  pen:     <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>,
  import:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>,
  spin:    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>,
};

// ─── Shared input style ───────────────────────────────────────────────────────
const INPUT = 'w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent';
const SELECT = `${INPUT} bg-white`;

// ─── Step indicator ───────────────────────────────────────────────────────────
function StepDots({ current, total }) {
  return (
    <div className="flex items-center gap-2 justify-center">
      {Array.from({ length: total }).map((_, i) => (
        <span key={i} className={`rounded-full transition-all duration-300 ${
          i < current  ? 'w-2 h-2 bg-blue-600' :
          i === current ? 'w-5 h-2 bg-blue-600' :
                          'w-2 h-2 bg-gray-200'
        }`} />
      ))}
    </div>
  );
}

// ─── Mode tab ─────────────────────────────────────────────────────────────────
function ModeTabs({ mode, onChange }) {
  return (
    <div className="flex gap-1 p-1 bg-gray-100 rounded-xl w-full mb-5">
      {[
        { value: 'manual', label: 'Add manually', icon: Ico.pen },
        { value: 'import', label: 'Import from store', icon: Ico.import },
      ].map(t => (
        <button
          key={t.value}
          type="button"
          onClick={() => onChange(t.value)}
          className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-semibold transition-all ${
            mode === t.value
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <span className="opacity-70">{t.icon}</span>
          {t.label}
        </button>
      ))}
    </div>
  );
}

// ─── Import source cards ──────────────────────────────────────────────────────
const IMPORT_SOURCES = [
  { value: 'xml',         label: 'XML Feed',     desc: 'Upload an XML product catalog',         icon: Ico.upload, iconBg: 'bg-orange-50 text-orange-600' },
  { value: 'woocommerce', label: 'WooCommerce',  desc: 'Connect via REST API',                  icon: Ico.store,  iconBg: 'bg-violet-50 text-violet-600' },
  { value: 'shopify',     label: 'Shopify',      desc: 'Connect via Admin API',                 icon: Ico.cart,   iconBg: 'bg-emerald-50 text-emerald-600' },
];

// ─── Step 0: Welcome ──────────────────────────────────────────────────────────
function StepWelcome({ onNext }) {
  return (
    <div className="text-center space-y-6 py-4">
      <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto text-blue-600">{Ico.wave}</div>
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Welcome to MarketIntel</h2>
        <p className="text-gray-500 mt-2 text-sm max-w-sm mx-auto">
          Let's get you set up in 3 quick steps. We'll add products, a competitor to monitor, and your first price alert.
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {[
          { icon: Ico.box,    text: 'Track your products' },
          { icon: Ico.globe,  text: 'Monitor any website' },
          { icon: Ico.bell,   text: 'Get price alerts' },
        ].map((f, i) => (
          <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 border border-gray-100 rounded-full text-xs text-gray-600 font-medium">
            <span className="text-blue-500 scale-75">{f.icon}</span>{f.text}
          </span>
        ))}
      </div>
      <button
        onClick={onNext}
        className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium text-sm transition-colors"
      >
        Get started {Ico.arrow}
      </button>
    </div>
  );
}

// ─── Import sub-flow ──────────────────────────────────────────────────────────
function ImportFlow({ onDone, onBack }) {
  const [subStep, setSubStep]     = useState('source'); // 'source' | 'configure' | 'done'
  const [source, setSource]       = useState(null);
  const [importing, setImporting] = useState(false);
  const [error, setError]         = useState('');
  const [result, setResult]       = useState(null);

  // XML state
  const [xmlFile, setXmlFile]     = useState(null);
  const [xmlFormat, setXmlFormat] = useState('auto');

  // WooCommerce state
  const [woo, setWoo] = useState({ storeUrl: '', consumerKey: '', consumerSecret: '', importLimit: 100 });

  // Shopify state
  const [shopify, setShopify] = useState({ shopUrl: '', accessToken: '', importLimit: 100 });

  const runImport = async () => {
    setImporting(true);
    setError('');
    try {
      let res;
      if (source === 'xml') {
        if (!xmlFile) { setError('Please select an XML file'); setImporting(false); return; }
        res = await api.importFromXML(xmlFile, xmlFormat);
      } else if (source === 'woocommerce') {
        if (!woo.storeUrl || !woo.consumerKey || !woo.consumerSecret) {
          setError('Store URL, Consumer Key and Consumer Secret are required');
          setImporting(false);
          return;
        }
        res = await api.importFromWooCommerce(woo.storeUrl, woo.consumerKey, woo.consumerSecret, woo.importLimit);
      } else if (source === 'shopify') {
        if (!shopify.shopUrl || !shopify.accessToken) {
          setError('Shop URL and Access Token are required');
          setImporting(false);
          return;
        }
        res = await api.importFromShopify(shopify.shopUrl, shopify.accessToken, shopify.importLimit);
      }

      if (res?.success) {
        setResult(res);
        setSubStep('done');
      } else {
        setError(res?.errors?.[0] || 'Import failed. Check your credentials and try again.');
      }
    } catch (e) {
      setError(e.message || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  // ── Source picker ────────────────────────────────────────────────────────
  if (subStep === 'source') {
    return (
      <div className="space-y-4">
        <p className="text-xs text-gray-500">Choose where to pull your product catalogue from:</p>
        <div className="grid grid-cols-3 gap-3">
          {IMPORT_SOURCES.map(s => (
            <button
              key={s.value}
              type="button"
              onClick={() => { setSource(s.value); setSubStep('configure'); setError(''); }}
              className="flex flex-col items-center gap-2 p-4 bg-white border border-gray-200 hover:border-blue-400 hover:bg-blue-50 rounded-xl text-center transition-all"
            >
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${s.iconBg}`}>{s.icon}</div>
              <p className="text-xs font-semibold text-gray-900">{s.label}</p>
              <p className="text-[10px] text-gray-400 leading-tight">{s.desc}</p>
            </button>
          ))}
        </div>
        <button type="button" onClick={onBack} className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1">
          {Ico.back} Switch to manual entry
        </button>
      </div>
    );
  }

  // ── Configuration form ───────────────────────────────────────────────────
  if (subStep === 'configure') {
    const src = IMPORT_SOURCES.find(s => s.value === source);
    return (
      <div className="space-y-4">
        <button type="button" onClick={() => setSubStep('source')} className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600">
          {Ico.back} Back
        </button>

        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${src.iconBg}`}>{src.icon}</div>
          <div>
            <p className="text-sm font-bold text-gray-900">Connect {src.label}</p>
            <p className="text-xs text-gray-400">{src.desc}</p>
          </div>
        </div>

        {error && <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-xl px-3 py-2">{error}</p>}

        {/* XML form */}
        {source === 'xml' && (
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">XML file</label>
              <input
                type="file"
                accept=".xml"
                onChange={e => setXmlFile(e.target.files[0])}
                className="block w-full text-xs text-gray-500 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
              />
              {xmlFile && <p className="mt-1 text-xs text-gray-500">Selected: {xmlFile.name}</p>}
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Format</label>
              <select value={xmlFormat} onChange={e => setXmlFormat(e.target.value)} className={SELECT}>
                {XML_FORMATS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
              </select>
            </div>
          </div>
        )}

        {/* WooCommerce form */}
        {source === 'woocommerce' && (
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Store URL <span className="text-red-400">*</span></label>
              <input value={woo.storeUrl} onChange={e => setWoo(w => ({ ...w, storeUrl: e.target.value }))} placeholder="https://yourstore.com" className={INPUT} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Consumer Key <span className="text-red-400">*</span></label>
                <input value={woo.consumerKey} onChange={e => setWoo(w => ({ ...w, consumerKey: e.target.value }))} placeholder="ck_xxxxx" className={INPUT} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Consumer Secret <span className="text-red-400">*</span></label>
                <input type="password" value={woo.consumerSecret} onChange={e => setWoo(w => ({ ...w, consumerSecret: e.target.value }))} placeholder="cs_xxxxx" className={INPUT} />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Max products to import</label>
              <input type="number" min="1" max="1000" value={woo.importLimit} onChange={e => setWoo(w => ({ ...w, importLimit: parseInt(e.target.value) || 100 }))} className={INPUT} />
            </div>
            <p className="text-xs text-gray-400">
              Find your API keys in WooCommerce → Settings → Advanced → REST API.
            </p>
          </div>
        )}

        {/* Shopify form */}
        {source === 'shopify' && (
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Shop URL <span className="text-red-400">*</span></label>
              <input value={shopify.shopUrl} onChange={e => setShopify(s => ({ ...s, shopUrl: e.target.value }))} placeholder="your-store.myshopify.com" className={INPUT} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Admin API Access Token <span className="text-red-400">*</span></label>
              <input type="password" value={shopify.accessToken} onChange={e => setShopify(s => ({ ...s, accessToken: e.target.value }))} placeholder="shpat_xxxxx" className={INPUT} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Max products to import</label>
              <input type="number" min="1" max="1000" value={shopify.importLimit} onChange={e => setShopify(s => ({ ...s, importLimit: parseInt(e.target.value) || 100 }))} className={INPUT} />
            </div>
            <p className="text-xs text-gray-400">
              Create a private app in Shopify Admin → Settings → Apps → Develop apps.
            </p>
          </div>
        )}

        <button
          type="button"
          onClick={runImport}
          disabled={importing}
          className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {importing ? <>{Ico.spin} Importing…</> : 'Import Products'}
        </button>
      </div>
    );
  }

  // ── Done ─────────────────────────────────────────────────────────────────
  if (subStep === 'done') {
    return (
      <div className="text-center space-y-4 py-2">
        <div className="w-14 h-14 bg-emerald-50 rounded-2xl flex items-center justify-center mx-auto text-emerald-500">{Ico.checkLg}</div>
        <div>
          <p className="text-base font-bold text-gray-900">Import complete!</p>
          <p className="text-sm text-gray-500 mt-1">
            <strong className="text-gray-900">{result?.products_imported ?? 0}</strong> products imported
            {result?.products_skipped > 0 && <span className="text-gray-400"> · {result.products_skipped} skipped (duplicates)</span>}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onDone({ importedCount: result?.products_imported ?? 0 })}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors"
        >
          Continue {Ico.arrow}
        </button>
      </div>
    );
  }
}

// ─── Step 1: Add / import products ───────────────────────────────────────────
function StepProduct({ onNext, onSkip }) {
  const [mode, setMode]   = useState('manual'); // 'manual' | 'import'
  const [form, setForm]   = useState({ title: '', sku: '', my_price: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleManualSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) { setError('Product name is required'); return; }
    setSaving(true);
    setError('');
    try {
      const payload = { title: form.title.trim() };
      if (form.sku.trim())  payload.sku = form.sku.trim();
      if (form.my_price)    payload.my_price = parseFloat(form.my_price);
      const product = await api.createProduct(payload);
      onNext({ product, importedCount: 0 });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-1">
      <div className="flex items-start gap-3 mb-4">
        <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600 shrink-0">{Ico.box}</div>
        <div>
          <h2 className="text-lg font-bold text-gray-900">Add your products</h2>
          <p className="text-sm text-gray-500 mt-0.5">Add a single product or import your entire catalogue.</p>
        </div>
      </div>

      <ModeTabs mode={mode} onChange={m => { setMode(m); setError(''); }} />

      {/* ── Manual mode ── */}
      {mode === 'manual' && (
        <>
          {error && <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-xl px-3 py-2 mb-3">{error}</p>}
          <form onSubmit={handleManualSubmit} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">
                Product name <span className="text-red-400">*</span>
              </label>
              <input
                autoFocus
                value={form.title}
                onChange={e => set('title', e.target.value)}
                placeholder="e.g. Sony WH-1000XM5 Headphones"
                className={INPUT}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">SKU / ASIN</label>
                <input value={form.sku} onChange={e => set('sku', e.target.value)} placeholder="Optional" className={INPUT} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Your price ($)</label>
                <input type="number" step="0.01" min="0" value={form.my_price} onChange={e => set('my_price', e.target.value)} placeholder="e.g. 299.99" className={INPUT} />
              </div>
            </div>
            <div className="flex gap-3 pt-1">
              <button type="button" onClick={onSkip} className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors">
                Skip for now
              </button>
              <button type="submit" disabled={saving} className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                {saving ? <>{Ico.spin} Saving…</> : <>Add product {Ico.arrow}</>}
              </button>
            </div>
          </form>
          <p className="text-xs text-center text-gray-400 mt-2">
            Want more options?{' '}
            <Link href="/products/add" className="text-blue-600 hover:underline">Open full product form</Link>
          </p>
        </>
      )}

      {/* ── Import mode ── */}
      {mode === 'import' && (
        <>
          <ImportFlow
            onDone={({ importedCount }) => onNext({ product: null, importedCount })}
            onBack={() => setMode('manual')}
          />
          <div className="flex gap-3 pt-3 border-t border-gray-50 mt-4">
            <button type="button" onClick={onSkip} className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors">
              Skip for now
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Step 2: Add competitor ───────────────────────────────────────────────────
function StepCompetitor({ product, importedCount, onNext, onSkip }) {
  const [form, setForm]   = useState({ name: '', url: '', type: 'amazon' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.url.trim()) { setError('Name and URL are required'); return; }
    setSaving(true);
    setError('');
    try {
      let url = form.url.trim();
      if (!/^https?:\/\//i.test(url)) url = 'https://' + url;
      const competitor = await api.createCompetitor({
        name: form.name.trim(),
        base_url: url,
        competitor_type: form.type,
        is_active: true,
      });
      onNext({ competitor });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const productLabel = importedCount > 0
    ? `${importedCount} imported product${importedCount !== 1 ? 's' : ''}`
    : product?.title ?? null;

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-violet-50 rounded-xl flex items-center justify-center text-violet-600 shrink-0">{Ico.globe}</div>
        <div>
          <h2 className="text-lg font-bold text-gray-900">Add a competitor</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Add any website to monitor — Amazon, Shopify stores, or any e-commerce site.
            {productLabel && <> Prices will be matched against <strong>{productLabel}</strong>.</>}
          </p>
        </div>
      </div>

      {error && <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-xl px-3 py-2">{error}</p>}

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Name <span className="text-red-400">*</span></label>
            <input autoFocus value={form.name} onChange={e => set('name', e.target.value)} placeholder="e.g. Amazon UK" className={INPUT} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Type</label>
            <select value={form.type} onChange={e => set('type', e.target.value)} className={SELECT}>
              {COMPETITOR_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1.5">Website URL <span className="text-red-400">*</span></label>
          <input value={form.url} onChange={e => set('url', e.target.value)} placeholder="e.g. amazon.co.uk" className={INPUT} />
        </div>
        <div className="flex gap-3 pt-1">
          <button type="button" onClick={onSkip} className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors">
            Skip for now
          </button>
          <button type="submit" disabled={saving} className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
            {saving ? <>{Ico.spin} Saving…</> : <>Add competitor {Ico.arrow}</>}
          </button>
        </div>
      </form>

      <p className="text-xs text-center text-gray-400">
        Add more competitors later on the{' '}
        <Link href="/competitors" className="text-blue-600 hover:underline">Competitors page</Link>
      </p>
    </div>
  );
}

// ─── Step 3: Set alert ────────────────────────────────────────────────────────
function StepAlert({ product, importedCount, onNext, onSkip }) {
  const [alertType, setAlertType] = useState('price_drop');
  const [threshold, setThreshold] = useState('');
  const [saving, setSaving]       = useState(false);
  const [error, setError]         = useState('');

  const productLabel = importedCount > 0
    ? `your ${importedCount} product${importedCount !== 1 ? 's' : ''}`
    : product?.title ? `"${product.title}"` : 'all products';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = { alert_type: alertType };
      if (product?.id) payload.product_id = product.id;
      if (threshold)   payload.threshold_value = parseFloat(threshold);
      await api.createAlert(payload);
      onNext({});
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const showThreshold = ['price_drop', 'price_increase'].includes(alertType);

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-amber-50 rounded-xl flex items-center justify-center text-amber-600 shrink-0">{Ico.bell}</div>
        <div>
          <h2 className="text-lg font-bold text-gray-900">Set a price alert</h2>
          <p className="text-sm text-gray-500 mt-0.5">Get notified when conditions change for {productLabel}.</p>
        </div>
      </div>

      {error && <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-xl px-3 py-2">{error}</p>}

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {ALERT_TYPES.map(t => (
            <button key={t.value} type="button" onClick={() => setAlertType(t.value)}
              className={`px-3 py-2.5 rounded-xl text-xs font-medium border text-left transition-all ${
                alertType === t.value
                  ? 'bg-blue-50 border-blue-300 text-blue-700'
                  : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              {alertType === t.value && <span className="mr-1">✓</span>}
              {t.label}
            </button>
          ))}
        </div>

        {showThreshold && (
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Threshold % (optional)</label>
            <input type="number" step="0.1" min="0" value={threshold} onChange={e => setThreshold(e.target.value)} placeholder="e.g. 5 → alert when price drops by 5%" className={INPUT} />
          </div>
        )}

        <div className="flex gap-3 pt-1">
          <button type="button" onClick={onSkip} className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors">
            Skip for now
          </button>
          <button type="submit" disabled={saving} className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
            {saving ? <>{Ico.spin} Saving…</> : <>Create alert {Ico.arrow}</>}
          </button>
        </div>
      </form>
    </div>
  );
}

// ─── Step 4: Done ─────────────────────────────────────────────────────────────
function StepDone({ product, importedCount, competitor, onDismiss }) {
  return (
    <div className="text-center space-y-6 py-4">
      <div className="w-16 h-16 bg-emerald-50 rounded-2xl flex items-center justify-center mx-auto text-emerald-600">{Ico.rocket}</div>
      <div>
        <h2 className="text-2xl font-bold text-gray-900">You're all set!</h2>
        <p className="text-sm text-gray-500 mt-2 max-w-xs mx-auto">
          {!product && importedCount === 0
            ? "Explore MarketIntel and add products when you're ready."
            : "Start scraping to see competitor prices in real time."}
        </p>
      </div>

      <div className="bg-gray-50 rounded-2xl p-4 space-y-2 text-left max-w-xs mx-auto">
        {importedCount > 0 ? (
          <SummaryRow done label={`${importedCount} product${importedCount !== 1 ? 's' : ''} imported`} />
        ) : (
          <SummaryRow done={!!product} label={product ? `Product: ${product.title}` : 'No product added yet'} />
        )}
        <SummaryRow done={!!competitor} label={competitor ? `Competitor: ${competitor.name}` : 'No competitor added yet'} />
        <SummaryRow done label="Alert configured" />
      </div>

      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        {importedCount > 0 || product ? (
          <Link
            href={importedCount > 0 ? '/products' : `/products/${product.id}`}
            onClick={onDismiss}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors"
          >
            {importedCount > 0 ? 'View all products' : 'View product'} {Ico.arrow}
          </Link>
        ) : (
          <Link href="/products/add" onClick={onDismiss} className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors">
            Add a product {Ico.arrow}
          </Link>
        )}
        <button onClick={onDismiss} className="inline-flex items-center justify-center gap-2 px-5 py-2.5 border border-gray-200 hover:bg-gray-50 text-gray-700 rounded-xl text-sm font-medium transition-colors">
          Explore dashboard
        </button>
      </div>
    </div>
  );
}

function SummaryRow({ done, label }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 text-white text-xs ${done ? 'bg-emerald-500' : 'bg-gray-200'}`}>
        {done && Ico.check}
      </span>
      <span className={`text-sm ${done ? 'text-gray-900' : 'text-gray-400'}`}>{label}</span>
    </div>
  );
}

// ─── Main wizard component ────────────────────────────────────────────────────
export default function OnboardingWizard({ onDismiss }) {
  const [step, setStep]               = useState(0);
  const [product, setProduct]         = useState(null);
  const [importedCount, setImported]  = useState(0);
  const [competitor, setCompetitor]   = useState(null);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      if (saved.step) setStep(saved.step);
    } catch { /* ignore */ }
  }, []);

  const goTo = (s) => {
    setStep(s);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ step: s })); } catch { /* */ }
  };

  const handleDismiss = () => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ dismissed: true })); } catch { /* */ }
    onDismiss?.();
  };

  const TOTAL = 5; // steps 0‒4

  return (
    <div className="bg-white rounded-2xl border border-blue-100 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 pt-5 pb-4 border-b border-gray-50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Setup Guide · Step {Math.min(step + 1, TOTAL)} of {TOTAL - 1}
          </span>
        </div>
        <button onClick={handleDismiss} className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors" title="Dismiss">
          {Ico.x}
        </button>
      </div>

      {/* Progress dots */}
      <div className="px-5 pt-4">
        <StepDots current={step} total={TOTAL} />
      </div>

      {/* Content */}
      <div className="p-5 pt-6">
        {step === 0 && <StepWelcome onNext={() => goTo(1)} />}

        {step === 1 && (
          <StepProduct
            onNext={({ product: p, importedCount: n }) => {
              setProduct(p);
              setImported(n || 0);
              goTo(2);
            }}
            onSkip={() => goTo(2)}
          />
        )}

        {step === 2 && (
          <StepCompetitor
            product={product}
            importedCount={importedCount}
            onNext={({ competitor: c }) => { setCompetitor(c); goTo(3); }}
            onSkip={() => goTo(3)}
          />
        )}

        {step === 3 && (
          <StepAlert
            product={product}
            importedCount={importedCount}
            onNext={() => goTo(4)}
            onSkip={() => goTo(4)}
          />
        )}

        {step === 4 && (
          <StepDone
            product={product}
            importedCount={importedCount}
            competitor={competitor}
            onDismiss={handleDismiss}
          />
        )}
      </div>
    </div>
  );
}

// ─── Helper ───────────────────────────────────────────────────────────────────
export function shouldShowOnboarding() {
  if (typeof window === 'undefined') return false;
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    return !saved.dismissed;
  } catch {
    return true;
  }
}
