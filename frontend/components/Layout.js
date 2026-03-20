import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../context/AuthContext';
import { usePwa } from '../context/PwaContext';
import usePriceEvents from '../lib/usePriceEvents';

// --- TIER CONFIG ---
const TIER = {
  free:       { pill: 'bg-white/10 text-white/70',        label: 'Free'       },
  pro:        { pill: 'bg-amber-500/20 text-amber-300',   label: 'Pro'        },
  business:   { pill: 'bg-amber-500/30 text-amber-200',   label: 'Business'   },
  enterprise: { pill: 'bg-orange-500/30 text-orange-200', label: 'Enterprise' },
};

// --- ICONS ---
const Icon = {
  home:        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>,
  products:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" /></svg>,
  chart:       <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  lightning:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  bell:        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>,
  users:       <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>,
  link:        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>,
  clock:       <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  trend:       <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>,
  tag:         <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>,
  globe:       <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>,
  gear:        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>,
  plus:        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  plusSm:      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  search:      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>,
  logout:      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>,
  upgrade:     <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  chevronDown: <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>,
  bookmark:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" /></svg>,
  activity:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" /></svg>,
  forecast:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" /></svg>,
  key:         <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" /></svg>,
  download:    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>,
  wifi_off:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M18.364 5.636a9 9 0 010 12.728M15.536 8.464a5 5 0 010 7.072M12 12h.01M3.636 18.364a9 9 0 010-12.728M6.464 15.536a5 5 0 010-7.072" /></svg>,
};

// --- NAV ITEMS ---
const NAV_ITEMS = [
  { href: '/',                 label: 'Home',           icon: Icon.home,      match: (p) => p === '/' },
  { href: '/products',         label: 'Products',       icon: Icon.products,  match: (p) => p.startsWith('/products') },
  { href: '/command-center',   label: 'Command Center', icon: Icon.lightning, match: (p) => p.startsWith('/command-center') },
  { href: '/saved-views',      label: 'Saved Views',    icon: Icon.bookmark,  match: (p) => p.startsWith('/saved-views') },
  { href: '/dashboard',        label: 'Comparison',     icon: Icon.chart,     match: (p) => p.startsWith('/dashboard') },
  { href: '/insights',         label: 'Intelligence',   icon: Icon.trend,     match: (p) => p.startsWith('/insights') },
  { href: '/activity',         label: 'Activity Log',   icon: Icon.activity,  match: (p) => p.startsWith('/activity') },
  { href: '/forecasting',      label: 'Forecasting',    icon: Icon.forecast,  match: (p) => p.startsWith('/forecasting') },
  { href: '/alerts',           label: 'Alerts',         icon: Icon.bell,      match: (p) => p.startsWith('/alerts') },
  { href: '/competitor-intel', label: 'Rival Profiles', icon: Icon.users,     match: (p) => p.startsWith('/competitor-intel') },
  { href: '/competitor-dna',  label: 'Strategy DNA',   icon: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>, match: (p) => p.startsWith('/competitor-dna') },
  { href: '/integrations',     label: 'Integrations',   icon: Icon.link,      match: (p) => p.startsWith('/integrations') },
  { href: '/scheduler',        label: 'Scheduler',      icon: Icon.clock,     match: (p) => p.startsWith('/scheduler') },
];

const TICKER = [
  { s: 'AMZN',  p: '189.42', c: '+1.23', up: true  },
  { s: 'WMT',   p: '67.88',  c: '-0.45', up: false },
  { s: 'SHOP',  p: '94.11',  c: '+2.87', up: true  },
  { s: 'EBAY',  p: '44.33',  c: '+0.12', up: true  },
  { s: 'TGT',   p: '139.50', c: '-1.09', up: false },
  { s: 'COST',  p: '891.77', c: '+4.21', up: true  },
  { s: 'ETSY',  p: '52.30',  c: '-0.88', up: false },
  { s: 'CHEWY', p: '28.14',  c: '+0.67', up: true  },
];

