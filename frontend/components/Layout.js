import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';

const NAV = [
  {
    href: '/',
    label: 'Overview',
    exact: true,
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /></svg>,
  },
  {
    href: '/products',
    label: 'Products',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M20 7H4a2 2 0 00-2 2v10a2 2 0 002 2h16a2 2 0 002-2V9a2 2 0 00-2-2z" /><path d="M16 3H8l-2 4h12l-2-4z" /></svg>,
  },
  {
    href: '/competitors',
    label: 'Competitors',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20" /></svg>,
  },
  {
    href: '/insights',
    label: 'Intelligence',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  },
  {
    href: '/alerts',
    label: 'Alerts',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>,
  },
  {
    href: '/integrations',
    label: 'Integrations',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" /></svg>,
  },
  {
    href: '/settings',
    label: 'Settings',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" /></svg>,
  },
];

const BOTTOM_NAV = [NAV[0], NAV[1], null, NAV[4], NAV[6]];
const PlusIcon = <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>;
const ChevronLeft = <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>;

export default function Layout({ children }) {
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const width = collapsed ? 64 : 240;

  const isActive = (item) =>
    item.exact ? router.pathname === item.href : router.pathname.startsWith(item.href);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#F3F4F6' }}>
      <aside
        aria-label="Main navigation"
        style={{
          width,
          background: '#FFFFFF',
          borderRight: '1px solid #E5E7EB',
          transition: 'width 0.2s ease',
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          position: 'fixed',
          top: 0,
          left: 0,
          height: '100vh',
          zIndex: 50,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            padding: collapsed ? '16px 0' : '16px 16px',
            borderBottom: '1px solid #E5E7EB',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            minHeight: '56px',
            justifyContent: collapsed ? 'center' : 'flex-start',
          }}
        >
          <div style={{ width: '28px', height: '28px', background: '#2563EB', borderRadius: '7px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M2 11L6 6.5l3 3L14 3" stroke="#FFFFFF" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          {!collapsed && <span style={{ fontWeight: 700, fontSize: '15px', color: '#111827', letterSpacing: '-0.01em', whiteSpace: 'nowrap' }}>MarketIntel</span>}
        </div>

        <nav aria-label="Primary" style={{ flex: 1, padding: '10px 0', overflowY: 'auto', overflowX: 'hidden' }}>
          {NAV.map((item) => {
            const active = isActive(item);
            return (
              <Link key={item.href} href={item.href} legacyBehavior>
                <a
                  aria-label={collapsed ? item.label : undefined}
                  aria-current={active ? 'page' : undefined}
                  title={collapsed ? item.label : undefined}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: collapsed ? '10px 0' : '9px 14px',
                    margin: '2px 8px',
                    borderRadius: '8px',
                    textDecoration: 'none',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    background: active ? '#EFF6FF' : 'transparent',
                    color: active ? '#2563EB' : '#6B7280',
                    borderLeft: active ? '2px solid #2563EB' : '2px solid transparent',
                    transition: 'all 0.12s ease',
                    whiteSpace: 'nowrap',
                    fontWeight: active ? 600 : 400,
                  }}
                >
                  <span style={{ flexShrink: 0, display: 'flex' }}>{item.icon}</span>
                  {!collapsed && <span style={{ fontSize: '13.5px' }}>{item.label}</span>}
                </a>
              </Link>
            );
          })}
        </nav>

        <div style={{ borderTop: '1px solid #E5E7EB', padding: '10px 8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {!collapsed && (
            <Link href="/products/add" legacyBehavior>
              <a style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', padding: '9px 12px', borderRadius: '8px', background: '#2563EB', color: '#FFFFFF', textDecoration: 'none', fontSize: '13px', fontWeight: 600 }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                Add Product
              </a>
            </Link>
          )}
          <button
            onClick={() => setCollapsed((value) => !value)}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '8px', borderRadius: '8px', border: '1px solid #E5E7EB', background: 'transparent', color: '#9CA3AF', cursor: 'pointer', width: '100%', transition: 'all 0.12s' }}
          >
            <span style={{ transform: collapsed ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s', display: 'flex' }}>
              {ChevronLeft}
            </span>
          </button>
        </div>
      </aside>

      <div style={{ marginLeft: width, flex: 1, display: 'flex', flexDirection: 'column', transition: 'margin-left 0.2s ease', minWidth: 0 }}>
        <header style={{ height: '56px', borderBottom: '1px solid #E5E7EB', background: '#FFFFFF', display: 'flex', alignItems: 'center', padding: '0 20px', position: 'sticky', top: 0, zIndex: 40, gap: '12px' }}>
          <div style={{ flex: 1, maxWidth: '380px', position: 'relative' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" strokeWidth="2" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="search"
              placeholder="Search products, competitors..."
              aria-label="Search"
              autoComplete="off"
              style={{ width: '100%', background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '8px', padding: '7px 12px 7px 32px', fontSize: '13px', color: '#111827', outline: 'none', transition: 'border-color 0.15s, box-shadow 0.15s' }}
              onFocus={(e) => { e.target.style.borderColor = '#2563EB'; e.target.style.boxShadow = '0 0 0 3px rgba(37,99,235,0.08)'; e.target.style.background = '#FFFFFF'; }}
              onBlur={(e) => { e.target.style.borderColor = '#E5E7EB'; e.target.style.boxShadow = 'none'; e.target.style.background = '#F9FAFB'; }}
            />
          </div>

          <div style={{ flex: 1 }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#10B981', display: 'inline-block', animation: 'pulse-dot 2s ease-in-out infinite' }} />
            <span style={{ fontSize: '12px', color: '#6B7280', fontWeight: 500 }}>Live</span>
          </div>

          <Link href="/products/add" legacyBehavior>
            <a style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '7px 14px', borderRadius: '8px', background: '#2563EB', color: '#FFFFFF', textDecoration: 'none', fontSize: '13px', fontWeight: 600, boxShadow: '0 1px 4px rgba(37,99,235,0.25)' }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
              Add Product
            </a>
          </Link>
        </header>

        <main style={{ flex: 1, padding: '24px', maxWidth: '1400px', width: '100%', margin: '0 auto' }}>
          {children}
        </main>

        <footer style={{ borderTop: '1px solid #E5E7EB', padding: '12px 24px', background: '#FFFFFF', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', color: '#9CA3AF' }}>MarketIntel · Competitive Intelligence</span>
          <span style={{ fontSize: '12px', color: '#9CA3AF' }}>FastAPI + Next.js</span>
        </footer>
      </div>

      <nav
        aria-label="Mobile navigation"
        style={{ display: 'none', position: 'fixed', bottom: 0, left: 0, right: 0, background: '#FFFFFF', borderTop: '1px solid #E5E7EB', height: '60px', zIndex: 50 }}
        className="mobile-nav"
      >
        <div style={{ display: 'flex', alignItems: 'center', height: '100%', padding: '0 8px' }}>
          {BOTTOM_NAV.map((item) => {
            if (!item) {
              return (
                <div key="fab" style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
                  <Link href="/products/add" legacyBehavior>
                    <a aria-label="Add product" style={{ width: '48px', height: '48px', borderRadius: '50%', background: '#2563EB', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#FFFFFF', textDecoration: 'none', marginTop: '-20px', boxShadow: '0 4px 12px rgba(37,99,235,0.35)' }}>
                      {PlusIcon}
                    </a>
                  </Link>
                </div>
              );
            }

            const active = isActive(item);
            return (
              <Link key={item.href} href={item.href} legacyBehavior>
                <a aria-label={item.label} aria-current={active ? 'page' : undefined} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '3px', padding: '6px 0', textDecoration: 'none', color: active ? '#2563EB' : '#9CA3AF', transition: 'color 0.12s' }}>
                  {item.icon}
                  <span style={{ fontSize: '10px', fontWeight: active ? 600 : 400 }}>{item.label}</span>
                </a>
              </Link>
            );
          })}
        </div>
      </nav>

      <style jsx global>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.75); }
        }
        @media (max-width: 768px) {
          .mobile-nav { display: block !important; }
          main { padding-bottom: 72px !important; }
          aside { display: none !important; }
          aside + div { margin-left: 0 !important; }
        }
        nav a:hover {
          background: #F9FAFB !important;
          color: #374151 !important;
        }
      `}</style>
    </div>
  );
}
