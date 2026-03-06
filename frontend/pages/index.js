import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { SkeletonStats } from '../components/LoadingStates';
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
            </div>

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
    </Layout>
  );
}
