import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';

const NAV_ITEMS = [
  {
    href: '/', exact: true, label: 'Overview',
    d: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  },
  {
    href: '/dashboard', label: 'Intelligence',
    d: 'M2 12h4l3-9 4 18 3-9h6',
  },
  {
    href: '/products', label: 'Products',
    d: 'M20 7H4a2 2 0 00-2 2v10a2 2 0 002 2h16a2 2 0 002-2V9a2 2 0 00-2-2z',
  },
  {
    href: '/competitors', label: 'Competitors',
    d: 'M12 2a10 10 0 100 20A10 10 0 0012 2zM2 12h20',
  },
  {
    href: '/insights', label: 'Insights',
    d: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  },
  {
    href: '/integrations', label: 'Integrations',
    d: 'M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71',
  },
  {
    href: '/scheduler', label: 'Scheduler',
    d: 'M12 2a10 10 0 100 20A10 10 0 0012 2zM12 6v6l4 2',
  },
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

function NavIcon({ d }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

export default function Layout({ children }) {
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const W = collapsed ? 64 : 220;
import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../context/AuthContext';
import { usePwa } from '../context/PwaContext';
import usePriceEvents from '../lib/usePriceEvents';

// ─── TIER CONFIG ──────────────────────────────────────────────────────────────
const TIER = {
  free:       { pill: 'bg-white/10 text-white/70',        label: 'Free'       },
  pro:        { pill: 'bg-amber-500/20 text-amber-300',   label: 'Pro'        },
  business:   { pill: 'bg-amber-500/30 text-amber-200',   label: 'Business'   },
  enterprise: { pill: 'bg-orange-500/30 text-orange-200', label: 'Enterprise' },
};

// ─── ICONS ────────────────────────────────────────────────────────────────────
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

// ─── NAV ITEMS ────────────────────────────────────────────────────────────────
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
  { href: '/product-health',  label: 'Product Health',  icon: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" /></svg>, match: (p) => p.startsWith('/product-health') },
  { href: '/seller-intel',    label: 'Seller Intel',    icon: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>, match: (p) => p.startsWith('/seller-intel') },
  { href: '/keyword-ranks',   label: 'Keyword Ranks',  icon: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" /></svg>, match: (p) => p.startsWith('/keyword-ranks') },
  { href: '/competitors',      label: 'Competitors',    icon: Icon.globe,     match: (p) => p === '/competitors' || p === '/competitors/add' },
  { href: '/integrations',     label: 'Integrations',   icon: Icon.link,      match: (p) => p.startsWith('/integrations') },
  { href: '/scheduler',        label: 'Scheduler',      icon: Icon.clock,     match: (p) => p.startsWith('/scheduler') },
  { href: '/analytics',        label: 'Analytics',      icon: Icon.chart,     match: (p) => p.startsWith('/analytics') },
  { href: '/repricing',        label: 'Repricing',      icon: Icon.tag,       match: (p) => p.startsWith('/repricing') },
  { href: '/promotions',       label: 'Promotions',     icon: Icon.lightning, match: (p) => p.startsWith('/promotions') },
  { href: '/discovery',        label: 'Discovery',      icon: Icon.globe,     match: (p) => p.startsWith('/discovery') },
  { href: '/settings/team',    label: 'Team',           icon: Icon.users,     match: (p) => p.startsWith('/settings/team'),     group: 'Settings' },
  { href: '/settings/api-keys',label: 'API Keys',       icon: Icon.key,       match: (p) => p.startsWith('/settings/api-keys'), group: 'Settings' },
  { href: '/settings',         label: 'Settings',       icon: Icon.gear,      match: (p) => p === '/settings',                  group: 'Settings' },
];

const BOTTOM_NAV = [
  { href: '/products',       label: 'Products', icon: Icon.products  },
  { href: '/command-center', label: 'Battle',   icon: Icon.lightning },
  null, // FAB slot
  { href: '/alerts',         label: 'Alerts',   icon: Icon.bell      },
  { href: '/settings',       label: 'Settings', icon: Icon.gear      },
];

// ─── LOGO ─────────────────────────────────────────────────────────────────────
function Logo({ size = 'md' }) {
  const sz = size === 'sm' ? 'w-7 h-7 rounded-lg' : 'w-9 h-9 rounded-xl';
  return (
    <Link href="/" className="flex items-center gap-2.5 group">
      <div className={`${sz} gradient-brand flex items-center justify-center shadow-gradient shrink-0 transition-opacity group-hover:opacity-90`}>
        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
        </svg>
      </div>
      <span className={`font-bold ${size === 'sm' ? 'text-sm' : 'text-base'} text-white`}>
        Market<span className="gradient-text">Intel</span>
      </span>
    </Link>
  );
}

// ─── SIDEBAR USER DROPDOWN ────────────────────────────────────────────────────
function SidebarUser({ user, logout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  const isActive = (item) =>
    item.exact ? router.pathname === item.href : router.pathname.startsWith(item.href);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#F3F4F6' }}>

      {/* ── Sidebar ── */}
      <aside style={{
        width: W, background: '#FFFFFF', borderRight: '1px solid #E5E7EB',
        transition: 'width 0.25s ease', flexShrink: 0, display: 'flex',
        flexDirection: 'column', position: 'fixed', top: 0, left: 0,
        height: '100vh', zIndex: 50, overflow: 'hidden',
      }}>

        {/* Logo */}
        <div style={{
          padding: collapsed ? '16px 0' : '16px 16px',
          borderBottom: '1px solid #E5E7EB',
          display: 'flex', alignItems: 'center', gap: '10px',
          minHeight: '58px', justifyContent: collapsed ? 'center' : 'flex-start',
        }}>
          <div style={{
            width: '28px', height: '28px', background: '#2563EB',
            borderRadius: '6px', display: 'flex', alignItems: 'center',
            justifyContent: 'center', flexShrink: 0,
          }}>
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
              <path d="M2 11L6 6.5l3 3L14 3" stroke="#FFFFFF" strokeWidth="2.2"
                strokeLinecap="round" strokeLinejoin="round" />
            </svg>
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2.5 w-full px-2 py-1.5 rounded-xl hover:bg-white/5 transition-colors focus:outline-none"
      >
        <div className="w-8 h-8 rounded-xl gradient-brand flex items-center justify-center text-white text-xs font-bold shrink-0 shadow-gradient">
          {initials}
        </div>
        <div className="flex-1 min-w-0 text-left">
          <p className="text-sm font-semibold text-white truncate leading-tight">{user?.full_name || 'Account'}</p>
          <span className="text-[10px] font-medium text-white/40">{ts.label} plan</span>
        </div>
        <span className={`text-white/30 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}>
          {Icon.chevronDown}
        </span>
      </button>

      {open && (
        <div className="absolute bottom-full left-0 right-0 mb-2 rounded-2xl shadow-glass-lg overflow-hidden z-50 animate-fade-in"
          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-md)' }}>
          <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
            <p className="text-xs font-semibold text-white">{user?.full_name || 'Account'}</p>
            <p className="text-[11px] text-white/40 truncate mt-0.5">{user?.email}</p>
          </div>
          <div className="py-1">
            <Link href="/settings" onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-white/70 hover:text-white hover:bg-white/5 transition-colors">
              {Icon.gear} Settings
            </Link>
            <Link href="/pricing" onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 transition-colors">
              {Icon.upgrade} Upgrade
            </Link>
          </div>
          <div className="py-1" style={{ borderTop: '1px solid var(--border)' }}>
            <button onClick={() => { setOpen(false); logout(); }}
              className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors">
              {Icon.logout} Sign Out
            </button>
          </div>
          {!collapsed && (
            <span style={{
              fontWeight: 700, fontSize: '15px',
              color: '#111827', letterSpacing: '-0.02em', whiteSpace: 'nowrap',
            }}>
              MarketIntel
            </span>
          )}
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '10px 0', overflowY: 'auto', overflowX: 'hidden' }}>
          {NAV_ITEMS.map((item) => {
            const on = isActive(item);
            return (
              <Link key={item.href} href={item.href} legacyBehavior>
                <a
                  title={collapsed ? item.label : undefined}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    padding: collapsed ? '10px 0' : '9px 14px',
                    margin: '2px 8px', borderRadius: '8px', textDecoration: 'none',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    background: on ? '#EFF6FF' : 'transparent',
                    color: on ? '#2563EB' : '#6B7280',
                    borderLeft: on ? '2px solid #2563EB' : '2px solid transparent',
                    transition: 'all 0.15s ease', whiteSpace: 'nowrap',
                  }}
                >
                  <span style={{ flexShrink: 0 }}><NavIcon d={item.d} /></span>
                  {!collapsed && (
                    <span style={{ fontSize: '13px', fontWeight: on ? 600 : 400, letterSpacing: '0.01em' }}>
                      {item.label}
                    </span>
                  )}
                </a>
              </Link>
            );
          })}
        </nav>

        {/* Bottom */}
        <div style={{ borderTop: '1px solid #E5E7EB', padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {!collapsed && (
            <Link href="/products/add" legacyBehavior>
              <a style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                padding: '9px 12px', borderRadius: '8px', background: '#2563EB',
                color: '#FFFFFF', textDecoration: 'none', fontSize: '13px', fontWeight: 700,
                letterSpacing: '0.01em',
              }}>
                <span style={{ fontSize: '16px', lineHeight: 1 }}>+</span>
                {' '}Add Product
              </a>
      )}
    </div>
  );
}

// ─── TOPBAR AVATAR DROPDOWN ───────────────────────────────────────────────────
function TopbarAvatar({ user, logout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  const tier = user?.subscription_tier ?? 'free';
  const ts = TIER[tier] ?? TIER.free;
  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() ?? '?';

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-9 h-9 rounded-xl gradient-brand flex items-center justify-center text-white text-xs font-bold shadow-gradient hover:opacity-90 transition-opacity focus:outline-none focus:ring-2 focus:ring-amber-500/40 focus:ring-offset-1 focus:ring-offset-transparent"
      >
        {initials}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-60 rounded-2xl shadow-glass-lg z-50 overflow-hidden animate-fade-in"
          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-md)' }}>
          <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
            <p className="font-semibold text-white text-sm">{user?.full_name || 'Account'}</p>
            <p className="text-xs text-white/40 truncate mt-0.5">{user?.email}</p>
            <span className="inline-block mt-1.5 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400">
              {ts.label} Plan
            </span>
          </div>
          <div className="py-1">
            <Link href="/settings" onClick={() => setOpen(false)}
              className="flex items-center gap-3 px-4 py-2.5 text-sm text-white/70 hover:text-white hover:bg-white/5 transition-colors">
              {Icon.gear} Account Settings
            </Link>
            <Link href="/pricing" onClick={() => setOpen(false)}
              className="flex items-center gap-3 px-4 py-2.5 text-sm text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 transition-colors">
              {Icon.upgrade} Upgrade Plan
            </Link>
          )}
          <button
            onClick={() => setCollapsed((c) => !c)}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              padding: '8px', borderRadius: '8px', border: '1px solid #E5E7EB',
              background: 'transparent', color: '#6B7280', cursor: 'pointer',
              width: '100%', transition: 'all 0.15s',
            }}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
              style={{ transform: collapsed ? 'rotate(180deg)' : 'none', transition: 'transform 0.25s' }}>
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
        </div>
      </aside>

      {/* ── Main area ── */}
      <div style={{
        marginLeft: W, flex: 1, display: 'flex', flexDirection: 'column',
        transition: 'margin-left 0.25s ease', minWidth: 0,
      }}>

        {/* Topbar with live ticker */}
        <header style={{
          height: '46px', borderBottom: '1px solid #E5E7EB', background: '#FFFFFF',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 20px', position: 'sticky', top: 0, zIndex: 40,
          gap: '16px', overflow: 'hidden',
        }}>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <div style={{
              display: 'flex', animation: 'mi-ticker 40s linear infinite',
              width: 'max-content',
            }}>
              {[...TICKER, ...TICKER].map((t, i) => (
                <span key={i} style={{
                  display: 'inline-flex', alignItems: 'center', gap: '6px',
                  padding: '0 18px', fontSize: '11px',
                  fontFamily: 'monospace',
                  borderRight: '1px solid #E5E7EB', whiteSpace: 'nowrap',
                }}>
                  <span style={{ color: '#9CA3AF' }}>{t.s}</span>
                  <span style={{ color: '#111827', fontWeight: 500 }}>${t.p}</span>
                  <span style={{ color: t.up ? '#10B981' : '#EF4444' }}>{t.c}</span>
                </span>
              ))}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
            <span style={{
              width: '6px', height: '6px', borderRadius: '50%', background: '#10B981',
              display: 'inline-block', animation: 'mi-pulse 2s ease-in-out infinite',
            }} />
            <span style={{ fontSize: '11px', color: '#9CA3AF', fontFamily: 'monospace' }}>
              LIVE
            </span>
          </div>
        </header>

        <main style={{ flex: 1, padding: '28px', maxWidth: '1400px', width: '100%', margin: '0 auto' }}>
          {children}
        </main>

        <footer style={{
          borderTop: '1px solid #E5E7EB', padding: '14px 28px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: '#FFFFFF',
        }}>
          <span style={{ fontSize: '11px', color: '#9CA3AF', fontFamily: 'monospace' }}>
            MARKETINTEL · COMPETITIVE INTELLIGENCE PLATFORM
          </span>
          <span style={{ fontSize: '11px', color: '#9CA3AF', fontFamily: 'monospace' }}>
            FastAPI + Next.js
          </span>
        </footer>
      </div>

      <style jsx global>{`
        @keyframes mi-ticker {
          from { transform: translateX(0); }
          to   { transform: translateX(-50%); }
        }
        @keyframes mi-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.3; transform: scale(0.7); }
        }
        nav a:hover {
          background: #F9FAFB !important;
          color: #374151 !important;
        }
      `}</style>
          <div className="py-1" style={{ borderTop: '1px solid var(--border)' }}>
            <button onClick={() => { setOpen(false); logout(); }}
              className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors">
              {Icon.logout} Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── PWA INSTALL BUTTON ───────────────────────────────────────────────────────
function InstallButton() {
  const { canInstall, install } = usePwa();
  if (!canInstall) return null;
  return (
    <button
      onClick={install}
      className="flex items-center justify-center gap-1.5 w-full py-2 rounded-xl text-amber-400 text-xs font-semibold hover:bg-amber-500/10 transition-colors"
      style={{ border: '1px solid rgba(245,158,11,0.2)' }}
    >
      {Icon.download} Install App
    </button>
  );
}

// ─── SIDEBAR ──────────────────────────────────────────────────────────────────
function Sidebar({ pathname, user, logout }) {
  return (
    <aside className="hidden lg:flex flex-col fixed left-0 top-0 h-screen w-60 glass-sidebar z-30">
      {/* Logo */}
      <div className="px-5 py-5" style={{ borderBottom: '1px solid var(--border)' }}>
        <Logo />
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto scrollbar-hide px-3 py-4 space-y-0.5">
        {NAV_ITEMS.filter(i => !i.group).map(item => {
          const active = item.match(pathname);
          return (
            <Link key={item.href} href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                active
                  ? 'gradient-brand text-white shadow-gradient'
                  : 'text-white/50 hover:text-white hover:bg-white/5'
              }`}>
              <span className={active ? 'text-white/90' : ''}>
                {item.icon}
              </span>
              {item.label}
            </Link>
          );
        })}

        {/* Settings group */}
        <div className="pt-3 pb-1">
          <div className="h-px mx-2" style={{ background: 'var(--border)' }} />
        </div>
        <p className="px-3 pt-2 pb-1 text-[10px] font-bold text-white/20 uppercase tracking-widest">Settings</p>
        {NAV_ITEMS.filter(i => i.group === 'Settings').map(item => {
          const active = item.match(pathname);
          return (
            <Link key={item.href} href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                active
                  ? 'gradient-brand text-white shadow-gradient'
                  : 'text-white/50 hover:text-white hover:bg-white/5'
              }`}>
              <span className={active ? 'text-white/90' : ''}>
                {item.icon}
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Add Product + Install */}
      <div className="px-3 pb-3 space-y-2">
        <Link href="/products/add"
          className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl gradient-brand text-white text-sm font-semibold shadow-gradient hover:opacity-90 transition-opacity">
          {Icon.plus} Add Product
        </Link>
        <InstallButton />
      </div>

      {/* User */}
      <div className="px-3 pb-4 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
        {user
          ? <SidebarUser user={user} logout={logout} />
          : <Link href="/auth/login" className="text-sm text-white/50 hover:text-white px-3 py-2 rounded-xl hover:bg-white/5 flex items-center transition-colors">Sign In</Link>
        }
      </div>
    </aside>
  );
}

// ─── TOPBAR ───────────────────────────────────────────────────────────────────
function Topbar({ user, logout }) {
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 lg:left-60 h-16 glass-topbar z-20 flex items-center px-4 sm:px-5 gap-3">
      {/* Mobile logo */}
      <div className="lg:hidden shrink-0">
        <Logo size="sm" />
      </div>

      {/* Desktop search */}
      <div className="hidden lg:flex flex-1 max-w-sm">
        <div className="relative w-full">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none">
            {Icon.search}
          </span>
          <input type="text" placeholder="Search products, competitors…"
            className="w-full pl-10 pr-4 py-2.5 text-sm glass-input rounded-xl focus:outline-none" />
        </div>
      </div>

      <div className="flex-1" />

      {/* Right */}
      <div className="flex items-center gap-2">
        <button onClick={() => setSearchOpen(s => !s)}
          className="lg:hidden p-2.5 rounded-xl text-white/40 hover:text-white hover:bg-white/5 transition-colors">
          {Icon.search}
        </button>
        {user
          ? <TopbarAvatar user={user} logout={logout} />
          : <Link href="/auth/login" className="px-4 py-2 text-sm font-semibold gradient-brand text-white rounded-xl shadow-gradient hover:opacity-90 transition-opacity">Sign In</Link>
        }
      </div>

      {/* Mobile search expand */}
      {searchOpen && (
        <div className="absolute top-full left-0 right-0 glass-topbar px-4 py-3 lg:hidden animate-fade-in">
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30">{Icon.search}</span>
            <input autoFocus type="text" placeholder="Search…"
              onBlur={() => setSearchOpen(false)}
              className="w-full pl-10 pr-4 py-2.5 text-sm glass-input rounded-xl focus:outline-none" />
          </div>
        </div>
      )}
    </header>
  );
}

// ─── BOTTOM NAV ───────────────────────────────────────────────────────────────
function BottomNav({ pathname }) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 lg:hidden glass-nav z-30 safe-bottom">
      <div className="flex items-center h-16 px-2">
        {BOTTOM_NAV.map((item, i) => {
          if (!item) {
            return (
              <div key="fab" className="flex-1 flex justify-center">
                <Link href="/products/add"
                  className="w-14 h-14 rounded-full gradient-brand flex items-center justify-center text-white shadow-gradient hover:opacity-90 active:scale-95 transition-all -mt-5">
                  {Icon.plusSm}
                </Link>
              </div>
            );
          }
          const active = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href}
              className={`flex-1 flex flex-col items-center gap-0.5 py-2 transition-colors ${
                active ? 'text-amber-400' : 'text-white/30 hover:text-white/60'
              }`}>
              {item.icon}
              <span className="text-[10px] font-semibold leading-none">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

// ─── ROOT LAYOUT ──────────────────────────────────────────────────────────────
export default function Layout({ children }) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { isOnline } = usePwa();
  const { pathname } = router;

  const [liveAlerts, setLiveAlerts] = useState([]);

  const handlePriceEvent = useCallback((ev) => {
    const id = Date.now();
    const alert = {
      id,
      product_title: ev.product_title,
      competitor:    ev.competitor,
      new_price:     ev.new_price,
      change_pct:    ev.change_pct,
      product_id:    ev.product_id,
    };
    setLiveAlerts(prev => [alert, ...prev].slice(0, 5));
    setTimeout(() => setLiveAlerts(prev => prev.filter(a => a.id !== id)), 8000);
  }, []);

  usePriceEvents({ onEvent: handlePriceEvent, enabled: !!user });

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-base)' }}>
      {/* Offline banner */}
      {!isOnline && (
        <div className="fixed top-0 inset-x-0 z-[9999] bg-amber-500/95 backdrop-blur-sm text-white text-sm font-medium text-center py-2 px-4 flex items-center justify-center gap-2">
          {Icon.wifi_off}
          You&apos;re offline — showing cached data
        </div>
      )}

      <Sidebar pathname={pathname} user={user} logout={logout} />
      <Topbar  user={user} logout={logout} />

      <main className="lg:pl-60 pt-16 pb-20 lg:pb-8 min-h-screen">
        {children}
      </main>

      <BottomNav pathname={pathname} />

      {/* Live price-change toasts */}
      {liveAlerts.length > 0 && (
        <div className="fixed bottom-24 lg:bottom-6 right-4 z-50 flex flex-col gap-2 max-w-xs w-full pointer-events-none">
          {liveAlerts.map(a => {
            const isDown = a.change_pct != null ? a.change_pct < 0 : null;
            return (
              <div key={a.id}
                className="pointer-events-auto rounded-2xl px-4 py-3 flex items-start gap-3 animate-fade-in"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-md)' }}>
                <span className="text-base shrink-0 mt-0.5">
                  {isDown === true ? '📉' : isDown === false ? '📈' : '💰'}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-white truncate">{a.competitor}</p>
                  <p className="text-xs text-white/40 truncate">{a.product_title}</p>
                  {a.new_price != null && (
                    <p className={`text-xs font-bold mt-0.5 ${isDown === true ? 'text-red-400' : isDown === false ? 'text-emerald-400' : 'text-white'}`}>
                      ${a.new_price.toFixed(2)}
                      {a.change_pct != null && (
                        <span className="font-normal ml-1 text-white/30">
                          ({a.change_pct > 0 ? '+' : ''}{a.change_pct.toFixed(1)}%)
                        </span>
                      )}
                    </p>
                  )}
                </div>
                <Link href={`/products/${a.product_id}`}
                  className="shrink-0 text-xs font-semibold text-amber-400 hover:text-amber-300 transition-colors">
                  View
                </Link>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
