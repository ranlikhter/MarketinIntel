import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import AdvancedFilters from '../components/AdvancedFilters';
import api from '../lib/api';

const PAGE_SIZE = 50;

const DEFAULT_FILTERS = {
  q: '',
  competitor: [],
  brand: [],
  category: [],
  min_price: undefined,
  max_price: undefined,
  in_stock: undefined,
  min_rating: undefined,
  min_match_score: 60,
  is_prime: undefined,
  has_coupon: undefined,
  has_lightning_deal: undefined,
  badge: undefined,
  condition: undefined,
  scraped_within_days: undefined,
  sort: 'match_score_desc',
};

// ── URL ↔ filter serialization ────────────────────────────────────────────────

function filtersToQuery(filters) {
  const out = {};
  for (const [k, v] of Object.entries(filters)) {
    if (v === undefined || v === null || v === '') continue;
    if (Array.isArray(v) && v.length === 0) continue;
    if (Array.isArray(v)) out[k] = v.join(',');
    else out[k] = String(v);
  }
  return out;
}

function queryToFilters(query) {
  const f = { ...DEFAULT_FILTERS };
  const lists = ['competitor', 'brand', 'category'];
  const floats = ['min_price', 'max_price', 'min_rating', 'min_match_score'];
  const ints = ['scraped_within_days'];
  const bools = ['in_stock', 'is_prime', 'has_coupon', 'has_lightning_deal'];

  for (const [k, v] of Object.entries(query)) {
    if (!v) continue;
    if (lists.includes(k)) f[k] = v.split(',').filter(Boolean);
    else if (floats.includes(k)) f[k] = parseFloat(v);
    else if (ints.includes(k)) f[k] = parseInt(v, 10);
    else if (bools.includes(k)) f[k] = v === 'true' ? true : undefined;
    else f[k] = v;
  }
  return f;
}

// ── Badge pill ────────────────────────────────────────────────────────────────

const BADGE_LABELS = {
  best_seller: '🏆 Best Seller',
  amazons_choice: "✅ Amazon's Choice",
  new_release: '🆕 New Release',
};

function BadgePill({ badge }) {
  return (
    <span style={{
      fontSize: 10,
      padding: '1px 6px',
      borderRadius: 10,
      background: 'rgba(245,158,11,0.15)',
      color: '#f59e0b',
      border: '1px solid rgba(245,158,11,0.3)',
      whiteSpace: 'nowrap',
    }}>
      {BADGE_LABELS[badge] || badge}
    </span>
  );
}

// ── Star rating ───────────────────────────────────────────────────────────────

function Stars({ rating }) {
  if (!rating) return null;
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  return (
    <span style={{ color: '#f59e0b', fontSize: 12, whiteSpace: 'nowrap' }}>
      {'★'.repeat(full)}{half ? '½' : ''}{'☆'.repeat(Math.max(0, 5 - full - (half ? 1 : 0)))}
      <span style={{ color: 'var(--text-muted)', marginLeft: 4 }}>{rating.toFixed(1)}</span>
    </span>
  );
}

// ── Active filter chip ────────────────────────────────────────────────────────

function FilterChip({ label, onRemove }) {
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      padding: '3px 10px',
      borderRadius: 20,
      fontSize: 12,
      background: 'rgba(245,158,11,0.12)',
      border: '1px solid rgba(245,158,11,0.3)',
      color: '#f59e0b',
    }}>
      {label}
      <button
        onClick={onRemove}
        style={{ background: 'none', border: 'none', color: '#f59e0b', cursor: 'pointer', padding: 0, lineHeight: 1, fontSize: 14 }}
      >
        ×
      </button>
    </span>
  );
}

// ── Product row card ──────────────────────────────────────────────────────────

