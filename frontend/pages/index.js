import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import api from '../lib/api';

// ── Stat card ──────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, href, icon, loading }) {
  if (loading) {
    return (
      <div style={{
        background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '12px',
        padding: '20px 24px', height: '96px', animation: 'skeleton 1.4s ease-in-out infinite',
        backgroundImage: 'linear-gradient(90deg, #F3F4F6 25%, #E5E7EB 50%, #F3F4F6 75%)',
        backgroundSize: '200% 100%',
      }} />
    );
  }

  const card = (
    <div style={{
      background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '12px',
      padding: '20px 24px', display: 'flex', alignItems: 'center', gap: '16px',
      transition: 'border-color 0.15s, box-shadow 0.15s',
      cursor: href ? 'pointer' : 'default',
    }}
      onMouseEnter={href ? e => { e.currentTarget.style.borderColor = '#BFDBFE'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(37,99,235,0.08)'; } : undefined}
      onMouseLeave={href ? e => { e.currentTarget.style.borderColor = '#E5E7EB'; e.currentTarget.style.boxShadow = 'none'; } : undefined}
    >
      {icon && (
        <div style={{
          width: '42px', height: '42px', borderRadius: '10px', background: '#EFF6FF',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, color: '#2563EB',
        }}>
          {icon}
        </div>
      )}
      <div>
        <div style={{ fontSize: '26px', fontWeight: 700, color: '#111827', lineHeight: 1, letterSpacing: '-0.02em' }}>
          {value.toLocaleString()}
        </div>
        <div style={{ fontSize: '13px', color: '#6B7280', marginTop: '4px' }}>{label}</div>
        {sub && <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '2px' }}>{sub}</div>}
      </div>
      {href && (
        <div style={{ marginLeft: 'auto', color: '#9CA3AF' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
        </div>
      )}
    </div>
  );

  return href ? <Link href={href} style={{ textDecoration: 'none', display: 'block' }}>{card}</Link> : card;
}

// ── Feature card ───────────────────────────────────────────────────────────
const FEATURES = [
  { title: 'AI Product Matching',   desc: 'Semantic matching across retailers by ASIN, model number, and keywords.',  color: '#2563EB', bg: '#EFF6FF' },
  { title: 'Smart Price Alerts',    desc: '10 trigger types — drops, wars, out-of-stock, new competitors, and more.',  color: '#7C3AED', bg: '#F5F3FF' },
  { title: 'Bulk Repricing',        desc: 'Five strategies with Shopify & WooCommerce sync. Set floors and ceilings.', color: '#059669', bg: '#ECFDF5' },
  { title: 'Forecasting Engine',    desc: 'Historical trend analysis and price forecasting with Redis caching.',        color: '#D97706', bg: '#FFFBEB' },
  { title: 'Competitor Discovery',  desc: 'Auto-discover competitor websites from your product catalogue.',             color: '#DC2626', bg: '#FEF2F2' },
  { title: 'Competitor DNA',        desc: 'Predict strikes, extract behavioural patterns, and simulate repricing.',     color: '#0891B2', bg: '#ECFEFF' },
];

const BoxIcon    = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>;
const GlobeIcon  = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20"/></svg>;
const ChartIcon  = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>;
const ArrowIcon  = <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>;

const QUICK_ACTIONS = [
  { href: '/products/add',  label: 'Add Product',        icon: BoxIcon   },
  { href: '/integrations',  label: 'Import Products',    icon: BoxIcon   },
  { href: '/competitors',   label: 'Add Competitor',     icon: GlobeIcon },
  { href: '/alerts',        label: 'Set Up Alerts',      icon: ChartIcon },
];

export default function Home() {
  const [stats,   setStats]   = useState({ products: 0, competitors: 0, matches: 0 });
  const [recent,  setRecent]  = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [products, competitors] = await Promise.all([api.getProducts(), api.getCompetitors()]);
        const totalMatches = products.reduce((s, p) => s + (p.competitor_count || 0), 0);
        setStats({ products: products.length, competitors: competitors.length, matches: totalMatches });
        setRecent(products.slice(0, 6));
      } catch { /* ignore */ } finally {
        setLoading(false);
      }
    })();
  }, []);

  const isEmpty = !loading && stats.products === 0;

  return (
    <Layout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

        {/* ── Welcome / Hero ──────────────────────────────────────────── */}
        <div style={{
          background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '12px',
          padding: '28px 32px', position: 'relative', overflow: 'hidden',
        }}>
          {/* Subtle accent strip */}
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0, height: '3px',
            background: 'linear-gradient(90deg, #2563EB, #7C3AED)',
          }} />
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span style={{
                  width: '7px', height: '7px', borderRadius: '50%', background: '#10B981',
                  display: 'inline-block', animation: 'pulse-dot 2s ease-in-out infinite',
                }} />
                <span style={{ fontSize: '12px', color: '#10B981', fontWeight: 600 }}>Live monitoring active</span>
              </div>
              <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#111827', margin: 0, letterSpacing: '-0.01em' }}>
                {isEmpty ? 'Welcome to MarketIntel' : 'Overview'}
              </h1>
              <p style={{ fontSize: '14px', color: '#6B7280', marginTop: '4px', lineHeight: 1.6 }}>
                {isEmpty
                  ? 'Start by adding a product to monitor, then add competitor websites to track.'
                  : `Monitoring ${stats.products} product${stats.products !== 1 ? 's' : ''} across ${stats.competitors} competitor site${stats.competitors !== 1 ? 's' : ''}.`
                }
              </p>
            </div>
            {isEmpty && (
              <Link href="/products/add" style={{
                display: 'inline-flex', alignItems: 'center', gap: '7px',
                padding: '10px 20px', background: '#2563EB', color: '#FFFFFF',
                borderRadius: '8px', textDecoration: 'none', fontSize: '14px', fontWeight: 600,
                boxShadow: '0 1px 4px rgba(37,99,235,0.3)', whiteSpace: 'nowrap',
              }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Add first product
              </Link>
            )}
          </div>
        </div>

        {/* ── Stats ───────────────────────────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }} className="stats-grid">
          <StatCard label="Products Monitored" value={stats.products}   href="/products"    icon={BoxIcon}   loading={loading} />
          <StatCard label="Competitor Matches"  value={stats.matches}    href="/insights"    icon={ChartIcon} loading={loading} />
          <StatCard label="Tracked Websites"    value={stats.competitors} href="/competitors" icon={GlobeIcon} loading={loading} />
        </div>

        {/* ── Quick actions ────────────────────────────────────────────── */}
        <div>
          <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '12px' }}>Quick Actions</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }} className="actions-grid">
            {QUICK_ACTIONS.map((a) => (
              <Link key={a.href} href={a.href} legacyBehavior>
                <a style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  padding: '11px 14px', background: '#FFFFFF', border: '1px solid #E5E7EB',
                  borderRadius: '10px', textDecoration: 'none', fontSize: '13px',
                  fontWeight: 500, color: '#374151', transition: 'all 0.12s',
                }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = '#BFDBFE'; e.currentTarget.style.color = '#2563EB'; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = '#E5E7EB'; e.currentTarget.style.color = '#374151'; }}
                >
                  <span style={{ color: '#2563EB' }}>{a.icon}</span>
                  {a.label}
                </a>
              </Link>
            ))}
          </div>
        </div>

        {/* ── Recent products ──────────────────────────────────────────── */}
        {!loading && recent.length > 0 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', margin: 0 }}>Recent Products</h2>
              <Link href="/products" style={{ fontSize: '13px', color: '#2563EB', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
                View all {ArrowIcon}
              </Link>
            </div>
            <div style={{ background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '12px', overflow: 'hidden' }}>
              {recent.map((p, i) => (
                <Link key={p.id} href={`/products/${p.id}`} legacyBehavior>
                  <a
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '13px 20px', textDecoration: 'none',
                      borderBottom: i < recent.length - 1 ? '1px solid #F3F4F6' : 'none',
                      transition: 'background 0.1s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = '#F9FAFB'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: '14px', fontWeight: 500, color: '#111827', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {p.title}
                      </div>
                      <div style={{ fontSize: '12px', color: '#9CA3AF', marginTop: '2px' }}>
                        {p.brand ? `${p.brand} · ` : ''}{p.competitor_count || 0} match{(p.competitor_count || 0) !== 1 ? 'es' : ''}
                      </div>
                    </div>
                    <span style={{ color: '#D1D5DB', flexShrink: 0, marginLeft: '12px' }}>{ArrowIcon}</span>
                  </a>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* ── Empty state ──────────────────────────────────────────────── */}
        {isEmpty && (
          <div style={{
            background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '12px',
            padding: '48px 32px', textAlign: 'center',
          }}>
            <div style={{ width: '48px', height: '48px', background: '#EFF6FF', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', color: '#2563EB' }}>
              {BoxIcon}
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#111827', marginBottom: '8px' }}>No products yet</h3>
            <p style={{ fontSize: '14px', color: '#6B7280', lineHeight: 1.65, maxWidth: '360px', margin: '0 auto 24px' }}>
              Add your first product and MarketIntel will start tracking competitor prices automatically.
            </p>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <Link href="/products/add" style={{
                display: 'inline-flex', alignItems: 'center', gap: '7px',
                padding: '10px 20px', background: '#2563EB', color: '#FFFFFF',
                borderRadius: '8px', textDecoration: 'none', fontSize: '14px', fontWeight: 600,
              }}>
                Add a product
              </Link>
              <Link href="/integrations" style={{
                display: 'inline-flex', alignItems: 'center', gap: '7px',
                padding: '10px 20px', background: '#FFFFFF', color: '#374151',
                border: '1px solid #E5E7EB', borderRadius: '8px', textDecoration: 'none', fontSize: '14px', fontWeight: 500,
              }}>
                Import from WooCommerce / XML
              </Link>
            </div>
          </div>
        )}

        {/* ── Feature overview ─────────────────────────────────────────── */}
        <div>
          <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '12px' }}>Platform Features</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }} className="features-grid">
            {FEATURES.map((f, i) => (
              <div key={i} style={{
                background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '10px',
                padding: '18px 20px', display: 'flex', alignItems: 'flex-start', gap: '14px',
                transition: 'border-color 0.15s',
              }}
                onMouseEnter={e => e.currentTarget.style.borderColor = '#BFDBFE'}
                onMouseLeave={e => e.currentTarget.style.borderColor = '#E5E7EB'}
              >
                <div style={{
                  width: '36px', height: '36px', borderRadius: '8px',
                  background: f.bg, color: f.color,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                </div>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: '#111827', marginBottom: '4px' }}>{f.title}</div>
                  <div style={{ fontSize: '12px', color: '#6B7280', lineHeight: 1.55 }}>{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>

      <style jsx global>{`
        @keyframes skeleton {
          0%   { background-position: -200% 0; }
          100% { background-position:  200% 0; }
        }
        @media (max-width: 1024px) { .features-grid { grid-template-columns: repeat(2,1fr) !important; } }
        @media (max-width: 768px)  {
          .stats-grid   { grid-template-columns: 1fr !important; }
          .actions-grid { grid-template-columns: repeat(2,1fr) !important; }
          .features-grid{ grid-template-columns: 1fr !important; }
        }
      `}</style>
    </Layout>
  );
}
