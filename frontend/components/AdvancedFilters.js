import { useState } from 'react';

const RATING_OPTIONS = [
  { label: 'Any', value: null },
  { label: '3★+', value: 3 },
  { label: '4★+', value: 4 },
  { label: '4.5★+', value: 4.5 },
];

const SCRAPED_OPTIONS = [
  { label: 'Any', value: null },
  { label: '24h', value: 1 },
  { label: '7d', value: 7 },
  { label: '30d', value: 30 },
];

const SORT_OPTIONS = [
  { label: 'Best match', value: 'match_score_desc' },
  { label: 'Price: low → high', value: 'price_asc' },
  { label: 'Price: high → low', value: 'price_desc' },
  { label: 'Rating', value: 'rating_desc' },
  { label: 'Recently scraped', value: 'last_scraped_desc' },
];

function SectionHeader({ label }) {
  return (
    <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>
      {label}
    </div>
  );
}

function MultiSelectChips({ options, selected, onChange }) {
  const toggle = (val) => {
    if (selected.includes(val)) {
      onChange(selected.filter((v) => v !== val));
    } else {
      onChange([...selected, val]);
    }
  };
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {options.map((opt) => {
        const active = selected.includes(opt);
        return (
          <button
            key={opt}
            onClick={() => toggle(opt)}
            style={{
              padding: '3px 10px',
              borderRadius: 20,
              fontSize: 12,
              border: active ? '1px solid #f59e0b' : '1px solid var(--border)',
              background: active ? 'rgba(245,158,11,0.15)' : 'var(--bg-surface)',
              color: active ? '#f59e0b' : 'var(--text-muted)',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

function PillSelector({ options, selected, onChange }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {options.map(({ label, value }) => {
        const active = selected === value;
        return (
          <button
            key={label}
            onClick={() => onChange(active ? null : value)}
            style={{
              padding: '3px 12px',
              borderRadius: 20,
              fontSize: 12,
              border: active ? '1px solid #f59e0b' : '1px solid var(--border)',
              background: active ? 'rgba(245,158,11,0.15)' : 'var(--bg-surface)',
              color: active ? '#f59e0b' : 'var(--text-muted)',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

function RangeSlider({ min, max, valueMin, valueMax, onChange }) {
  const safeMin = min ?? 0;
  const safeMax = max ?? 10000;
  const curMin = valueMin ?? safeMin;
  const curMax = valueMax ?? safeMax;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>
        <span>${curMin.toFixed(0)}</span>
        <span>${curMax.toFixed(0)}</span>
      </div>
      <div style={{ position: 'relative', height: 20 }}>
        <input
          type="range"
          min={safeMin}
          max={safeMax}
          step={1}
          value={curMin}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            if (v <= curMax) onChange(v, curMax);
          }}
          style={{ position: 'absolute', width: '100%', pointerEvents: 'auto', zIndex: 2, appearance: 'none', background: 'transparent' }}
        />
        <input
          type="range"
          min={safeMin}
          max={safeMax}
          step={1}
          value={curMax}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            if (v >= curMin) onChange(curMin, v);
          }}
          style={{ position: 'absolute', width: '100%', pointerEvents: 'auto', zIndex: 2, appearance: 'none', background: 'transparent' }}
        />
        <div style={{ position: 'absolute', top: 8, left: 0, right: 0, height: 4, background: 'var(--border)', borderRadius: 2 }}>
          <div
            style={{
              position: 'absolute',
              left: `${((curMin - safeMin) / (safeMax - safeMin)) * 100}%`,
              right: `${100 - ((curMax - safeMin) / (safeMax - safeMin)) * 100}%`,
              height: '100%',
              background: '#f59e0b',
              borderRadius: 2,
            }}
          />
        </div>
      </div>
    </div>
  );
}

function Toggle({ label, checked, onChange }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13, color: 'var(--text-muted)', padding: '4px 0' }}>
      <span
        onClick={() => onChange(!checked)}
        style={{
          width: 32,
          height: 18,
          borderRadius: 9,
          background: checked ? '#f59e0b' : 'var(--border)',
          position: 'relative',
          display: 'inline-block',
          transition: 'background 0.2s',
          flexShrink: 0,
        }}
      >
        <span
          style={{
            position: 'absolute',
            top: 2,
            left: checked ? 16 : 2,
            width: 14,
            height: 14,
            borderRadius: '50%',
            background: '#fff',
            transition: 'left 0.2s',
          }}
        />
      </span>
      {label}
    </label>
  );
}

function BrandSearchSelect({ brands, selected, onChange }) {
  const [search, setSearch] = useState('');
  const filtered = brands.filter((b) => b.toLowerCase().includes(search.toLowerCase()));
  const allSelected = brands.length > 0 && brands.every((b) => selected.includes(b));

  const toggleAll = () => {
    if (allSelected) onChange([]);
    else onChange([...brands]);
  };

  const toggle = (b) => {
    if (selected.includes(b)) onChange(selected.filter((v) => v !== b));
    else onChange([...selected, b]);
  };

  return (
    <div>
      <input
        type="text"
        placeholder="Search brands…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{
          width: '100%',
          padding: '5px 8px',
          borderRadius: 6,
          border: '1px solid var(--border)',
          background: 'var(--bg-input, var(--bg-surface))',
          color: 'var(--text)',
          fontSize: 12,
          marginBottom: 6,
          boxSizing: 'border-box',
        }}
      />
      <div style={{ maxHeight: 140, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {brands.length > 1 && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer', padding: '2px 0', color: 'var(--text-muted)' }}>
            <input type="checkbox" checked={allSelected} onChange={toggleAll} />
            <span style={{ fontStyle: 'italic' }}>Select all</span>
          </label>
        )}
        {filtered.map((b) => (
          <label key={b} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer', padding: '2px 0', color: 'var(--text-muted)' }}>
            <input type="checkbox" checked={selected.includes(b)} onChange={() => toggle(b)} />
            {b}
          </label>
        ))}
        {filtered.length === 0 && <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>No brands match</div>}
      </div>
    </div>
  );
}

export default function AdvancedFilters({ facets, value, onChange, onReset }) {
  const f = facets || {};
  const priceMin = f.price_range?.min ?? 0;
  const priceMax = f.price_range?.max ?? 10000;

  const set = (key, val) => onChange({ ...value, [key]: val });

  const section = { marginBottom: 20 };
  const divider = { borderTop: '1px solid var(--border)', margin: '16px 0' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', padding: '16px 12px', height: '100%', overflowY: 'auto' }}>

      {/* Search */}
      <div style={section}>
        <input
          type="text"
          placeholder="Search by product name…"
          value={value.q || ''}
          onChange={(e) => set('q', e.target.value)}
          style={{
            width: '100%',
            padding: '7px 10px',
            borderRadius: 8,
            border: '1px solid var(--border)',
            background: 'var(--bg-input, var(--bg-surface))',
            color: 'var(--text)',
            fontSize: 13,
            boxSizing: 'border-box',
          }}
        />
      </div>

      <div style={divider} />

      {/* Competitor */}
      {f.competitors?.length > 0 && (
        <div style={section}>
          <SectionHeader label="Competitor" />
          <MultiSelectChips
            options={f.competitors}
            selected={value.competitor || []}
            onChange={(v) => set('competitor', v)}
          />
        </div>
      )}

      {/* Brand */}
      {f.brands?.length > 0 && (
        <div style={section}>
          <SectionHeader label="Brand" />
          <BrandSearchSelect
            brands={f.brands}
            selected={value.brand || []}
            onChange={(v) => set('brand', v)}
          />
        </div>
      )}

      {/* Category */}
      {f.categories?.length > 0 && (
        <div style={section}>
          <SectionHeader label="Category" />
          <MultiSelectChips
            options={f.categories}
            selected={value.category || []}
            onChange={(v) => set('category', v)}
          />
        </div>
      )}

      <div style={divider} />

      {/* Price range */}
      <div style={section}>
        <SectionHeader label="Price range" />
        <RangeSlider
          min={priceMin}
          max={priceMax}
          valueMin={value.min_price ?? priceMin}
          valueMax={value.max_price ?? priceMax}
          onChange={(lo, hi) => onChange({ ...value, min_price: lo, max_price: hi })}
        />
      </div>

      {/* Match confidence */}
      <div style={section}>
        <SectionHeader label={`Match confidence ≥ ${value.min_match_score ?? 60}%`} />
        <input
          type="range"
          min={50}
          max={100}
          step={5}
          value={value.min_match_score ?? 60}
          onChange={(e) => set('min_match_score', parseFloat(e.target.value))}
          style={{ width: '100%', accentColor: '#f59e0b' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
          <span>50%</span><span>100%</span>
        </div>
      </div>

      <div style={divider} />

      {/* Rating */}
      <div style={section}>
        <SectionHeader label="Rating" />
        <PillSelector
          options={RATING_OPTIONS}
          selected={value.min_rating ?? null}
          onChange={(v) => set('min_rating', v)}
        />
      </div>

      {/* Status toggles */}
      <div style={section}>
        <SectionHeader label="Status" />
        <Toggle label="In stock only" checked={!!value.in_stock} onChange={(v) => set('in_stock', v || undefined)} />
        <Toggle label="Has coupon" checked={!!value.has_coupon} onChange={(v) => set('has_coupon', v || undefined)} />
        <Toggle label="Prime eligible" checked={!!value.is_prime} onChange={(v) => set('is_prime', v || undefined)} />
        <Toggle label="Lightning deal" checked={!!value.has_lightning_deal} onChange={(v) => set('has_lightning_deal', v || undefined)} />
        <Toggle label="Best Seller badge" checked={value.badge === 'best_seller'} onChange={(v) => set('badge', v ? 'best_seller' : undefined)} />
        <Toggle label="Amazon's Choice" checked={value.badge === 'amazons_choice'} onChange={(v) => set('badge', v ? 'amazons_choice' : undefined)} />
      </div>

      <div style={divider} />

      {/* Condition */}
      {f.conditions?.length > 0 && (
        <div style={section}>
          <SectionHeader label="Condition" />
          <PillSelector
            options={[{ label: 'Any', value: null }, ...f.conditions.map((c) => ({ label: c, value: c }))]}
            selected={value.condition ?? null}
            onChange={(v) => set('condition', v)}
          />
        </div>
      )}

      {/* Last scraped */}
      <div style={section}>
        <SectionHeader label="Last scraped" />
        <PillSelector
          options={SCRAPED_OPTIONS}
          selected={value.scraped_within_days ?? null}
          onChange={(v) => set('scraped_within_days', v)}
        />
      </div>

      <div style={divider} />

      {/* Sort */}
      <div style={section}>
        <SectionHeader label="Sort" />
        <select
          value={value.sort || 'match_score_desc'}
          onChange={(e) => set('sort', e.target.value)}
          style={{
            width: '100%',
            padding: '6px 8px',
            borderRadius: 6,
            border: '1px solid var(--border)',
            background: 'var(--bg-input, var(--bg-surface))',
            color: 'var(--text)',
            fontSize: 13,
          }}
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* Reset */}
      <button
        onClick={onReset}
        style={{
          marginTop: 'auto',
          padding: '8px 0',
          background: 'none',
          border: 'none',
          color: 'var(--text-muted)',
          cursor: 'pointer',
          fontSize: 13,
          textDecoration: 'underline',
          textAlign: 'center',
        }}
      >
        Reset all filters
      </button>

      <style jsx>{`
        input[type='range'] {
          accent-color: #f59e0b;
        }
        input[type='checkbox'] {
          accent-color: #f59e0b;
        }
      `}</style>
    </div>
  );
}
