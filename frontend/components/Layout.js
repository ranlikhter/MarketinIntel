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

  const isActive = (item) =>
    item.exact ? router.pathname === item.href : router.pathname.startsWith(item.href);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#0A0A0F' }}>

      {/* ── Sidebar ── */}
      <aside style={{
        width: W, background: '#111118', borderRight: '1px solid #1E1E2E',
        transition: 'width 0.25s ease', flexShrink: 0, display: 'flex',
        flexDirection: 'column', position: 'fixed', top: 0, left: 0,
        height: '100vh', zIndex: 50, overflow: 'hidden',
      }}>

        {/* Logo */}
        <div style={{
          padding: collapsed ? '16px 0' : '16px 16px',
          borderBottom: '1px solid #1E1E2E',
          display: 'flex', alignItems: 'center', gap: '10px',
          minHeight: '58px', justifyContent: collapsed ? 'center' : 'flex-start',
        }}>
          <div style={{
            width: '28px', height: '28px', background: '#F59E0B',
            borderRadius: '6px', display: 'flex', alignItems: 'center',
            justifyContent: 'center', flexShrink: 0,
          }}>
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
              <path d="M2 11L6 6.5l3 3L14 3" stroke="#0A0A0F" strokeWidth="2.2"
                strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          {!collapsed && (
            <span style={{
              fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px',
              color: '#F0F0FA', letterSpacing: '-0.02em', whiteSpace: 'nowrap',
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
                    background: on ? 'rgba(245,158,11,0.1)' : 'transparent',
                    color: on ? '#F59E0B' : '#606080',
                    borderLeft: on ? '2px solid #F59E0B' : '2px solid transparent',
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
        <div style={{ borderTop: '1px solid #1E1E2E', padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {!collapsed && (
            <Link href="/products/add" legacyBehavior>
              <a style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                padding: '9px 12px', borderRadius: '8px', background: '#F59E0B',
                color: '#0A0A0F', textDecoration: 'none', fontSize: '13px', fontWeight: 700,
                fontFamily: 'Syne, sans-serif', letterSpacing: '0.01em',
              }}>
                <span style={{ fontSize: '16px', lineHeight: 1 }}>+</span>
                {' '}Add Product
              </a>
            </Link>
          )}
          <button
            onClick={() => setCollapsed((c) => !c)}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              padding: '8px', borderRadius: '8px', border: '1px solid #1E1E2E',
              background: 'transparent', color: '#606080', cursor: 'pointer',
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
          height: '46px', borderBottom: '1px solid #1E1E2E', background: '#111118',
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
                  fontFamily: 'IBM Plex Mono, monospace',
                  borderRight: '1px solid #1E1E2E', whiteSpace: 'nowrap',
                }}>
                  <span style={{ color: '#606080' }}>{t.s}</span>
                  <span style={{ color: '#F0F0FA', fontWeight: 500 }}>${t.p}</span>
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
            <span style={{ fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace' }}>
              LIVE
            </span>
          </div>
        </header>

        <main style={{ flex: 1, padding: '28px', maxWidth: '1400px', width: '100%', margin: '0 auto' }}>
          {children}
        </main>

        <footer style={{
          borderTop: '1px solid #1E1E2E', padding: '14px 28px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span style={{ fontSize: '11px', color: '#3A3A58', fontFamily: 'IBM Plex Mono, monospace' }}>
            MARKETINTEL · COMPETITIVE INTELLIGENCE PLATFORM
          </span>
          <span style={{ fontSize: '11px', color: '#3A3A58', fontFamily: 'IBM Plex Mono, monospace' }}>
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
        @keyframes mi-fade-up {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        nav a:hover {
          background: rgba(255,255,255,0.04) !important;
          color: #C8C8E0 !important;
        }
      `}</style>
    </div>
  );
}
