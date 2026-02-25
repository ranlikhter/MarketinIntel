/**
 * Price Report Page — printable / saveable as PDF
 * Navigate to /products/[id]/report?print=1 to auto-trigger print dialog
 */

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import api from '../../../lib/api';

function fmt(n) { return n != null ? `$${Number(n).toFixed(2)}` : '—'; }
function pct(a, b) { return a && b ? `${(((b - a) / a) * 100).toFixed(1)}%` : '—'; }

function PositionBadge({ position }) {
  if (!position) return null;
  const styles = {
    cheapest:    { bg: '#dcfce7', color: '#166534', label: 'Cheapest' },
    competitive: { bg: '#fef3c7', color: '#92400e', label: 'Competitive' },
    expensive:   { bg: '#fef9c3', color: '#854d0e', label: 'Expensive' },
    most_expensive:{ bg: '#fee2e2', color: '#991b1b', label: 'Most Expensive' },
  };
  const s = styles[position] || { bg: '#f3f4f6', color: '#374151', label: position };
  return (
    <span style={{ background: s.bg, color: s.color, padding: '2px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600 }}>
      {s.label}
    </span>
  );
}

export default function ProductReportPage() {
  const router = useRouter();
  const { id } = router.query;
  const [product, setProduct] = useState(null);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const printed = useRef(false);

  const today = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

  useEffect(() => {
    if (!id) return;
    Promise.all([api.getProduct(id), api.getProductMatches(id)])
      .then(([p, m]) => { setProduct(p); setMatches(m); })
      .catch(() => setError('Failed to load product data'))
      .finally(() => setLoading(false));
  }, [id]);

  // Auto-print when data is ready and ?print=1 is in URL
  useEffect(() => {
    if (!loading && product && router.query.print === '1' && !printed.current) {
      printed.current = true;
      setTimeout(() => window.print(), 400);
    }
  }, [loading, product, router.query.print]);

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', fontFamily: 'system-ui' }}>
      <p style={{ color: '#6b7280' }}>Loading report…</p>
    </div>
  );

  if (error || !product) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', fontFamily: 'system-ui' }}>
      <p style={{ color: '#ef4444' }}>{error || 'Product not found'}</p>
    </div>
  );

  const prices = matches.map(m => m.latest_price).filter(p => p != null);
  const lowestPrice = prices.length ? Math.min(...prices) : null;
  const avgPrice = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : null;
  const highestPrice = prices.length ? Math.max(...prices) : null;

  // Determine price position
  let pricePosition = null;
  if (product.my_price != null && lowestPrice != null) {
    if (product.my_price <= lowestPrice) pricePosition = 'cheapest';
    else if (product.my_price >= highestPrice) pricePosition = 'most_expensive';
    else if (product.my_price <= avgPrice) pricePosition = 'competitive';
    else pricePosition = 'expensive';
  }

  const inStock = matches.filter(m => m.stock_status === 'In Stock').length;

  return (
    <>
      <Head>
        <title>{product.title} — Price Report</title>
        <style>{`
          @media print {
            .no-print { display: none !important; }
            body { margin: 0; }
          }
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #fff; color: #1f2937; margin: 0; }
          * { box-sizing: border-box; }
        `}</style>
      </Head>

      {/* Print toolbar — hidden when printing */}
      <div className="no-print" style={{ position: 'sticky', top: 0, zIndex: 10, background: '#0e0e1a', borderBottom: '1px solid rgba(255,255,255,0.07)', padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 12 }}>
        <button
          onClick={() => window.print()}
          style={{ background: 'linear-gradient(135deg, #f59e0b, #f97316)', color: '#fff', border: 'none', padding: '8px 20px', borderRadius: 8, fontSize: 14, fontWeight: 600, cursor: 'pointer' }}
        >
          Print / Save as PDF
        </button>
        <button
          onClick={() => window.history.back()}
          style={{ background: 'transparent', color: '#9ca3af', border: '1px solid rgba(255,255,255,0.1)', padding: '8px 16px', borderRadius: 8, fontSize: 14, cursor: 'pointer' }}
        >
          ← Back
        </button>
        <span style={{ fontSize: 13, color: '#6b7280', marginLeft: 'auto' }}>
          Tip: In the print dialog, choose "Save as PDF" to download
        </span>
      </div>

      {/* Report body */}
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px' }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 32, paddingBottom: 24, borderBottom: '2px solid #f59e0b' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <div style={{ width: 32, height: 32, background: 'linear-gradient(135deg, #f59e0b, #f97316)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <svg width="20" height="20" fill="none" stroke="#fff" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <span style={{ fontWeight: 700, fontSize: 16, color: '#d97706' }}>MarketIntel</span>
            </div>
            <h1 style={{ margin: '0 0 6px', fontSize: 22, fontWeight: 700, color: '#1f2937', lineHeight: 1.3 }}>{product.title}</h1>
            <div style={{ display: 'flex', gap: 16, fontSize: 13, color: '#6b7280' }}>
              {product.brand && <span>{product.brand}</span>}
              {product.sku && <span>SKU: {product.sku}</span>}
            </div>
          </div>
          <div style={{ textAlign: 'right', fontSize: 12, color: '#9ca3af' }}>
            <p style={{ margin: '0 0 4px', fontWeight: 600, color: '#6b7280' }}>Price Report</p>
            <p style={{ margin: 0 }}>{today}</p>
          </div>
        </div>

        {/* Summary stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
          {[
            { label: 'My Price', value: fmt(product.my_price), sub: pricePosition && <PositionBadge position={pricePosition} /> },
            { label: 'Lowest Price', value: fmt(lowestPrice), sub: lowestPrice && product.my_price ? <span style={{ fontSize: 11, color: '#6b7280' }}>{pct(product.my_price, lowestPrice)} vs mine</span> : null },
            { label: 'Market Average', value: fmt(avgPrice), sub: <span style={{ fontSize: 11, color: '#6b7280' }}>{matches.length} competitor{matches.length !== 1 ? 's' : ''}</span> },
            { label: 'In Stock', value: `${inStock} / ${matches.length}`, sub: <span style={{ fontSize: 11, color: '#6b7280' }}>competitors</span> },
          ].map(card => (
            <div key={card.label} style={{ background: '#f9fafb', borderRadius: 12, padding: '16px', border: '1px solid #e5e7eb' }}>
              <p style={{ margin: '0 0 6px', fontSize: 11, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>{card.label}</p>
              <p style={{ margin: '0 0 4px', fontSize: 22, fontWeight: 700, color: '#1f2937' }}>{card.value}</p>
              <div style={{ minHeight: 18 }}>{card.sub}</div>
            </div>
          ))}
        </div>

        {/* Price range bar */}
        {lowestPrice != null && highestPrice != null && highestPrice > lowestPrice && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 12, padding: 20, marginBottom: 32 }}>
            <p style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 600, color: '#374151' }}>Market Price Range</p>
            <div style={{ position: 'relative', height: 12, background: '#e5e7eb', borderRadius: 6, marginBottom: 8 }}>
              {/* Filled range */}
              <div style={{ position: 'absolute', left: 0, right: 0, height: '100%', background: 'linear-gradient(90deg, #bbf7d0, #fde68a, #fca5a5)', borderRadius: 6 }} />
              {/* My price marker */}
              {product.my_price != null && (() => {
                const pctPos = Math.min(100, Math.max(0, ((product.my_price - lowestPrice) / (highestPrice - lowestPrice)) * 100));
                return (
                  <div style={{ position: 'absolute', top: -4, left: `${pctPos}%`, transform: 'translateX(-50%)', width: 20, height: 20, background: '#f59e0b', borderRadius: '50%', border: '3px solid #fff', boxShadow: '0 1px 4px rgba(0,0,0,0.2)' }} title={`My price: ${fmt(product.my_price)}`} />
                );
              })()}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#6b7280' }}>
              <span>Low: {fmt(lowestPrice)}</span>
              {product.my_price != null && <span style={{ color: '#d97706', fontWeight: 600 }}>● My Price: {fmt(product.my_price)}</span>}
              <span>High: {fmt(highestPrice)}</span>
            </div>
          </div>
        )}

        {/* Competitor price table */}
        <div style={{ marginBottom: 32 }}>
          <p style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 700, color: '#1f2937' }}>Competitor Prices ({matches.length})</p>

          {matches.length === 0 ? (
            <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 12, padding: 32, textAlign: 'center', color: '#9ca3af', fontSize: 14 }}>
              No competitor matches found. Run a scrape to collect data.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  {['Competitor', 'Product', 'Price', 'vs My Price', 'Stock', 'Updated'].map(h => (
                    <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '1px solid #e5e7eb' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...matches]
                  .sort((a, b) => (a.latest_price || 0) - (b.latest_price || 0))
                  .map((m, i) => {
                    const diff = product.my_price != null && m.latest_price != null ? m.latest_price - product.my_price : null;
                    const diffPct = diff != null && product.my_price ? ((diff / product.my_price) * 100).toFixed(1) : null;
                    const diffColor = diff == null ? '#9ca3af' : diff < 0 ? '#dc2626' : diff > 0 ? '#16a34a' : '#6b7280';
                    return (
                      <tr key={m.id} style={{ background: i % 2 === 0 ? '#fff' : '#f9fafb' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600, color: '#374151', borderBottom: '1px solid #f3f4f6' }}>{m.competitor_name}</td>
                        <td style={{ padding: '10px 12px', color: '#4b5563', maxWidth: 200, borderBottom: '1px solid #f3f4f6' }}>
                          <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.competitor_product_title}</span>
                        </td>
                        <td style={{ padding: '10px 12px', fontWeight: 700, color: '#1f2937', borderBottom: '1px solid #f3f4f6' }}>{fmt(m.latest_price)}</td>
                        <td style={{ padding: '10px 12px', color: diffColor, fontWeight: 600, borderBottom: '1px solid #f3f4f6' }}>
                          {diff != null ? (diff > 0 ? `+${fmt(Math.abs(diff))} (+${diffPct}%)` : diff < 0 ? `-${fmt(Math.abs(diff))} (${Math.abs(diffPct)}%)` : 'Same') : '—'}
                        </td>
                        <td style={{ padding: '10px 12px', borderBottom: '1px solid #f3f4f6' }}>
                          <span style={{
                            padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 600,
                            background: m.stock_status === 'In Stock' ? '#dcfce7' : '#f3f4f6',
                            color: m.stock_status === 'In Stock' ? '#166534' : '#6b7280',
                          }}>
                            {m.stock_status || 'Unknown'}
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', color: '#9ca3af', fontSize: 12, borderBottom: '1px solid #f3f4f6' }}>
                          {m.last_checked ? new Date(m.last_checked).toLocaleDateString() : '—'}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          )}
        </div>

        {/* Market position summary */}
        {pricePosition && (
          <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 12, padding: 20, marginBottom: 32 }}>
            <p style={{ margin: '0 0 8px', fontSize: 13, fontWeight: 700, color: '#92400e' }}>Market Position Summary</p>
            <p style={{ margin: 0, fontSize: 13, color: '#92400e', lineHeight: 1.6 }}>
              {pricePosition === 'cheapest' && `Your price (${fmt(product.my_price)}) is the lowest in the market. You have a strong competitive advantage but may be leaving margin on the table.`}
              {pricePosition === 'competitive' && `Your price (${fmt(product.my_price)}) is below the market average (${fmt(avgPrice)}). You are well-positioned competitively.`}
              {pricePosition === 'expensive' && `Your price (${fmt(product.my_price)}) is above the market average (${fmt(avgPrice)}). Consider reviewing your pricing strategy.`}
              {pricePosition === 'most_expensive' && `Your price (${fmt(product.my_price)}) is the highest in the market. This may reduce conversion rates unless your product offers clear differentiation.`}
            </p>
          </div>
        )}

        {/* Footer */}
        <div style={{ borderTop: '1px solid #e5e7eb', paddingTop: 16, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#9ca3af' }}>
          <span>Generated by MarketIntel &mdash; E-commerce Competitive Intelligence</span>
          <span>{today}</span>
        </div>
      </div>
    </>
  );
}
