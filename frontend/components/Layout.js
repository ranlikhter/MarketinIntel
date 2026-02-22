import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../context/AuthContext';

// ─── TIER CONFIG ──────────────────────────────────────────────────────────────
const TIER = {
  free:       { bg: 'bg-gray-100',   text: 'text-gray-600',   label: 'Free'       },
  pro:        { bg: 'bg-blue-100',   text: 'text-blue-700',   label: 'Pro'        },
  business:   { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Business'   },
  enterprise: { bg: 'bg-amber-100',  text: 'text-amber-700',  label: 'Enterprise' },
};

// ─── INLINE SVG ICONS ─────────────────────────────────────────────────────────
const Icon = {
  home: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>,
  products: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" /></svg>,
  chart: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  lightning: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  bell: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>,
  users: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>,
  link: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>,
  clock: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  trend: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>,
  tag:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>,
  globe: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>,
  gear: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>,
  plus: <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  search: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>,
  logout: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>,
  upgrade: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  logoChart: <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" /></svg>,
  chevronDown: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>,
};

// ─── SIDEBAR NAV ──────────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { href: '/',                label: 'Home',           icon: Icon.home,      match: (p) => p === '/'              },
  { href: '/products',        label: 'Products',       icon: Icon.products,  match: (p) => p.startsWith('/products') },
  { href: '/command-center',  label: 'Command Center', icon: Icon.lightning, match: (p) => p.startsWith('/command-center') },
  { href: '/dashboard',       label: 'Comparison',     icon: Icon.chart,     match: (p) => p.startsWith('/dashboard') },
  { href: '/insights',        label: 'Intelligence',   icon: Icon.trend,     match: (p) => p.startsWith('/insights') },
  { href: '/alerts',          label: 'Alerts',         icon: Icon.bell,      match: (p) => p.startsWith('/alerts') },
  { href: '/competitor-intel', label: 'Rival Profiles', icon: Icon.users, match: (p) => p.startsWith('/competitor-intel') },
  { href: '/competitors',      label: 'Competitors',    icon: Icon.globe, match: (p) => p === '/competitors' || p === '/competitors/add' },
  { href: '/integrations', label: 'Integrations', icon: Icon.link,      match: (p) => p.startsWith('/integrations') },
  { href: '/scheduler',    label: 'Scheduler',    icon: Icon.clock,     match: (p) => p.startsWith('/scheduler') },
  { href: '/analytics',    label: 'Analytics',    icon: Icon.trend,     match: (p) => p.startsWith('/analytics') },
  { href: '/repricing',    label: 'Repricing',    icon: Icon.tag,       match: (p) => p.startsWith('/repricing') },
  { href: '/discovery',    label: 'Discovery',    icon: Icon.globe,     match: (p) => p.startsWith('/discovery') },
];

const BOTTOM_NAV = [
  { href: '/products',        label: 'Products',  icon: Icon.products  },
  { href: '/command-center',  label: 'Battle',    icon: Icon.lightning },
  null, // FAB slot
  { href: '/alerts',          label: 'Alerts',    icon: Icon.bell      },
  { href: '/settings',   label: 'Settings',     icon: Icon.gear      },
];

// ─── LOGO ─────────────────────────────────────────────────────────────────────
function Logo({ size = 'md' }) {
  return (
    <Link href="/" className="flex items-center gap-2.5 group">
      <div className={`${size === 'sm' ? 'w-7 h-7' : 'w-9 h-9'} bg-blue-600 rounded-xl flex items-center justify-center shadow-sm group-hover:bg-blue-700 transition-colors shrink-0`}>
        {Icon.logoChart}
      </div>
      <span className={`font-bold text-gray-900 ${size === 'sm' ? 'text-sm' : 'text-base'}`}>
        Market<span className="text-blue-600">Intel</span>
      </span>
    </Link>
  );
}

