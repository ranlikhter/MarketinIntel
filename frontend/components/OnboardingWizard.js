/**
 * OnboardingWizard — shown to new users with 0 products.
 *
 * Steps:
 *   0  Welcome
 *   1  Add first product
 *   2  Add a competitor
 *   3  Set a price alert
 *   4  All done!
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

// ─── Icons ───────────────────────────────────────────────────────────────────
const Ico = {
  x:      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>,
  check:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>,
  arrow:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>,
  box:    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>,
  globe:  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>,
  bell:   <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>,
  rocket: <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>,
  wave:   <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" /></svg>,
  spin:   <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>,
};

// ─── Step indicator ───────────────────────────────────────────────────────────
function StepDots({ current, total }) {
  return (
    <div className="flex items-center gap-2 justify-center">
      {Array.from({ length: total }).map((_, i) => (
        <span
          key={i}
          className={`rounded-full transition-all duration-300 ${
            i < current
              ? 'w-2 h-2 bg-blue-600'
              : i === current
              ? 'w-5 h-2 bg-blue-600'
              : 'w-2 h-2 bg-gray-200'
          }`}
        />
      ))}
    </div>
  );
}

// ─── Step 0: Welcome ──────────────────────────────────────────────────────────
function StepWelcome({ onNext }) {
  return (
    <div className="text-center space-y-6 py-4">
      <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto text-blue-600">
        {Ico.wave}
      </div>
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Welcome to MarketIntel</h2>
        <p className="text-gray-500 mt-2 text-sm max-w-sm mx-auto">
          Let's get you set up in 3 quick steps. We'll add a product, add a competitor to monitor, and set your first price alert.
        </p>
      </div>

      {/* Feature pills */}
      <div className="flex flex-wrap justify-center gap-2">
        {[
          { icon: Ico.box,   text: 'Track your products' },
          { icon: Ico.globe, text: 'Monitor any website' },
          { icon: Ico.bell,  text: 'Get price alerts' },
        ].map((f, i) => (
          <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 border border-gray-100 rounded-full text-xs text-gray-600 font-medium">
            <span className="text-blue-500 scale-75">{f.icon}</span>
            {f.text}
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

// ─── Step 1: Add product ──────────────────────────────────────────────────────
function StepProduct({ onNext, onSkip }) {
  const [form, setForm] = useState({ title: '', sku: '', brand: '', my_price: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) { setError('Product name is required'); return; }
    setSaving(true);
    setError('');
    try {
      const payload = { title: form.title.trim() };
      if (form.sku.trim())   payload.sku = form.sku.trim();
      if (form.brand.trim()) payload.brand = form.brand.trim();
      if (form.my_price)     payload.my_price = parseFloat(form.my_price);
      const product = await api.createProduct(payload);
      onNext({ product });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600 shrink-0">{Ico.box}</div>
        <div>
          <h2 className="text-lg font-bold text-gray-900">Add your first product</h2>
          <p className="text-sm text-gray-500 mt-0.5">This is the product whose price you want to compare against competitors.</p>
        </div>
      </div>

      {error && <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-xl px-3 py-2">{error}</p>}

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1.5">
            Product name <span className="text-red-400">*</span>
          </label>
          <input
            autoFocus
            value={form.title}
            onChange={e => set('title', e.target.value)}
            placeholder="e.g. Sony WH-1000XM5 Headphones"
            className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">SKU / ASIN</label>
            <input
              value={form.sku}
              onChange={e => set('sku', e.target.value)}
              placeholder="Optional"
              className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Your price ($)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={form.my_price}
              onChange={e => set('my_price', e.target.value)}
              placeholder="e.g. 299.99"
              className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="flex gap-3 pt-1">
          <button
            type="button"
            onClick={onSkip}
            className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors"
          >
            Skip for now
          </button>
          <button
            type="submit"
            disabled={saving}
            className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {saving ? <>{Ico.spin} Saving…</> : <>Add product {Ico.arrow}</>}
          </button>
        </div>
      </form>

      <p className="text-xs text-center text-gray-400">
        Want more options?{' '}
        <Link href="/products/add" className="text-blue-600 hover:underline">Open full product form</Link>
      </p>
    </div>
  );
}

// ─── Step 2: Add competitor ───────────────────────────────────────────────────
function StepCompetitor({ product, onNext, onSkip }) {
  const [form, setForm] = useState({ name: '', url: '', type: 'amazon' });
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

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-violet-50 rounded-xl flex items-center justify-center text-violet-600 shrink-0">{Ico.globe}</div>
        <div>
          <h2 className="text-lg font-bold text-gray-900">Add a competitor</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Add any website to monitor — Amazon, Shopify stores, or any e-commerce site.
            {product && <> We'll start matching prices for <strong>{product.title}</strong>.</>}
          </p>
        </div>
      </div>

      {error && <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-xl px-3 py-2">{error}</p>}

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">
              Name <span className="text-red-400">*</span>
            </label>
            <input
              autoFocus
              value={form.name}
              onChange={e => set('name', e.target.value)}
              placeholder="e.g. Amazon UK"
              className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Type</label>
            <select
              value={form.type}
              onChange={e => set('type', e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              {COMPETITOR_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1.5">
            Website URL <span className="text-red-400">*</span>
          </label>
          <input
            value={form.url}
            onChange={e => set('url', e.target.value)}
            placeholder="e.g. amazon.co.uk"
            className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div className="flex gap-3 pt-1">
          <button
            type="button"
            onClick={onSkip}
            className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors"
          >
            Skip for now
          </button>
          <button
            type="submit"
            disabled={saving}
            className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
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
function StepAlert({ product, onNext, onSkip }) {
  const [form, setForm] = useState({ alert_type: 'price_drop', threshold_value: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = { alert_type: form.alert_type };
      if (product?.id)         payload.product_id = product.id;
      if (form.threshold_value) payload.threshold_value = parseFloat(form.threshold_value);
      await api.createAlert(payload);
      onNext({});
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const showThreshold = ['price_drop', 'price_increase'].includes(form.alert_type);

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-amber-50 rounded-xl flex items-center justify-center text-amber-600 shrink-0">{Ico.bell}</div>
        <div>
          <h2 className="text-lg font-bold text-gray-900">Set a price alert</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            We'll notify you when this condition is met
            {product && <> for <strong>{product.title}</strong></>}.
          </p>
        </div>
      </div>

      {error && <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-xl px-3 py-2">{error}</p>}

      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Alert type grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {ALERT_TYPES.map(t => (
            <button
              key={t.value}
              type="button"
              onClick={() => set('alert_type', t.value)}
              className={`px-3 py-2.5 rounded-xl text-xs font-medium border text-left transition-all ${
                form.alert_type === t.value
                  ? 'bg-blue-50 border-blue-300 text-blue-700'
                  : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              {form.alert_type === t.value && (
                <span className="mr-1 text-blue-600">✓</span>
              )}
              {t.label}
            </button>
          ))}
        </div>

        {/* Threshold */}
        {showThreshold && (
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">
              Threshold % (optional)
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={form.threshold_value}
              onChange={e => set('threshold_value', e.target.value)}
              placeholder="e.g. 5 → alert when price drops by 5%"
              className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        )}

        <div className="flex gap-3 pt-1">
          <button
            type="button"
            onClick={onSkip}
            className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors"
          >
            Skip for now
          </button>
          <button
            type="submit"
            disabled={saving}
            className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {saving ? <>{Ico.spin} Saving…</> : <>Create alert {Ico.arrow}</>}
          </button>
        </div>
      </form>
    </div>
  );
}

// ─── Step 4: Done ─────────────────────────────────────────────────────────────
function StepDone({ product, competitor, onDismiss }) {
  const completed = [product, competitor].filter(Boolean).length;
  const total = 2; // product + competitor (alert is optional)

  return (
    <div className="text-center space-y-6 py-4">
      <div className="w-16 h-16 bg-emerald-50 rounded-2xl flex items-center justify-center mx-auto text-emerald-600">
        {Ico.rocket}
      </div>
      <div>
        <h2 className="text-2xl font-bold text-gray-900">You're all set!</h2>
        <p className="text-sm text-gray-500 mt-2 max-w-xs mx-auto">
          {completed === 0
            ? "You're ready to explore MarketIntel. Add products anytime to start tracking."
            : completed === total
            ? "MarketIntel is configured and ready. Start scraping to see competitor prices."
            : "Good start! You can add more products and competitors whenever you're ready."}
        </p>
      </div>

      {/* Summary */}
      <div className="bg-gray-50 rounded-2xl p-4 space-y-2 text-left max-w-xs mx-auto">
        <SummaryRow done={!!product}    label={product    ? `Product: ${product.title}` : 'No product added yet'} />
        <SummaryRow done={!!competitor} label={competitor ? `Competitor: ${competitor.name}` : 'No competitor added yet'} />
        <SummaryRow done label="Alert configured" />
      </div>

      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        {product ? (
          <Link
            href={`/products/${product.id}`}
            onClick={onDismiss}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors"
          >
            View product {Ico.arrow}
          </Link>
        ) : (
          <Link
            href="/products/add"
            onClick={onDismiss}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors"
          >
            Add a product {Ico.arrow}
          </Link>
        )}
        <button
          onClick={onDismiss}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 border border-gray-200 hover:bg-gray-50 text-gray-700 rounded-xl text-sm font-medium transition-colors"
        >
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
        {done ? Ico.check : null}
      </span>
      <span className={`text-sm ${done ? 'text-gray-900' : 'text-gray-400'}`}>{label}</span>
    </div>
  );
}

// ─── Main wizard component ────────────────────────────────────────────────────
export default function OnboardingWizard({ onDismiss }) {
  const [step, setStep]           = useState(0);
  const [product, setProduct]     = useState(null);
  const [competitor, setCompetitor] = useState(null);

  // Restore step from localStorage
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      if (saved.step) setStep(saved.step);
    } catch { /* ignore */ }
  }, []);

  const save = (nextStep) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ step: nextStep }));
    } catch { /* ignore */ }
  };

  const goTo = (s) => { setStep(s); save(s); };

  const handleDismiss = () => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ dismissed: true })); } catch { /* */ }
    onDismiss?.();
  };

  const TOTAL_CONTENT_STEPS = 5; // 0 Welcome, 1 Product, 2 Competitor, 3 Alert, 4 Done

  return (
    <div className="bg-white rounded-2xl border border-blue-100 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 pt-5 pb-4 border-b border-gray-50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Setup Guide · Step {Math.min(step + 1, TOTAL_CONTENT_STEPS)} of {TOTAL_CONTENT_STEPS - 1}
          </span>
        </div>
        <button
          onClick={handleDismiss}
          className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          title="Dismiss"
        >
          {Ico.x}
        </button>
      </div>

      {/* Progress dots */}
      <div className="px-5 pt-4">
        <StepDots current={step} total={TOTAL_CONTENT_STEPS} />
      </div>

      {/* Step content */}
      <div className="p-5 pt-6">
        {step === 0 && (
          <StepWelcome onNext={() => goTo(1)} />
        )}
        {step === 1 && (
          <StepProduct
            onNext={({ product: p }) => { setProduct(p); goTo(2); }}
            onSkip={() => goTo(2)}
          />
        )}
        {step === 2 && (
          <StepCompetitor
            product={product}
            onNext={({ competitor: c }) => { setCompetitor(c); goTo(3); }}
            onSkip={() => goTo(3)}
          />
        )}
        {step === 3 && (
          <StepAlert
            product={product}
            onNext={() => goTo(4)}
            onSkip={() => goTo(4)}
          />
        )}
        {step === 4 && (
          <StepDone
            product={product}
            competitor={competitor}
            onDismiss={handleDismiss}
          />
        )}
      </div>
    </div>
  );
}

// ─── Helper to check if wizard should show ────────────────────────────────────
export function shouldShowOnboarding() {
  if (typeof window === 'undefined') return false;
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    return !saved.dismissed;
  } catch {
    return true;
  }
}
