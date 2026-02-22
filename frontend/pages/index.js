import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import OnboardingWizard, { shouldShowOnboarding } from '../components/OnboardingWizard';
import api from '../lib/api';

const Ico = {
  box:     <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>,
  chart:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  globe:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>,
  arrow:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>,
  plus:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  bell:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>,
  bolt:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  shield:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
  clock:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
};

function StatCard({ label, value, sub, color, icon, href }) {
  const bg = {
    blue:    'bg-blue-50 text-blue-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    violet:  'bg-violet-50 text-violet-600',
    amber:   'bg-amber-50 text-amber-600',
  }[color];

  const inner = (
    <div className={`bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex items-center gap-4 ${href ? 'hover:shadow-md hover:border-gray-200 transition-all' : ''}`}>
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${bg}`}>{icon}</div>
      <div>
        <p className="text-2xl font-bold text-gray-900 leading-none">{value}</p>
        <p className="text-xs text-gray-500 mt-1">{label}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );

  return href ? <Link href={href}>{inner}</Link> : inner;
}

const FEATURES = [
  { icon: Ico.bolt,   iconBg: 'bg-blue-50 text-blue-600',    title: 'Real-time Scraping',      desc: 'On-demand Playwright scraping with anti-bot detection for Amazon and any custom site.' },
  { icon: Ico.globe,  iconBg: 'bg-violet-50 text-violet-600', title: 'Any Website',             desc: 'Add any competitor with custom CSS selectors. Works with every e-commerce platform.' },
  { icon: Ico.chart,  iconBg: 'bg-emerald-50 text-emerald-600', title: 'Price Analytics',       desc: 'Charts, trends, linear regression forecasting, and full historical price data.' },
  { icon: Ico.bell,   iconBg: 'bg-amber-50 text-amber-600',   title: 'Smart Alerts',           desc: '10 trigger types — price drops, price wars, out-of-stock, new competitors and more.' },
  { icon: Ico.clock,  iconBg: 'bg-red-50 text-red-500',       title: 'Automated Monitoring',   desc: 'Set schedules and let Celery handle scraping automatically around the clock.' },
  { icon: Ico.shield, iconBg: 'bg-gray-100 text-gray-500',    title: 'Repricing Rules',        desc: 'Five strategies — match lowest, undercut, margin-based, dynamic, and MAP protected.' },
];

const QUICK_LINKS = [
  { href: '/products/add',  label: 'Add Product',         color: 'bg-blue-600 hover:bg-blue-700',    icon: Ico.plus },
  { href: '/integrations',  label: 'Import Products',     color: 'bg-violet-600 hover:bg-violet-700', icon: Ico.box },
  { href: '/competitors',   label: 'Manage Competitors',  color: 'bg-emerald-600 hover:bg-emerald-700', icon: Ico.globe },
  { href: '/alerts',        label: 'Set Up Alerts',       color: 'bg-amber-500 hover:bg-amber-600',   icon: Ico.bell },
];

export default function Home() {
  const [stats, setStats]           = useState({ products: 0, competitors: 0, matches: 0 });
  const [recent, setRecent]         = useState([]);
  const [loading, setLoading]       = useState(true);
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    loadData();
    // Delay wizard check until after client hydration
    setShowWizard(shouldShowOnboarding());
  }, []);

  const loadData = async () => {
    try {
      const [products, competitors] = await Promise.all([
        api.getProducts(),
        api.getCompetitors(),
      ]);
      const totalMatches = products.reduce((sum, p) => sum + (p.competitor_count || 0), 0);
      setStats({ products: products.length, competitors: competitors.length, matches: totalMatches });
      setRecent(products.slice(0, 5));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const isNew = !loading && stats.products === 0;

  return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">

        {/* ── Onboarding wizard (new users) ─────────────────────────── */}
        {isNew && showWizard && (
          <OnboardingWizard
            onDismiss={() => {
              setShowWizard(false);
              loadData(); // refresh stats in case they created something
            }}
          />
        )}

        {/* ── Hero banner (only shown when no wizard / has products) ── */}
        {(!isNew || !showWizard) && (
          <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl p-6 lg:p-8 text-white relative overflow-hidden">
            <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle at 70% 50%, white 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
            <div className="relative">
              <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-full px-3 py-1 text-xs font-medium mb-3">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Real-time competitive intelligence
              </div>
              <h1 className="text-2xl lg:text-3xl font-bold mb-2">
                {isNew ? 'Welcome to MarketIntel' : 'Good to see you back'}
              </h1>
              <p className="text-blue-100 text-sm max-w-xl">
                {isNew
                  ? 'Start by adding a product to monitor, then add competitor websites to track.'
                  : `You're monitoring ${stats.products} product${stats.products !== 1 ? 's' : ''} across ${stats.competitors} competitor${stats.competitors !== 1 ? 's' : ''}.`
                }
              </p>
              {isNew && (
                <div className="flex flex-wrap gap-3 mt-4">
                  <Link href="/products/add" className="inline-flex items-center gap-2 px-4 py-2 bg-white text-blue-700 rounded-xl text-sm font-semibold hover:bg-blue-50 transition-colors">
                    {Ico.plus} Add first product
                  </Link>
                  <Link href="/integrations" className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-sm font-medium transition-colors">
                    Import from XML / WooCommerce
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Stats row ──────────────────────────────────────────────── */}
        {!loading && (
          <div className="grid grid-cols-3 gap-4">
            <StatCard
              label="Products"
              value={stats.products}
              color="blue"
              icon={Ico.box}
              href="/products"
            />
            <StatCard
              label="Competitors"
              value={stats.competitors}
              color="violet"
              icon={Ico.globe}
              href="/competitors"
            />
            <StatCard
              label="Price Matches"
              value={stats.matches}
              color="emerald"
              icon={Ico.chart}
              href="/dashboard"
            />
          </div>
        )}

        {loading && (
          <div className="grid grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-white rounded-2xl border border-gray-100 animate-pulse" />)}
          </div>
        )}

        {/* ── Quick links ─────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {QUICK_LINKS.map((l, i) => (
            <Link key={i} href={l.href} className={`flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium text-white transition-colors ${l.color}`}>
              {l.icon} {l.label}
            </Link>
          ))}
        </div>

        {/* ── Recent products ─────────────────────────────────────────── */}
        {recent.length > 0 && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-50 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-900">Recent Products</h2>
              <Link href="/products" className="text-xs text-blue-600 hover:underline font-medium flex items-center gap-1">
                View all {Ico.arrow}
              </Link>
            </div>
            <div className="divide-y divide-gray-50">
              {recent.map((p) => (
                <Link key={p.id} href={`/products/${p.id}`} className="flex items-center justify-between px-5 py-3 hover:bg-gray-50 transition-colors group">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate group-hover:text-blue-600 transition-colors">{p.title}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {p.brand && <span className="mr-2">{p.brand}</span>}
                      {p.competitor_count || 0} match{(p.competitor_count || 0) !== 1 ? 'es' : ''}
                    </p>
                  </div>
                  <span className="text-gray-300 group-hover:text-blue-400 transition-colors ml-3">{Ico.arrow}</span>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* ── Feature grid ─────────────────────────────────────────────── */}
        <div>
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Platform Features</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f, i) => (
              <div key={i} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex items-start gap-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${f.iconBg}`}>{f.icon}</div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{f.title}</p>
                  <p className="text-xs text-gray-500 mt-1 leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Reopen wizard button (for returning new users) ──────────── */}
        {isNew && !showWizard && (
          <button
            onClick={() => setShowWizard(true)}
            className="w-full py-3 border border-dashed border-blue-200 rounded-2xl text-sm text-blue-600 hover:bg-blue-50 hover:border-blue-300 transition-colors font-medium"
          >
            Reopen setup guide
          </button>
        )}

      </div>
    </Layout>
  );
}