function ProductCard({ item }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '56px 1fr auto',
      gap: 12,
      padding: '12px 16px',
      borderBottom: '1px solid var(--border)',
      alignItems: 'center',
    }}>
      {/* Image */}
      <div style={{ width: 56, height: 56, borderRadius: 6, overflow: 'hidden', background: 'var(--bg-surface)', flexShrink: 0 }}>
        {item.image_url
          ? <img src={item.image_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
          : <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 20 }}>📦</div>
        }
      </div>

      {/* Info */}
      <div style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 2 }}>
          <span style={{ fontSize: 11, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 4, padding: '1px 6px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
            {item.competitor_name}
          </span>
          {item.is_prime && (
            <span style={{ fontSize: 11, color: '#60a5fa', fontWeight: 600 }}>Prime</span>
          )}
          {item.badges?.map((b) => <BadgePill key={b} badge={b} />)}
          {item.has_coupon && (
            <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 10, background: 'rgba(34,197,94,0.15)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.3)' }}>
              Coupon
            </span>
          )}
        </div>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: 2 }}>
          {item.competitor_product_title}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {item.brand && <span>Brand: <b>{item.brand}</b></span>}
          {item.category && <span>· {item.category}</span>}
          {item.rating != null && <Stars rating={item.rating} />}
          {item.review_count != null && <span>({item.review_count.toLocaleString()} reviews)</span>}
          <span style={{ color: item.in_stock ? '#22c55e' : '#ef4444' }}>
            {item.in_stock === true ? '● In stock' : item.in_stock === false ? '○ Out of stock' : ''}
          </span>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
          My product: <span style={{ color: 'var(--text)' }}>{item.my_product_title}</span>
          {' · '}Match {Math.round(item.match_score)}%
        </div>
      </div>

      {/* Price + CTA */}
      <div style={{ textAlign: 'right', minWidth: 80 }}>
        {item.latest_price != null
          ? <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>${item.latest_price.toFixed(2)}</div>
          : <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>—</div>
        }
        <a
          href={item.competitor_url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ fontSize: 11, color: '#f59e0b', textDecoration: 'none', display: 'inline-block', marginTop: 4 }}
        >
          View →
        </a>
      </div>
    </div>
  );
}

// ── Build active chips list ───────────────────────────────────────────────────

