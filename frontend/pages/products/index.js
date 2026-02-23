import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { ConfirmModal } from '../../components/Modal';
import { useToast } from '../../components/Toast';
import api from '../../lib/api';

// ─── MINI SPARKLINE ───────────────────────────────────────────────────────────
function Sparkline({ values, positive }) {
  if (!values || values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const W = 64, H = 28;
  const pts = values.map((v, i) =>
    `${(i / (values.length - 1)) * W},${H - ((v - min) / range) * (H - 4) - 2}`
  ).join(' ');
  const color = positive ? '#10b981' : '#ef4444';
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="shrink-0">
      <polyline fill="none" stroke={color} strokeWidth="1.8" points={pts}
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ─── STOCK BADGE ──────────────────────────────────────────────────────────────
function StockBadge({ inStockCount, competitorCount }) {
  if (competitorCount === 0) return null;
  if (inStockCount === 0) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-white/40" style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.08)' }}>
        <span className="w-1.5 h-1.5 rounded-full bg-white/40" />
        Out of Stock
      </span>
    );
  }
  if (inStockCount <= 1) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-amber-400" style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.2)' }}>
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
        Low Stock
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-emerald-400" style={{ background: 'rgba(5,150,105,0.12)', border: '1px solid rgba(5,150,105,0.2)' }}>
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
      In Stock
    </span>
  );
}

// ─── PRICE POSITION BADGE ─────────────────────────────────────────────────────
function PricePositionBadge({ position }) {
  if (!position) return null;
  const map = {
    cheapest:  { label: 'Lowest Price', bg: 'rgba(124,58,237,0.12)', border: 'rgba(124,58,237,0.2)', color: '#a78bfa' },
    mid:       { label: 'Mid Range',    bg: 'rgba(255,255,255,0.07)', border: 'rgba(255,255,255,0.1)', color: '#9ca3af' },
    expensive: { label: 'Expensive',   bg: 'rgba(239,68,68,0.12)',   border: 'rgba(239,68,68,0.2)',   color: '#f87171' },
  };
  const cfg = map[position];
  if (!cfg) return null;
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ background: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.color }}>
      {cfg.label}
    </span>
  );
}