export default function Layout({ children }) {
  const router = useRouter();
  const { user, tier, logout } = useAuth();
  const { pwa, promptInstall } = usePwa();
  const [collapsed, setCollapsed] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const prices = usePriceEvents();
  const W = collapsed ? 80 : 240;

  useEffect(() => {
    document.body.style.backgroundColor = 'var(--color-light-background)';
    document.documentElement.style.setProperty('--color-light-background', '#F0F0FA');
    document.documentElement.style.setProperty('--color-light-surface', '#FFFFFF');
    document.documentElement.style.setProperty('--color-light-border', '#E0E0E0');
    document.documentElement.style.setProperty('--color-light-text', '#0A0A0F');
    document.documentElement.style.setProperty('--color-light-textMuted', '#606080');
    document.documentElement.style.setProperty('--color-amber-500', '#F59E0B');
    document.documentElement.style.setProperty('--color-ink-900', '#0A0A0F');
    document.documentElement.style.setProperty('--color-ink-300', '#606080');
    document.documentElement.style.setProperty('--color-ink-400', '#3A3A58');
    document.documentElement.style.setProperty('--color-signal-up', '#10B981');
    document.documentElement.style.setProperty('--color-signal-down', '#EF4444');
    document.documentElement.style.setProperty('--color-glass-light', 'rgba(255, 255, 255, 0.15)');
    document.documentElement.style.setProperty('--color-glass-borderLight', 'rgba(255, 255, 255, 0.2)');
    document.documentElement.style.setProperty('--box-shadow-glass', '0 4px 24px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.1)');
    document.documentElement.style.setProperty('--box-shadow-gradient-lg', '0 6px 28px rgba(245,158,11,0.35)');
  }, []);

  return (
    <div className="w-full h-screen flex bg-light-background text-light-text">
      {/* --- Left Nav --- */}
      <div style={{ width: W, transition: 'width 0.2s ease-out' }} className="flex-shrink-0 bg-glass-light border-r border-glass-borderLight flex flex-col z-20 backdrop-blur-lg">
        <div style={{ height: 64 }} className="flex-shrink-0 flex items-center justify-center px-5 border-b border-glass-borderLight">
          <Link href="/" className="flex items-center gap-2.5">
            <img src="/favicon.svg" className="w-7 h-7" />
            {!collapsed && <span className="font-display font-bold text-xl text-amber-500 tracking-tighter">MarketIntel</span>}
          </Link>
        </div>

        <div className="flex-grow py-2.5 border-b border-glass-borderLight overflow-y-auto">
          {NAV_ITEMS.map(item => {
            const isActive = item.match(router.pathname);
            return (
              <Link href={item.href} key={item.href} className={`flex items-center gap-3.5 px-6 py-2.5 text-sm font-medium transition-all duration-150 ease-out ${isActive ? 'text-light-text' : 'text-light-textMuted hover:text-light-text'}`}>
                <div className={`w-1 h-6 rounded-full transition-all duration-150 ease-out ${isActive ? 'bg-amber-500' : 'bg-transparent'}`}></div>
                <div className={`transition-all duration-150 ease-out ${isActive ? 'text-amber-500' : ''}`}>{item.icon}</div>
                {!collapsed && <span className="whitespace-nowrap">{item.label}</span>}
              </Link>
            );
          })}
        </div>

        <div className="flex-shrink-0 py-2.5">
          <Link href="/settings" className={`flex items-center gap-3.5 px-6 py-2.5 text-sm font-medium transition-all duration-150 ease-out ${router.pathname.startsWith('/settings') ? 'text-light-text' : 'text-light-textMuted hover:text-light-text'}`}>
            <div className={`w-1 h-6 rounded-full transition-all duration-150 ease-out ${router.pathname.startsWith('/settings') ? 'bg-amber-500' : 'bg-transparent'}`}></div>
            <div className={`transition-all duration-150 ease-out ${router.pathname.startsWith('/settings') ? 'text-amber-500' : ''}`}>{Icon.gear}</div>
            {!collapsed && <span className="whitespace-nowrap">Settings</span>}
          </Link>
        </div>
      </div>

      {/* --- Main Content --- */}
      <div className="flex-grow flex flex-col bg-light-background">
        <div style={{ height: 64 }} className="flex-shrink-0 border-b border-light-border flex items-center px-6 justify-between gap-5 bg-glass-light backdrop-blur-lg">
          <div className="flex items-center gap-3">
            <button onClick={() => setCollapsed(!collapsed)} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors">
              <svg className="w-5 h-5 text-light-textMuted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" /></svg>
            </button>
            <span className="text-sm text-light-textMuted">Welcome back, <span className="font-semibold text-light-text">{user?.name}</span></span>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={() => setShowSearch(true)} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors">
              {Icon.search}
            </button>
            <button className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors">
              {Icon.bell}
            </button>
            <div className="w-px h-6 bg-light-border"></div>
            <div className={`text-xs font-mono tracking-widest uppercase px-2.5 py-1 rounded-full ${TIER[tier]?.pill}`}>{TIER[tier]?.label}</div>
            <button onClick={logout} className="text-xs text-light-textMuted hover:text-light-text transition-colors">Logout</button>
          </div>
        </div>

        <div className="flex-grow overflow-y-auto p-6 bg-light-background">
          {children}
        </div>

        <div style={{ height: 32 }} className="flex-shrink-0 border-t border-glass-borderLight bg-glass-light backdrop-blur-lg z-10 flex items-center px-6 gap-5 overflow-hidden">
          <span className="text-xs font-mono uppercase text-ink-300">Live Market Data</span>
          <div className="flex-grow flex items-center gap-5 animate-ticker">
            {[...TICKER, ...TICKER].map((t, i) => (
              <div key={i} className="flex items-center gap-2.5 flex-shrink-0">
                <span className="text-xs font-mono text-light-textMuted">{t.s}</span>
                <span className="text-xs font-semibold text-light-text">{t.p}</span>
                <span className={`text-xs font-semibold ${t.up ? 'text-signal-up' : 'text-signal-down'}`}>{t.c}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