function buildActiveChips(filters, facets, onRemove) {
  const chips = [];
  const priceMin = facets?.price_range?.min ?? 0;
  const priceMax = facets?.price_range?.max ?? 10000;

  if (filters.q) chips.push({ label: `"${filters.q}"`, key: 'q' });
  (filters.competitor || []).forEach((v) => chips.push({ label: `Competitor: ${v}`, key: 'competitor', value: v }));
  (filters.brand || []).forEach((v) => chips.push({ label: `Brand: ${v}`, key: 'brand', value: v }));
  (filters.category || []).forEach((v) => chips.push({ label: `Category: ${v}`, key: 'category', value: v }));
  if (filters.min_price != null && filters.min_price > priceMin)
    chips.push({ label: `Min $${filters.min_price}`, key: 'min_price' });
  if (filters.max_price != null && filters.max_price < priceMax)
    chips.push({ label: `Max $${filters.max_price}`, key: 'max_price' });
  if (filters.min_rating) chips.push({ label: `${filters.min_rating}★+`, key: 'min_rating' });
  if (filters.in_stock) chips.push({ label: 'In stock', key: 'in_stock' });
  if (filters.has_coupon) chips.push({ label: 'Has coupon', key: 'has_coupon' });
  if (filters.is_prime) chips.push({ label: 'Prime', key: 'is_prime' });
  if (filters.has_lightning_deal) chips.push({ label: 'Lightning deal', key: 'has_lightning_deal' });
  if (filters.badge) chips.push({ label: BADGE_LABELS[filters.badge] || filters.badge, key: 'badge' });
  if (filters.condition) chips.push({ label: `Condition: ${filters.condition}`, key: 'condition' });
  if (filters.scraped_within_days) chips.push({ label: `Scraped within ${filters.scraped_within_days}d`, key: 'scraped_within_days' });
  if (filters.min_match_score && filters.min_match_score !== 60)
    chips.push({ label: `Match ≥${filters.min_match_score}%`, key: 'min_match_score' });

  return chips.map((chip) => (
    <FilterChip
      key={`${chip.key}-${chip.value || ''}`}
      label={chip.label}
      onRemove={() => onRemove(chip.key, chip.value)}
    />
  ));
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CompetitorCatalog() {
  const router = useRouter();
  const [facets, setFacets] = useState(null);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const debounceRef = useRef(null);
  const initializedRef = useRef(false);

  // Load facets once
  useEffect(() => {
    api.getCompetitorFacets()
      .then(setFacets)
      .catch(() => setFacets({}));
  }, []);

  // Initialize filters from URL on first router.isReady
  useEffect(() => {
    if (!router.isReady || initializedRef.current) return;
    initializedRef.current = true;
    const f = queryToFilters(router.query);
    setFilters(f);
  }, [router.isReady]);

  const fetchResults = useCallback(async (f, page = 0) => {
    setLoading(true);
    try {
      const data = await api.getCompetitorProducts({ ...f, limit: PAGE_SIZE, offset: page * PAGE_SIZE });
      if (page === 0) {
        setResults(data.results || []);
      } else {
        setResults((prev) => [...prev, ...(data.results || [])]);
      }
      setTotal(data.total || 0);
      setHasMore((data.results?.length || 0) === PAGE_SIZE);
      setOffset(page);
    } catch {
      if (page === 0) setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Debounced fetch when filters change
  useEffect(() => {
    if (!initializedRef.current) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchResults(filters, 0);
      // Sync URL
      const q = filtersToQuery(filters);
      router.replace({ pathname: router.pathname, query: q }, undefined, { shallow: true });
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [filters]);

  const handleReset = () => {
    setFilters(DEFAULT_FILTERS);
  };

  const removeChip = (key, value) => {
    if (['competitor', 'brand', 'category'].includes(key)) {
      setFilters((prev) => ({ ...prev, [key]: (prev[key] || []).filter((v) => v !== value) }));
    } else {
      setFilters((prev) => ({ ...prev, [key]: DEFAULT_FILTERS[key] }));
    }
  };

  const loadMore = () => fetchResults(filters, offset + 1);

  const activeChips = buildActiveChips(filters, facets, removeChip);

  return (
    <Layout>
      {/* Header */}
      <div style={{ padding: '20px 24px 12px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: 'var(--text)' }}>
            Competitor Products
          </h1>
          {!loading && (
            <span style={{ fontSize: 14, color: 'var(--text-muted)' }}>
              {total.toLocaleString()} match{total !== 1 ? 'es' : ''}
            </span>
          )}
          {loading && (
            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading…</span>
          )}
        </div>
        {activeChips.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
            {activeChips}
          </div>
        )}
      </div>

      {/* Body: sidebar + results */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', minHeight: 0 }}>

        {/* Sidebar */}
        <div style={{
          width: 240,
          flexShrink: 0,
          borderRight: '1px solid var(--border)',
          overflowY: 'auto',
          background: 'var(--bg-surface)',
        }}>
          <AdvancedFilters
            facets={facets}
            value={filters}
            onChange={setFilters}
            onReset={handleReset}
          />
        </div>

        {/* Results */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          {results.length === 0 && !loading && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: 12, padding: 40 }}>
              <div style={{ fontSize: 40 }}>🔍</div>
              <div style={{ fontSize: 16, fontWeight: 600 }}>No competitor products found</div>
              <div style={{ fontSize: 13 }}>Try adjusting your filters or add products to start tracking.</div>
              <button
                onClick={handleReset}
                style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid #f59e0b', background: 'rgba(245,158,11,0.1)', color: '#f59e0b', cursor: 'pointer', fontSize: 13 }}
              >
                Reset filters
              </button>
            </div>
          )}

          {results.map((item) => (
            <ProductCard key={item.match_id} item={item} />
          ))}

          {hasMore && (
            <div style={{ padding: '16px', textAlign: 'center' }}>
              <button
                onClick={loadMore}
                disabled={loading}
                style={{
                  padding: '9px 28px',
                  borderRadius: 8,
                  border: '1px solid var(--border)',
                  background: 'var(--bg-surface)',
                  color: 'var(--text)',
                  cursor: loading ? 'default' : 'pointer',
                  fontSize: 13,
                  opacity: loading ? 0.5 : 1,
                }}
              >
                {loading ? 'Loading…' : 'Load more'}
              </button>
            </div>
          )}

          {!hasMore && results.length > 0 && (
            <div style={{ padding: '12px 16px', textAlign: 'center', fontSize: 12, color: 'var(--text-muted)' }}>
              Showing all {total.toLocaleString()} result{total !== 1 ? 's' : ''}
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        :global(body) { overflow: hidden; }
      `}</style>
    </Layout>
  );
}