// ─── USER DROPDOWN (sidebar) ──────────────────────────────────────────────────
function SidebarUser({ user, logout }) {
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
      <button onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2.5 w-full px-2 py-1.5 rounded-xl hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500/40">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white text-sm font-semibold shrink-0">
          {initials}
        </div>
        <div className="flex-1 min-w-0 text-left">
          <p className="text-sm font-medium text-gray-900 truncate leading-tight">{user?.full_name || 'Account'}</p>
          <span className={`text-xs font-medium px-1.5 rounded ${ts.bg} ${ts.text}`}>{ts.label}</span>
        </div>
        <span className={`text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}>{Icon.chevronDown}</span>
      </button>

      {open && (
        <div className="absolute bottom-full left-0 right-0 mb-2 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden z-50">
          <div className="px-4 py-2.5 border-b border-gray-50">
            <p className="text-xs text-gray-400 truncate">{user?.email}</p>
          </div>
          <div className="py-1">
            <Link href="/settings" onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors">
              {Icon.gear} Settings
            </Link>
            <Link href="/pricing" onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors">
              {Icon.upgrade} Upgrade
            </Link>
          </div>
          <div className="border-t border-gray-100 py-1">
            <button onClick={() => { setOpen(false); logout(); }}
              className="flex items-center gap-2.5 w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors">
              {Icon.logout} Sign Out
            </button>
          </div>
        </div>
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
      <button onClick={() => setOpen(o => !o)}
        className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white text-sm font-semibold shadow-sm hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1">
        {initials}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-xl shadow-xl border border-gray-100 z-50 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
            <p className="font-semibold text-gray-900 text-sm">{user?.full_name || 'Account'}</p>
            <p className="text-xs text-gray-400 truncate">{user?.email}</p>
            <span className={`inline-block mt-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${ts.bg} ${ts.text}`}>{ts.label} Plan</span>
          </div>
          <div className="py-1">
            <Link href="/settings" onClick={() => setOpen(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors">
              {Icon.gear} Account Settings
            </Link>
            <Link href="/pricing" onClick={() => setOpen(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors">
              {Icon.upgrade} Upgrade Plan
            </Link>
          </div>
          <div className="border-t border-gray-100 py-1">
            <button onClick={() => { setOpen(false); logout(); }} className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors">
              {Icon.logout} Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── SIDEBAR ──────────────────────────────────────────────────────────────────
function Sidebar({ pathname, user, logout }) {
  return (
    <aside className="hidden lg:flex flex-col fixed left-0 top-0 h-screen w-64 bg-white border-r border-gray-100 z-30">
      <div className="px-5 py-5 border-b border-gray-50">
        <Logo />
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const active = item.match(pathname);
          return (
            <Link key={item.href} href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${active ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'}`}>
              <span className={active ? 'text-blue-600' : 'text-gray-400'}>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}

        <div className="pt-3 pb-1">
          <div className="h-px bg-gray-100 mx-3" />
        </div>

        <Link href="/settings"
          className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${pathname.startsWith('/settings') ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'}`}>
          <span className={pathname.startsWith('/settings') ? 'text-blue-600' : 'text-gray-400'}>{Icon.gear}</span>
          Settings
        </Link>
      </nav>

      <div className="px-3 pb-3">
        <Link href="/products/add"
          className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition-colors shadow-sm">
          {Icon.plus} Add Product
        </Link>
      </div>

      <div className="px-3 pb-4 border-t border-gray-100 pt-3">
        {user
          ? <SidebarUser user={user} logout={logout} />
          : <Link href="/auth/login" className="text-sm text-gray-600 hover:text-gray-900 px-3 py-2 rounded-xl hover:bg-gray-50 flex items-center transition-colors">Sign In</Link>
        }
      </div>
    </aside>
  );
}

// ─── TOPBAR ───────────────────────────────────────────────────────────────────
function Topbar({ user, logout }) {
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 lg:left-64 h-16 bg-white border-b border-gray-100 z-20 flex items-center px-4 sm:px-5 gap-3">
      {/* Mobile logo */}
      <div className="lg:hidden shrink-0">
        <Logo size="sm" />
      </div>

      {/* Desktop search bar */}
      <div className="hidden lg:flex flex-1 max-w-xs">
        <div className="relative w-full">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">{Icon.search}</span>
          <input type="text" placeholder="Search products, competitors…"
            className="w-full pl-10 pr-4 py-2 text-sm bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-400 transition-shadow placeholder-gray-400" />
        </div>
      </div>

      <div className="flex-1" />

      {/* Right icons */}
      <div className="flex items-center gap-1">
        <button onClick={() => setSearchOpen(s => !s)}
          className="lg:hidden p-2 rounded-xl text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors">
          {Icon.search}
        </button>

        {user
          ? <TopbarAvatar user={user} logout={logout} />
          : <Link href="/auth/login" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-50 transition-colors">Sign In</Link>
        }
      </div>

      {/* Mobile search expand */}
      {searchOpen && (
        <div className="absolute top-full left-0 right-0 bg-white border-b border-gray-100 px-4 py-3 shadow-md lg:hidden">
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">{Icon.search}</span>
            <input autoFocus type="text" placeholder="Search products, competitors…"
              onBlur={() => setSearchOpen(false)}
              className="w-full pl-10 pr-4 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-400 transition-shadow placeholder-gray-400" />
          </div>
        </div>
      )}
    </header>
  );
}

// ─── BOTTOM NAV ───────────────────────────────────────────────────────────────
function BottomNav({ pathname }) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 lg:hidden bg-white border-t border-gray-100 z-30 safe-bottom">
      <div className="flex items-center h-16 px-2">
        {BOTTOM_NAV.map((item, i) => {
          if (!item) {
            return (
              <div key="fab" className="flex-1 flex justify-center">
                <Link href="/products/add"
                  className="w-14 h-14 rounded-full bg-gray-900 flex items-center justify-center text-white shadow-lg hover:bg-gray-800 active:scale-95 transition-all -mt-5">
                  {Icon.plus}
                </Link>
              </div>
            );
          }
          const active = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href}
              className={`flex-1 flex flex-col items-center gap-0.5 py-2 transition-colors ${active ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'}`}>
              {item.icon}
              <span className="text-[10px] font-medium leading-none">{item.label}</span>
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
  const { pathname } = router;

  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar pathname={pathname} user={user} logout={logout} />
      <Topbar user={user} logout={logout} />

      {/* lg:pl-64 = sidebar offset, pt-16 = topbar offset, pb-20 = bottom nav on mobile */}
      <main className="lg:pl-64 pt-16 pb-20 lg:pb-8 min-h-screen">
        {children}
      </main>

      <BottomNav pathname={pathname} />
    </div>
  );
}
