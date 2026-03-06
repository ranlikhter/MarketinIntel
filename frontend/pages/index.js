import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import OnboardingWizard, { shouldShowOnboarding } from '../components/OnboardingWizard';
import api from '../lib/api';

function useCountUp(target, duration, start) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!start || target === 0) return;
    let startTime = null;
    const step = (ts) => {
      if (!startTime) startTime = ts;
      const p = Math.min((ts - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(Math.floor(eased * target));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, start, duration]);
  return value;
}

const FEATURES = [
  { tag: '01 — SCRAPING',   title: 'Amazon & Custom Sites',      body: 'Playwright-powered scraper with anti-bot fingerprinting. Add any website using CSS selectors — no limits.',                             accent: '#F59E0B' },
  { tag: '02 — MATCHING',   title: 'AI Product Matching',        body: 'Claude-powered semantic matching across retailers. ASIN, model number, and keyword correlation at scale.',                            accent: '#10B981' },
  { tag: '03 — STRATEGY',   title: 'Competitor DNA',             body: 'Predict competitor price strikes. Extract behavioral patterns, reprice simulation, and MAP violation tracking.',                     accent: '#818CF8' },
  { tag: '04 — ALERTS',     title: 'Smart Notifications',        body: 'Multi-channel alerts with quiet hours, snooze, and escalation. Price wars and OOS detection built in.',                              accent: '#F472B6' },
  { tag: '05 — ANALYTICS',  title: 'Forecasting Engine',         body: 'Historical trend analysis, price forecasting, and Redis-cached dashboards. CSV import for bulk data.',                               accent: '#34D399' },
  { tag: '06 — AUTOMATION', title: 'Bulk Repricing',             body: 'Rule-based repricing automation with Shopify + WooCommerce sync. Set floors, ceilings, and margins.',                               accent: '#FB923C' },
];

export default function Home() {
  const [stats, setStats] = useState({ products: 0, competitors: 0, matches: 0 });
  const [loading, setLoading] = useState(true);
  const [recentActivity, setRecentActivity] = useState([]);
  const [visible, setVisible] = useState(false);

  const products    = useCountUp(stats.products,    1000, visible);
  const competitors = useCountUp(stats.competitors, 1000, visible);
  const matches     = useCountUp(stats.matches,     1200, visible);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 300);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [prods, comps] = await Promise.all([api.getProducts(), api.getCompetitors()]);
        const totalMatches = prods.reduce((s, p) => s + (p.competitor_count || 0), 0);
        setStats({ products: prods.length, competitors: comps.length, matches: totalMatches });
        setRecentActivity(prods.slice(0, 6));
      } catch { /* ignore */ } finally {
        setLoading(false);
      }
    })();
  }, []);
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
  const styles = {
    blue:    { bg: 'rgba(37,99,235,0.12)',    border: 'rgba(37,99,235,0.2)',    text: '#60a5fa' },
    emerald: { bg: 'rgba(5,150,105,0.12)',    border: 'rgba(5,150,105,0.2)',    text: '#34d399' },
    violet:  { bg: 'rgba(124,58,237,0.12)',   border: 'rgba(124,58,237,0.2)',   text: '#a78bfa' },
    amber:   { bg: 'rgba(245,158,11,0.12)',   border: 'rgba(245,158,11,0.2)',   text: '#fbbf24' },
  }[color] || { bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.1)', text: '#9ca3af' };

  const inner = (
    <div className={`rounded-2xl p-5 flex items-center gap-4 transition-all ${href ? 'hover:scale-[1.02]' : ''}`}
      style={{ background: styles.bg, border: `1px solid ${styles.border}` }}>
      <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: `${styles.bg}`, color: styles.text, border: `1px solid ${styles.border}` }}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-white leading-none">{value}</p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
        {sub && <p className="text-xs mt-0.5" style={{ color: 'var(--text-dim)' }}>{sub}</p>}
      </div>
    </div>
  );

  return href ? <Link href={href}>{inner}</Link> : inner;
}

