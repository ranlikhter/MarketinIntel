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
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
        <span className="w-1.5 h-1.5 rounded-full bg-gray-400" />
        Out of Stock
      </span>
    );
  }
  if (inStockCount <= 1) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
        Low Stock
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
      In Stock
    </span>
  );
}

// ─── PRICE POSITION BADGE ─────────────────────────────────────────────────────
function PricePositionBadge({ position }) {
  if (!position) return null;
  const map = {
    cheapest:  { label: 'Lowest Price', cls: 'bg-violet-50 text-violet-700' },
    mid:       { label: 'Mid Range',    cls: 'bg-gray-100 text-gray-600'    },
    expensive: { label: 'Expensive',    cls: 'bg-red-50 text-red-600'       },
  };
  const cfg = map[position];
  if (!cfg) return null;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.cls}`}>
      {cfg.label}
    </span>
  );
}

// ─── IMAGE PLACEHOLDER ────────────────────────────────────────────────────────
function ProductImage({ src, title }) {
  const [err, setErr] = useState(false);
  if (!src || err) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-50">
        <svg className="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
    <div className={`bg-white rounded-2xl shadow-sm border transition-all ${selected ? 'border-blue-400 ring-2 ring-blue-100' : 'border-gray-100 hover:border-gray-200 hover:shadow-md'}`}>
      <div className="p-4">
        <div className="flex gap-3">
          {/* Image */}
          <div className="relative shrink-0 w-20 h-20 rounded-xl overflow-hidden bg-gray-50 border border-gray-100">
            <ProductImage src={product.image_url} title={product.title} />
            {changePct !== null && changePct !== undefined && (
              <div className={`absolute bottom-1 left-1 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-md leading-none ${changePct <= 0 ? 'bg-emerald-600' : 'bg-red-500'}`}>
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
                  className="font-semibold text-gray-900 text-sm leading-snug hover:text-blue-600 transition-colors line-clamp-2">
                  {product.title}
                </Link>
                {product.sku && (
                  <p className="text-[11px] text-gray-400 mt-0.5">SKU: {product.sku}</p>
                )}
              </div>
              <input type="checkbox" checked={selected}
                onChange={(e) => onSelect(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 shrink-0 cursor-pointer" />
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
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider leading-none mb-1">My Price</p>
                {editingPrice ? (
                  <div className="flex items-center gap-1">
                    <span className="text-gray-400 text-sm font-medium">$</span>
                    <input autoFocus type="number" step="0.01" value={priceInput}
                      onChange={(e) => setPriceInput(e.target.value)}
                      onBlur={handleSavePrice}
                      onKeyDown={(e) => { if (e.key === 'Enter') handleSavePrice(); if (e.key === 'Escape') setEditingPrice(false); }}
                      className="w-20 text-lg font-bold text-gray-900 border-b-2 border-blue-500 bg-transparent focus:outline-none" />
                    {saving && <span className="text-xs text-gray-400 animate-pulse">saving…</span>}
                  </div>
                ) : (
                  <button onClick={() => { setPriceInput(myPrice ?? ''); setEditingPrice(true); }}
                    className="text-lg font-bold text-gray-900 hover:text-blue-600 transition-colors text-left leading-tight"
                    title="Click to set your price">
                    {myPrice != null ? `$${myPrice.toFixed(2)}` : (
                      <span className="text-gray-300 text-base font-medium">Set price</span>
                    )}
                  </button>
                )}
                {product.lowest_price && (
                  <p className="text-[11px] text-gray-400 mt-0.5">
                    Mkt: <span className="font-medium">${product.lowest_price.toFixed(2)}</span>
                  </p>
                )}
              </div>
              {sparkValues && <Sparkline values={sparkValues} positive={isPositive} />}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-50">
          <span className={`text-xs font-medium ${product.competitor_count > 0 ? 'text-gray-500' : 'text-gray-300'}`}>
            {product.competitor_count > 0
              ? `${product.competitor_count} competitor${product.competitor_count !== 1 ? 's' : ''}`
              : 'No matches yet'}
          </span>
          <div className="flex items-center gap-3">
            <Link href={`/products/${product.id}`} className="text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors">Details</Link>
            <button onClick={onDelete} className="text-xs font-medium text-red-400 hover:text-red-600 transition-colors">Remove</button>
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

  // ── Loading skeleton ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <Layout>
        <div className="px-4 sm:px-6 max-w-2xl mx-auto lg:max-w-none lg:px-6">
          <div className="h-8 bg-gray-200 rounded-xl animate-pulse mb-6 w-40" />
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
            {[1,2,3,4,5,6].map(i => (
              <div key={i} className="bg-white rounded-2xl p-4 border border-gray-100 animate-pulse">
                <div className="flex gap-3">
                  <div className="w-20 h-20 bg-gray-100 rounded-xl shrink-0" />
                  <div className="flex-1 space-y-2 pt-1">
                    <div className="h-4 bg-gray-100 rounded-lg w-3/4" />
                    <div className="h-3 bg-gray-100 rounded-lg w-1/3" />
                    <div className="flex gap-1.5 mt-2">
                      <div className="h-5 w-16 bg-gray-100 rounded-full" />
                      <div className="h-5 w-20 bg-gray-100 rounded-full" />
                    </div>
                    <div className="h-5 bg-gray-100 rounded-lg w-1/2 mt-2" />
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
          <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center">
            <p className="font-semibold text-red-800 mb-2">{error}</p>
            <button onClick={loadProducts} className="text-sm text-red-600 underline">Try again</button>
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
            <h1 className="text-2xl font-bold text-gray-900">Products</h1>
            <p className="text-sm text-gray-500 mt-0.5">{products.length} product{products.length !== 1 ? 's' : ''} monitored</p>
          </div>
          <Link href="/products/add"
            className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition-colors shadow-sm">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Add Product
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          {[
            { label: 'Products',    value: products.length,  color: 'text-blue-600',    bg: 'bg-blue-50'   },
            { label: 'Competitors', value: totalMatches,     color: 'text-violet-600',  bg: 'bg-violet-50' },
            { label: 'Cheapest',    value: cheapestCount,    color: 'text-emerald-600', bg: 'bg-emerald-50'},
            { label: 'Expensive',   value: expensiveCount,   color: 'text-red-500',     bg: 'bg-red-50'    },
          ].map(s => (
            <div key={s.label} className={`${s.bg} rounded-2xl px-4 py-3`}>
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-xs text-gray-500 font-medium mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
          <input type="text" placeholder="Search by name or SKU…" value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-400 transition-shadow placeholder-gray-400" />
        </div>

        {/* Filter tabs */}
        <div className="flex gap-2 overflow-x-auto scrollbar-hide mb-5 pb-1">
          {TABS.map(tab => {
            const count = tabCount(tab.key);
            const active = activeTab === tab.key;
            return (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-all shrink-0 ${active ? 'bg-gray-900 text-white shadow-sm' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'}`}>
                {tab.label}
                <span className={`text-[11px] font-semibold px-1.5 py-0.5 rounded-full ${active ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-500'}`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Bulk select row */}
        {filtered.length > 0 && (
          <div className="flex items-center gap-3 mb-4">
            <button onClick={toggleAll} className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700 transition-colors font-medium">
              <input type="checkbox" readOnly
                checked={selected.size > 0 && selected.size === filtered.length}
                ref={el => { if (el) el.indeterminate = selected.size > 0 && selected.size < filtered.length; }}
                className="w-4 h-4 rounded border-gray-300 text-blue-600" />
              {selected.size > 0 ? `${selected.size} selected` : 'Select all'}
            </button>
            {selected.size > 0 && (
              <div className="flex items-center gap-2 ml-auto">
                <button className="px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">Export</button>
                <Link href="/repricing" className="px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">Reprice</Link>
              </div>
            )}
          </div>
        )}

        {/* Cards grid */}
        {filtered.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center shadow-sm">
            <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-gray-900">
              {search ? 'No results' : activeTab !== 'all' ? 'None in this filter' : 'No products yet'}
            </h3>
            <p className="text-sm text-gray-400 mt-1 mb-5">
              {search ? `No products match "${search}"`
                : activeTab !== 'all' ? 'Try a different filter.'
                : 'Add your first product to start tracking competitor prices.'}
            </p>
            {activeTab === 'all' && !search && (
              <Link href="/products/add"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 transition-colors shadow-sm">
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
          <div className="fixed bottom-20 lg:bottom-6 left-4 right-4 lg:left-auto lg:right-6 lg:w-auto bg-gray-900 text-white rounded-2xl px-4 py-3 flex items-center gap-4 shadow-xl z-40">
            <span className="text-sm font-medium flex-1">{selected.size} item{selected.size !== 1 ? 's' : ''} selected</span>
            <button className="text-xs text-gray-300 hover:text-white transition-colors font-medium">Export</button>
            <Link href="/repricing" className="text-xs font-semibold text-blue-400 hover:text-blue-300 transition-colors">Reprice</Link>
            <button onClick={() => setSelected(new Set())} className="text-gray-400 hover:text-white transition-colors ml-1">
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