// ─── IMAGE PLACEHOLDER ────────────────────────────────────────────────────────
function ProductImage({ src, title }) {
  const [err, setErr] = useState(false);
  if (!src || err) {
    return (
      <div className="w-full h-full flex items-center justify-center" style={{ background: 'var(--bg-elevated)' }}>
        <svg className="w-8 h-8" style={{ color: 'var(--text-muted)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </div>
    );
  }
  return <img src={src} alt={title} className="w-full h-full object-cover" onError={() => setErr(true)} />;
}

// ─── PRODUCT CARD ─────────────────────────────────────────────────────────────
function ProductCard({ product, selected, onSelect, onDelete }) {
  const [editingPrice, setEditingPrice] = useState(false);
  const [priceInput, setPriceInput] = useState(product.my_price ?? '');
  const [myPrice, setMyPrice] = useState(product.my_price);
  const [saving, setSaving] = useState(false);
  const { addToast } = useToast();

  const handleSavePrice = async () => {
    const parsed = parseFloat(priceInput);
    if (isNaN(parsed) || parsed < 0) { setEditingPrice(false); return; }
    setSaving(true);
    try {
      await api.updateProduct(product.id, { my_price: parsed });
      setMyPrice(parsed);
      addToast('Price updated', 'success');

      // Push to connected store if credentials are saved
      const conn = (() => { try { return JSON.parse(localStorage.getItem('marketintel_store_connection')); } catch { return null; } })();
      if (conn) {
        try {
          if (conn.type === 'woocommerce') {
            await api.pushPriceToWooCommerce(conn.credentials.store_url, conn.credentials.consumer_key, conn.credentials.consumer_secret, product.sku || '', product.title, parsed);
          } else if (conn.type === 'shopify') {
            await api.pushPriceToShopify(conn.credentials.shop_url, conn.credentials.access_token, product.sku || '', product.title, parsed);
          }
          addToast(`Synced to ${conn.type === 'woocommerce' ? 'WooCommerce' : 'Shopify'}`, 'success');
        } catch (syncErr) {
          addToast(`Store sync failed: ${syncErr.message}`, 'error');
        }
      }
    } catch {
      addToast('Failed to update price', 'error');
    } finally {
      setSaving(false);
      setEditingPrice(false);
    }
  };

  const changePct = product.price_change_pct;
  const isPositive = changePct !== null && changePct !== undefined && changePct <= 0;

  // Decorative sparkline derived from trend direction
  const sparkValues = product.lowest_price
    ? Array.from({ length: 7 }, (_, i) => {
        const base = product.lowest_price;
        const trend = (changePct || 0) / 700;
        return base * (1 + trend * (i - 3) + Math.sin(i * 1.2) * 0.003);
      })
    : null;

  return (
    <div className={`rounded-2xl transition-all ${selected ? 'ring-2 ring-amber-500/50' : 'hover:shadow-glass-lg'}`}
      style={{ background: 'var(--bg-surface)', border: `1px solid ${selected ? 'rgba(245,158,11,0.4)' : 'var(--border)'}` }}>
      <div className="p-4">
        <div className="flex gap-3">
          {/* Image */}
          <div className="relative shrink-0 w-20 h-20 rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
            <ProductImage src={product.image_url} title={product.title} />
            {changePct !== null && changePct !== undefined && (
              <div className={`absolute bottom-1 left-1 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-md leading-none ${changePct <= 0 ? 'bg-emerald-600' : 'bg-red-600'}`}>
                {changePct > 0 ? '+' : ''}{changePct}%
              </div>
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Title + checkbox */}
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <Link href={`/products/${product.id}`}
                  className="font-semibold text-white text-sm leading-snug hover:text-amber-400 transition-colors line-clamp-2">
                  {product.title}
                </Link>
                {product.sku && (
                  <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>SKU: {product.sku}</p>
                )}
              </div>
              <input type="checkbox" checked={selected}
                onChange={(e) => onSelect(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded shrink-0 cursor-pointer accent-amber-500" />
            </div>

            {/* Status badges */}
            {(product.competitor_count > 0 || product.price_position) && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                <StockBadge inStockCount={product.in_stock_count} competitorCount={product.competitor_count} />
                <PricePositionBadge position={product.price_position} />
              </div>
            )}

            {/* Price row */}
            <div className="flex items-end justify-between mt-2.5 gap-2">
              <div className="min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-wider leading-none mb-1" style={{ color: 'var(--text-muted)' }}>My Price</p>
                {editingPrice ? (
                  <div className="flex items-center gap-1">
                    <span className="text-white/50 text-sm font-medium">$</span>
                    <input autoFocus type="number" step="0.01" value={priceInput}
                      onChange={(e) => setPriceInput(e.target.value)}
                      onBlur={handleSavePrice}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.target.blur(); } if (e.key === 'Escape') setEditingPrice(false); }}
                      className="w-20 text-lg font-bold text-white border-b-2 border-amber-500 bg-transparent focus:outline-none" />
                    {saving && <span className="text-xs animate-pulse" style={{ color: 'var(--text-muted)' }}>saving…</span>}
                  </div>
                ) : (
                  <button onClick={() => { setPriceInput(myPrice ?? ''); setEditingPrice(true); }}
                    className="text-lg font-bold text-white hover:text-amber-400 transition-colors text-left leading-tight"
                    title="Click to set your price">
                    {myPrice != null ? `$${myPrice.toFixed(2)}` : (
                      <span className="text-base font-medium" style={{ color: 'var(--text-muted)' }}>Set price</span>
                    )}
                  </button>
                )}
                {product.lowest_price && (
                  <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                    Mkt: <span className="font-medium text-amber-400">${product.lowest_price.toFixed(2)}</span>
                  </p>
                )}
              </div>
              {sparkValues && <Sparkline values={sparkValues} positive={isPositive} />}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-3 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
          <span className="text-xs font-medium" style={{ color: product.competitor_count > 0 ? 'var(--text-muted)' : 'var(--text-dim)' }}>
            {product.competitor_count > 0
              ? `${product.competitor_count} competitor${product.competitor_count !== 1 ? 's' : ''}`
              : 'No matches yet'}
          </span>
          <div className="flex items-center gap-3">
            <Link href={`/products/${product.id}`} className="text-xs font-medium text-amber-400 hover:text-amber-300 transition-colors">Details</Link>
            <button onClick={onDelete} className="text-xs font-medium text-red-400 hover:text-red-300 transition-colors">Remove</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── FILTER TABS ──────────────────────────────────────────────────────────────
const TABS = [
  { key: 'all',       label: 'All Products'    },
  { key: 'watchlist', label: 'Watchlist'        },
  { key: 'repricing', label: 'Need Repricing'  },
  { key: 'low_stock', label: 'Low Stock'        },
];

// ─── MAIN PAGE ────────────────────────────────────────────────────────────────
export default function ProductsPage() {
  const { addToast } = useToast();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('all');
  const [selected, setSelected] = useState(new Set());
  const [deleteModal, setDeleteModal] = useState({ open: false, product: null });
  const [search, setSearch] = useState('');

  useEffect(() => { loadProducts(); }, []);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const data = await api.getProducts();
      setProducts(data);
      setError(null);
    } catch (err) {
      setError('Failed to load products. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    try {
      await api.deleteProduct(deleteModal.product.id);
      setProducts(ps => ps.filter(p => p.id !== deleteModal.product.id));
      setSelected(s => { const n = new Set(s); n.delete(deleteModal.product.id); return n; });
      addToast('Product removed', 'success');
    } catch {
      addToast('Failed to remove product', 'error');
    }
  };

  const toggleSelect = useCallback((id, checked) => {
    setSelected(s => { const n = new Set(s); checked ? n.add(id) : n.delete(id); return n; });
  }, []);

  // Filtering
  const filtered = products.filter(p => {
    if (search) {
      const q = search.toLowerCase();
      if (!p.title.toLowerCase().includes(q) && !(p.sku || '').toLowerCase().includes(q)) return false;
    }
    if (activeTab === 'watchlist') return p.my_price != null;
    if (activeTab === 'repricing') return p.price_position === 'expensive';
    if (activeTab === 'low_stock') return p.in_stock_count === 0 && p.competitor_count > 0;
    return true;
  });

  const toggleAll = () => {
    setSelected(selected.size === filtered.length ? new Set() : new Set(filtered.map(p => p.id)));
  };

  const totalMatches   = products.reduce((s, p) => s + (p.competitor_count || 0), 0);
  const cheapestCount  = products.filter(p => p.price_position === 'cheapest').length;
  const expensiveCount = products.filter(p => p.price_position === 'expensive').length;

  const tabCount = (key) => {
    if (key === 'all') return products.length;
    if (key === 'watchlist') return products.filter(p => p.my_price != null).length;
    if (key === 'repricing') return products.filter(p => p.price_position === 'expensive').length;
    return products.filter(p => p.in_stock_count === 0 && p.competitor_count > 0).length;
  };

  const exportToCSV = (list) => {
    const rows = list.map(p => [
      p.title,
      p.brand || '',
      p.sku || '',
      p.my_price != null ? p.my_price.toFixed(2) : '',
      p.lowest_price != null ? p.lowest_price.toFixed(2) : '',
      p.competitor_count || 0,
      p.price_position || '',
      p.in_stock_count > 0 ? 'Yes' : p.competitor_count > 0 ? 'No' : '',
    ]);
    const csv = [
      ['Title', 'Brand', 'SKU', 'My Price', 'Lowest Market Price', 'Competitors', 'Price Position', 'In Stock'],
      ...rows,
    ].map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `products-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── Loading skeleton ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <Layout>
        <div className="px-4 sm:px-6 max-w-2xl mx-auto lg:max-w-none lg:px-6">
          <div className="h-8 rounded-xl animate-pulse mb-6 w-40" style={{ background: 'var(--bg-surface)' }} />
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
            {[1,2,3,4,5,6].map(i => (
              <div key={i} className="rounded-2xl p-4 animate-pulse" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                <div className="flex gap-3">
                  <div className="w-20 h-20 rounded-xl shrink-0" style={{ background: 'var(--bg-elevated)' }} />
                  <div className="flex-1 space-y-2 pt-1">
                    <div className="h-4 rounded-lg w-3/4" style={{ background: 'var(--bg-elevated)' }} />
                    <div className="h-3 rounded-lg w-1/3" style={{ background: 'var(--bg-elevated)' }} />
                    <div className="flex gap-1.5 mt-2">
                      <div className="h-5 w-16 rounded-full" style={{ background: 'var(--bg-elevated)' }} />
                      <div className="h-5 w-20 rounded-full" style={{ background: 'var(--bg-elevated)' }} />
                    </div>
                    <div className="h-5 rounded-lg w-1/2 mt-2" style={{ background: 'var(--bg-elevated)' }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="px-4 sm:px-6 max-w-2xl mx-auto">
          <div className="rounded-2xl p-6 text-center" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}>
            <p className="font-semibold text-red-400 mb-2">{error}</p>
            <button onClick={loadProducts} className="text-sm text-red-400 underline">Try again</button>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="px-4 sm:px-6 max-w-2xl mx-auto lg:max-w-none lg:px-6">

        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-2xl font-bold text-white">Products</h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>{products.length} product{products.length !== 1 ? 's' : ''} monitored</p>
          </div>
          <div className="hidden sm:flex items-center gap-2">
            {products.length > 0 && (
              <button
                onClick={() => exportToCSV(filtered)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-white/60 hover:text-white hover:bg-white/5 transition-colors"
                style={{ border: '1px solid var(--border)' }}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Export CSV
              </button>
            )}
            <Link href="/products/add"
              className="flex items-center gap-2 px-4 py-2 rounded-xl gradient-brand text-white text-sm font-semibold hover:opacity-90 transition-opacity shadow-gradient">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Add Product
            </Link>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          {[
            { label: 'Products',    value: products.length, bg: 'rgba(37,99,235,0.15)',   border: 'rgba(37,99,235,0.2)',   color: '#60a5fa' },
            { label: 'Competitors', value: totalMatches,    bg: 'rgba(124,58,237,0.15)',  border: 'rgba(124,58,237,0.2)',  color: '#a78bfa' },
            { label: 'Cheapest',    value: cheapestCount,   bg: 'rgba(5,150,105,0.15)',   border: 'rgba(5,150,105,0.2)',   color: '#34d399' },
            { label: 'Expensive',   value: expensiveCount,  bg: 'rgba(239,68,68,0.15)',   border: 'rgba(239,68,68,0.2)',   color: '#f87171' },
          ].map(s => (
            <div key={s.label} className="rounded-2xl px-4 py-3"
              style={{ background: s.bg, border: `1px solid ${s.border}` }}>
              <p className="text-2xl font-bold text-white">{s.value}</p>
              <p className="text-xs font-medium mt-0.5" style={{ color: s.color }}>{s.label}</p>
            </div>
          ))}
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'var(--text-muted)' }}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
          <input type="text" placeholder="Search by name or SKU…" value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 glass-input rounded-xl text-sm" />
        </div>

        {/* Filter tabs */}
        <div className="flex gap-2 overflow-x-auto scrollbar-hide mb-5 pb-1">
          {TABS.map(tab => {
            const count = tabCount(tab.key);
            const active = activeTab === tab.key;
            return (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-all shrink-0 ${active ? 'gradient-brand text-white shadow-gradient' : 'text-white/40 hover:text-white hover:bg-white/5'}`}
                style={!active ? { border: '1px solid var(--border)' } : {}}>
                {tab.label}
                <span className={`text-[11px] font-semibold px-1.5 py-0.5 rounded-full ${active ? 'bg-white/20 text-white' : 'bg-white/10 text-white/40'}`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Bulk select row */}
        {filtered.length > 0 && (
          <div className="flex items-center gap-3 mb-4">
            <button onClick={toggleAll} className="flex items-center gap-2 text-xs font-medium transition-colors" style={{ color: 'var(--text-muted)' }}>
              <input type="checkbox" readOnly
                checked={selected.size > 0 && selected.size === filtered.length}
                ref={el => { if (el) el.indeterminate = selected.size > 0 && selected.size < filtered.length; }}
                className="w-4 h-4 rounded accent-amber-500" />
              {selected.size > 0 ? `${selected.size} selected` : 'Select all'}
            </button>
            {selected.size > 0 && (
              <div className="flex items-center gap-2 ml-auto">
                <button onClick={() => exportToCSV(products.filter(p => selected.has(p.id)))}
                  className="px-3 py-1.5 text-xs font-medium text-white/50 hover:text-white rounded-lg transition-colors"
                  style={{ border: '1px solid var(--border)' }}>Export CSV</button>
                <Link href="/repricing" className="px-3 py-1.5 text-xs font-semibold text-white gradient-brand rounded-lg hover:opacity-90 transition-opacity">Reprice</Link>
              </div>
            )}
          </div>
        )}

        {/* Cards grid */}
        {filtered.length === 0 ? (
          <div className="rounded-2xl p-12 text-center" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--bg-elevated)' }}>
              <svg className="w-8 h-8" style={{ color: 'var(--text-muted)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-white">
              {search ? 'No results' : activeTab !== 'all' ? 'None in this filter' : 'No products yet'}
            </h3>
            <p className="text-sm mt-1 mb-5" style={{ color: 'var(--text-muted)' }}>
              {search ? `No products match "${search}"`
                : activeTab !== 'all' ? 'Try a different filter.'
                : 'Add your first product to start tracking competitor prices.'}
            </p>
            {activeTab === 'all' && !search && (
              <Link href="/products/add"
                className="inline-flex items-center gap-2 px-5 py-2.5 gradient-brand text-white text-sm font-semibold rounded-xl transition-opacity hover:opacity-90 shadow-gradient">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
                Add First Product
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
            {filtered.map(product => (
              <ProductCard key={product.id} product={product}
                selected={selected.has(product.id)}
                onSelect={(checked) => toggleSelect(product.id, checked)}
                onDelete={() => setDeleteModal({ open: true, product })}
              />
            ))}
          </div>
        )}

        {/* Floating bulk-action bar */}
        {selected.size > 0 && (
          <div className="fixed bottom-20 lg:bottom-6 left-4 right-4 lg:left-auto lg:right-6 lg:w-auto backdrop-blur-xl text-white rounded-2xl px-4 py-3 flex items-center gap-4 shadow-xl z-40"
            style={{ background: 'rgba(20,20,40,0.95)', border: '1px solid var(--border-md)' }}>
            <span className="text-sm font-medium flex-1">{selected.size} item{selected.size !== 1 ? 's' : ''} selected</span>
            <button onClick={() => exportToCSV(products.filter(p => selected.has(p.id)))} className="text-xs text-white/50 hover:text-white transition-colors font-medium">Export CSV</button>
            <Link href="/repricing" className="text-xs font-semibold text-amber-400 hover:text-amber-300 transition-colors">Reprice</Link>
            <button onClick={() => setSelected(new Set())} className="text-white/40 hover:text-white transition-colors ml-1">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
      </div>

      <ConfirmModal
        isOpen={deleteModal.open}
        onClose={() => setDeleteModal({ open: false, product: null })}
        onConfirm={handleDelete}
        title="Remove Product"
        message={`Remove "${deleteModal.product?.title}"? This will delete all competitor matches and price history.`}
        confirmText="Remove"
        cancelText="Cancel"
        type="danger"
      />
    </Layout>
  );
}