const FEATURES = [
  { icon: Ico.bolt,   color: { bg: 'rgba(37,99,235,0.15)',  border: 'rgba(37,99,235,0.2)',  text: '#60a5fa'  }, title: 'Real-time Scraping',    desc: 'On-demand Playwright scraping with anti-bot detection for Amazon and any custom site.' },
  { icon: Ico.globe,  color: { bg: 'rgba(124,58,237,0.15)', border: 'rgba(124,58,237,0.2)', text: '#a78bfa'  }, title: 'Any Website',            desc: 'Add any competitor with custom CSS selectors. Works with every e-commerce platform.' },
  { icon: Ico.chart,  color: { bg: 'rgba(5,150,105,0.15)',  border: 'rgba(5,150,105,0.2)',  text: '#34d399'  }, title: 'Price Analytics',        desc: 'Charts, trends, linear regression forecasting, and full historical price data.' },
  { icon: Ico.bell,   color: { bg: 'rgba(245,158,11,0.15)', border: 'rgba(245,158,11,0.2)', text: '#fbbf24'  }, title: 'Smart Alerts',           desc: '10 trigger types — price drops, price wars, out-of-stock, new competitors and more.' },
  { icon: Ico.clock,  color: { bg: 'rgba(249,115,22,0.15)', border: 'rgba(249,115,22,0.2)', text: '#fb923c'  }, title: 'Automated Monitoring',   desc: 'Set schedules and let Celery handle scraping automatically around the clock.' },
  { icon: Ico.shield, color: { bg: 'rgba(255,255,255,0.06)', border: 'rgba(255,255,255,0.1)', text: '#94a3b8' }, title: 'Repricing Rules',        desc: 'Five strategies — match lowest, undercut, margin-based, dynamic, and MAP protected.' },
];

const QUICK_LINKS = [
  { href: '/products/add',  label: 'Add Product',        icon: Ico.plus,  style: 'bg-amber-500 hover:bg-amber-400' },
  { href: '/integrations',  label: 'Import Products',    icon: Ico.box,   style: 'bg-blue-600 hover:bg-blue-500' },
  { href: '/competitors',   label: 'Manage Competitors', icon: Ico.globe, style: 'bg-violet-600 hover:bg-violet-500' },
  { href: '/alerts',        label: 'Set Up Alerts',      icon: Ico.bell,  style: 'bg-emerald-600 hover:bg-emerald-500' },
];

export default function Home() {
  const [stats, setStats]           = useState({ products: 0, competitors: 0, matches: 0 });
  const [recent, setRecent]         = useState([]);
  const [loading, setLoading]       = useState(true);
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    loadData();
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
      <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>

        {/* Hero */}
        <section style={{
          position: 'relative', overflow: 'hidden',
          background: '#111118', border: '1px solid #1E1E2E', borderRadius: '12px',
          padding: '56px 48px',
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }}>
          <div style={{ position: 'absolute', top: '-80px', right: '-80px', width: '400px', height: '400px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(245,158,11,0.12) 0%, transparent 70%)', pointerEvents: 'none' }} />

          <div style={{ position: 'relative', zIndex: 1, maxWidth: '680px' }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px',
              padding: '5px 12px', borderRadius: '20px',
              border: '1px solid rgba(245,158,11,0.3)', background: 'rgba(245,158,11,0.08)',
              marginBottom: '28px', animation: 'mi-fade-up 0.5s ease-out both',
            }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981', animation: 'mi-pulse 2s ease-in-out infinite', display: 'inline-block' }} />
              <span style={{ fontSize: '11px', color: '#F59E0B', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.08em' }}>
                REAL-TIME COMPETITIVE INTELLIGENCE
              </span>
      <div className="p-4 lg:p-6 space-y-5">

        {/* Onboarding wizard */}
        {isNew && showWizard && (
          <OnboardingWizard
            onDismiss={() => {
              setShowWizard(false);
              loadData();
            }}
          />
        )}

        {/* Hero banner */}
        {(!isNew || !showWizard) && (
          <div className="rounded-2xl p-6 lg:p-8 relative overflow-hidden"
            style={{
              background: 'linear-gradient(135deg, rgba(245,158,11,0.15) 0%, rgba(249,115,22,0.08) 50%, rgba(14,14,26,0) 100%)',
              border: '1px solid rgba(245,158,11,0.2)',
            }}>
            <div className="absolute inset-0 opacity-5" style={{ backgroundImage: 'radial-gradient(circle at 70% 50%, #f59e0b 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
            {/* Amber glow orb */}
            <div className="absolute -top-16 -right-16 w-64 h-64 rounded-full opacity-10" style={{ background: 'radial-gradient(circle, #f59e0b, transparent 70%)' }} />
            <div className="relative">
              <div className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium mb-3 text-amber-400"
                style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.2)' }}>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Real-time competitive intelligence
              </div>
              <h1 className="text-2xl lg:text-3xl font-bold mb-2 text-white">
                {isNew ? 'Welcome to MarketIntel' : 'Good to see you back'}
              </h1>
              <p className="text-sm max-w-xl" style={{ color: 'var(--text-muted)' }}>
                {isNew
                  ? 'Start by adding a product to monitor, then add competitor websites to track.'
                  : `You're monitoring ${stats.products} product${stats.products !== 1 ? 's' : ''} across ${stats.competitors} competitor${stats.competitors !== 1 ? 's' : ''}.`
                }
              </p>
              {isNew && (
                <div className="flex flex-wrap gap-3 mt-4">
                  <Link href="/products/add" className="inline-flex items-center gap-2 px-4 py-2 gradient-brand text-white rounded-xl text-sm font-semibold shadow-gradient hover:opacity-90 transition-opacity">
                    {Ico.plus} Add first product
                  </Link>
                  <Link href="/integrations" className="inline-flex items-center gap-2 px-4 py-2 text-white/70 hover:text-white rounded-xl text-sm font-medium transition-colors"
                    style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}>
                    Import from XML / WooCommerce
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}

            <h1 style={{
              fontFamily: 'Syne, sans-serif', fontWeight: 800,
              fontSize: 'clamp(30px, 4vw, 52px)', lineHeight: 1.05,
              letterSpacing: '-0.03em', color: '#F0F0FA', marginBottom: '20px',
              animation: 'mi-fade-up 0.5s ease-out 0.1s both',
            }}>
              Know Every Move<br />
              <span style={{ background: 'linear-gradient(90deg, #F59E0B, #FCD34D)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                Your Competitors Make.
              </span>
            </h1>

            <p style={{
              fontSize: '16px', color: '#9090B8', lineHeight: 1.7,
              marginBottom: '36px', maxWidth: '520px',
              animation: 'mi-fade-up 0.5s ease-out 0.2s both',
            }}>
              Track pricing across Amazon, Walmart, and any custom website.
              AI-powered matching, predictive strike analysis, and automated repricing — in one platform.
            </p>

            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', animation: 'mi-fade-up 0.5s ease-out 0.3s both' }}>
              <Link href="/products/add" legacyBehavior>
                <a style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '12px 24px', borderRadius: '8px', background: '#F59E0B', color: '#0A0A0F', textDecoration: 'none', fontWeight: 700, fontSize: '14px', fontFamily: 'Syne, sans-serif', boxShadow: '0 0 24px rgba(245,158,11,0.3)' }}>
                  + Track a Product
                </a>
              </Link>
              <Link href="/dashboard" legacyBehavior>
                <a style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '12px 24px', borderRadius: '8px', border: '1px solid #2A2A3E', color: '#9090B8', textDecoration: 'none', fontWeight: 500, fontSize: '14px' }}>
                  View Intelligence
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18l6-6-6-6" /></svg>
                </a>
              </Link>
            </div>
          </div>

          <div style={{ position: 'absolute', bottom: '20px', right: '24px', fontFamily: 'IBM Plex Mono, monospace', fontSize: '10px', color: '#3A3A58', letterSpacing: '0.1em' }}>
            v2.0 · INTELLIGENCE SUITE
          </div>
        </section>

        {/* Stats */}
        {loading ? (
          <SkeletonStats />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }} className="stats-grid">
            {[
              { label: 'Products Monitored', value: products,    href: '/products',    color: '#F59E0B' },
              { label: 'Competitor Matches', value: matches,     href: '/dashboard',   color: '#10B981' },
              { label: 'Tracked Websites',   value: competitors, href: '/competitors', color: '#818CF8' },
            ].map((s, i) => (
              <Link key={s.label} href={s.href} legacyBehavior>
                <a
                  style={{ display: 'block', textDecoration: 'none', background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px', padding: '24px 28px', transition: 'border-color 0.2s, box-shadow 0.2s', animation: `mi-fade-up 0.5s ease-out ${0.1 * i}s both` }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = s.color + '55'; e.currentTarget.style.boxShadow = `0 0 24px ${s.color}18`; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = '#1E1E2E'; e.currentTarget.style.boxShadow = 'none'; }}
                >
                  <div style={{ fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.08em', marginBottom: '12px' }}>{s.label.toUpperCase()}</div>
                  <div style={{ fontSize: '44px', fontFamily: 'Syne, sans-serif', fontWeight: 800, color: s.color, letterSpacing: '-0.04em', lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
                    {s.value.toLocaleString()}
                  </div>
                  <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '4px', color: '#3A3A58', fontSize: '11px' }}>
                    View all
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18l6-6-6-6" /></svg>
                  </div>
                </a>
              </Link>
        {/* Stats row */}
        {!loading && (
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Products"     value={stats.products}   color="blue"    icon={Ico.box}   href="/products" />
            <StatCard label="Competitors"  value={stats.competitors} color="violet"  icon={Ico.globe} href="/competitors" />
            <StatCard label="Price Matches" value={stats.matches}   color="emerald"  icon={Ico.chart} href="/dashboard" />
          </div>
        )}

        {loading && (
          <div className="grid grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-24 rounded-2xl animate-pulse" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }} />
            ))}
          </div>
        )}

        {/* Features */}
        <section>
          <div style={{ marginBottom: '20px', display: 'flex', alignItems: 'baseline', gap: '12px' }}>
            <h2 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '20px', color: '#F0F0FA', letterSpacing: '-0.02em', margin: 0 }}>Intelligence Suite</h2>
            <span style={{ fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace' }}>06 MODULES</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
            {FEATURES.map((f, i) => (
              <div key={i}
                style={{ background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px', padding: '24px', transition: 'border-color 0.2s, transform 0.2s', animation: `mi-fade-up 0.5s ease-out ${0.05 * i}s both` }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = f.accent + '44'; e.currentTarget.style.transform = 'translateY(-2px)'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#1E1E2E'; e.currentTarget.style.transform = 'none'; }}
              >
                <div style={{ fontSize: '10px', color: f.accent, fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '12px' }}>{f.tag}</div>
                <h3 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: '#F0F0FA', letterSpacing: '-0.01em', marginBottom: '8px' }}>{f.title}</h3>
                <p style={{ fontSize: '13px', color: '#606080', lineHeight: 1.65, margin: 0 }}>{f.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Recent Products */}
        {!loading && recentActivity.length > 0 && (
          <section>
            <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h2 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '20px', color: '#F0F0FA', letterSpacing: '-0.02em', margin: 0 }}>Recent Products</h2>
              <Link href="/products" legacyBehavior>
                <a style={{ fontSize: '11px', color: '#F59E0B', textDecoration: 'none', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  VIEW ALL <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M9 18l6-6-6-6" /></svg>
                </a>
              </Link>
            </div>
            <div style={{ background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px', overflow: 'hidden' }}>
              {recentActivity.map((product, i) => (
                <Link key={product.id} href={`/products/${product.id}`} legacyBehavior>
                  <a
                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', textDecoration: 'none', borderBottom: i < recentActivity.length - 1 ? '1px solid #1E1E2E' : 'none', transition: 'background 0.15s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(245,158,11,0.04)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flex: 1, minWidth: 0 }}>
                      <div style={{ width: '32px', height: '32px', borderRadius: '6px', background: '#1E1E2E', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: '11px', fontFamily: 'IBM Plex Mono, monospace', color: '#606080' }}>
                        {String(i + 1).padStart(2, '0')}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: '13.5px', fontWeight: 500, color: '#F0F0FA', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{product.title}</div>
                        <div style={{ fontSize: '11px', color: '#606080', marginTop: '2px', fontFamily: 'IBM Plex Mono, monospace' }}>
                          {product.brand ? `${product.brand} · ` : ''}{product.competitor_count || 0} matches
                        </div>
                      </div>
                    </div>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3A3A58" strokeWidth="2"><path d="M9 18l6-6-6-6" /></svg>
                  </a>
        {/* Quick links */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {QUICK_LINKS.map((l, i) => (
            <Link key={i} href={l.href} className={`flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium text-white transition-all hover:scale-[1.02] ${l.style}`}>
              {l.icon} {l.label}
            </Link>
          ))}
        </div>

        {/* Recent products */}
        {recent.length > 0 && (
          <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <div className="px-5 py-4 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)' }}>
              <h2 className="text-sm font-semibold text-white">Recent Products</h2>
              <Link href="/products" className="text-xs text-amber-400 hover:text-amber-300 font-medium flex items-center gap-1 transition-colors">
                View all {Ico.arrow}
              </Link>
            </div>
            <div>
              {recent.map((p) => (
                <Link key={p.id} href={`/products/${p.id}`}
                  className="flex items-center justify-between px-5 py-3 group transition-colors"
                  style={{ borderBottom: '1px solid var(--border)' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate group-hover:text-amber-400 transition-colors">{p.title}</p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      {p.brand && <span className="mr-2">{p.brand}</span>}
                      {p.competitor_count || 0} match{(p.competitor_count || 0) !== 1 ? 'es' : ''}
                    </p>
                  </div>
                  <span className="text-white/20 group-hover:text-amber-400 transition-colors ml-3">{Ico.arrow}</span>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Empty state */}
        {stats.products === 0 && !loading && (
          <section style={{
            background: '#111118', border: '1px solid #1E1E2E', borderRadius: '12px',
            padding: '56px 48px', textAlign: 'center',
            backgroundImage: 'linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}>
            <div style={{ fontSize: '10px', color: '#3A3A58', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.12em', marginBottom: '16px' }}>NO PRODUCTS TRACKED YET</div>
            <h3 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '28px', color: '#F0F0FA', letterSpacing: '-0.02em', marginBottom: '12px' }}>Start Your Intelligence Feed</h3>
            <p style={{ color: '#606080', fontSize: '14px', lineHeight: 1.7, maxWidth: '400px', margin: '0 auto 28px' }}>
              Add your first product and MarketIntel will begin tracking competitor prices across every platform automatically.
            </p>
            <Link href="/products/add" legacyBehavior>
              <a style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '13px 28px', borderRadius: '8px', background: '#F59E0B', color: '#0A0A0F', textDecoration: 'none', fontWeight: 700, fontSize: '14px', fontFamily: 'Syne, sans-serif', boxShadow: '0 0 28px rgba(245,158,11,0.25)' }}>
                + Add First Product
              </a>
            </Link>
          </section>
        )}
      </div>

      <style jsx global>{`
        @media (max-width: 768px) { .stats-grid { grid-template-columns: 1fr !important; } }
        @keyframes mi-fade-up {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes mi-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.3; transform: scale(0.7); }
        }
      `}</style>
        {/* Feature grid */}
        <div>
          <h2 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-muted)' }}>Platform Features</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f, i) => (
              <div key={i} className="rounded-2xl p-5 flex items-start gap-4 transition-all hover:scale-[1.01]"
                style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                  style={{ background: f.color.bg, color: f.color.text, border: `1px solid ${f.color.border}` }}>
                  {f.icon}
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{f.title}</p>
                  <p className="text-xs mt-1 leading-relaxed" style={{ color: 'var(--text-muted)' }}>{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Reopen wizard */}
        {isNew && !showWizard && (
          <button
            onClick={() => setShowWizard(true)}
            className="w-full py-3 rounded-2xl text-sm text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 transition-colors font-medium"
            style={{ border: '1px dashed rgba(245,158,11,0.3)' }}
          >
            Reopen setup guide
          </button>
        )}

      </div>
    </Layout>
  );
}
