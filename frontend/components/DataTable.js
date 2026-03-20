import { useState, useMemo, useEffect } from 'react';

export default function DataTable({
  columns,
  data,
  searchable = true,
  sortable = true,
  pagination = true,
  pageSize = 10,
  emptyMessage = 'No results found',
}) {
  const [search,  setSearch]  = useState('');
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [page,    setPage]    = useState(1);

  // Reset to page 1 when data or search changes
  useEffect(() => { setPage(1); }, [data, search]);

  const filtered = useMemo(() => {
    if (!search.trim()) return data;
    const q = search.toLowerCase();
    return data.filter(row =>
      columns.some(col => col.accessor(row)?.toString().toLowerCase().includes(q))
    );
  }, [data, search, columns]);

  const sorted = useMemo(() => {
    if (!sortCol) return filtered;
    return [...filtered].sort((a, b) => {
      const av = sortCol.accessor(a), bv = sortCol.accessor(b);
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filtered, sortCol, sortDir]);

  const totalPages = Math.ceil(sorted.length / pageSize);
  const paged = useMemo(() =>
    pagination ? sorted.slice((page - 1) * pageSize, page * pageSize) : sorted,
    [sorted, page, pageSize, pagination]
  );

  const handleSort = (col) => {
    if (!sortable || col.sortable === false) return;
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('asc'); }
  };

  const SortArrow = ({ col }) => {
    if (!sortable || col.sortable === false) return null;
    if (sortCol !== col) return (
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#D1D5DB" strokeWidth="2">
        <path d="M7 10l5-5 5 5M7 14l5 5 5-5" />
      </svg>
    );
    return (
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#2563EB" strokeWidth="2.5">
        <path d={sortDir === 'asc' ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'} />
      </svg>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>

      {/* Search bar */}
      {searchable && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ position: 'relative', maxWidth: '320px', flex: 1 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" strokeWidth="2"
              style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              type="search"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search…"
              aria-label="Search table"
              autoComplete="off"
              style={{
                width: '100%', paddingLeft: '34px', paddingRight: '12px', paddingTop: '8px', paddingBottom: '8px',
                background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '8px',
                fontSize: '13px', color: '#111827', outline: 'none',
                transition: 'border-color 0.15s, box-shadow 0.15s',
              }}
              onFocus={e => { e.target.style.borderColor = '#2563EB'; e.target.style.boxShadow = '0 0 0 3px rgba(37,99,235,0.08)'; }}
              onBlur={e => { e.target.style.borderColor = '#E5E7EB'; e.target.style.boxShadow = 'none'; }}
            />
          </div>
          <span style={{ fontSize: '12px', color: '#9CA3AF', whiteSpace: 'nowrap' }}>
            {filtered.length} result{filtered.length !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      {/* Table */}
      <div style={{ background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '12px', overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }} role="table">
            <thead>
              <tr style={{ background: '#F9FAFB', borderBottom: '1px solid #E5E7EB' }}>
                {columns.map((col, i) => (
                  <th
                    key={i}
                    onClick={() => handleSort(col)}
                    aria-sort={sortCol === col ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
                    style={{
                      padding: '11px 20px', textAlign: 'left',
                      fontSize: '11px', fontWeight: 600, color: '#6B7280',
                      textTransform: 'uppercase', letterSpacing: '0.06em',
                      cursor: sortable && col.sortable !== false ? 'pointer' : 'default',
                      userSelect: 'none', whiteSpace: 'nowrap',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {col.header}
                      <SortArrow col={col} />
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paged.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} style={{ padding: '48px', textAlign: 'center' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                      </svg>
                      <span style={{ fontSize: '14px', color: '#9CA3AF' }}>{emptyMessage}</span>
                    </div>
                  </td>
                </tr>
              ) : paged.map((row, ri) => (
                <tr key={ri}
                  style={{ borderBottom: ri < paged.length - 1 ? '1px solid #F3F4F6' : 'none', transition: 'background 0.1s' }}
                  onMouseEnter={e => e.currentTarget.style.background = '#F9FAFB'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  {columns.map((col, ci) => (
                    <td key={ci} style={{ padding: '13px 20px', fontSize: '14px', color: '#111827' }}>
                      {col.render ? col.render(row) : (
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block' }}>
                          {col.accessor(row)}
                        </span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {pagination && totalPages > 1 && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '10px 16px', background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '10px',
        }}>
          <span style={{ fontSize: '13px', color: '#6B7280' }}>
            Showing <strong style={{ color: '#111827' }}>{(page - 1) * pageSize + 1}</strong>–
            <strong style={{ color: '#111827' }}>{Math.min(page * pageSize, sorted.length)}</strong> of{' '}
            <strong style={{ color: '#111827' }}>{sorted.length}</strong>
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <PageBtn label="← Prev" onClick={() => setPage(p => Math.max(1, p - 1))}    disabled={page === 1} />
            {getPageRange(page, totalPages).map((p, i) =>
              p === '…' ? (
                <span key={i} style={{ padding: '0 6px', color: '#9CA3AF', fontSize: '13px' }}>…</span>
              ) : (
                <PageBtn key={p} label={p} onClick={() => setPage(p)} active={page === p} />
              )
            )}
            <PageBtn label="Next →" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} />
          </div>
        </div>
      )}
    </div>
  );
}

function PageBtn({ label, onClick, disabled, active }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-current={active ? 'page' : undefined}
      style={{
        minWidth: '34px', height: '34px', padding: '0 8px',
        borderRadius: '7px', border: active ? 'none' : '1px solid #E5E7EB',
        background: active ? '#2563EB' : 'transparent',
        color: active ? '#FFFFFF' : disabled ? '#D1D5DB' : '#374151',
        fontSize: '13px', fontWeight: active ? 600 : 400,
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'all 0.12s',
      }}
    >
      {label}
    </button>
  );
}

function getPageRange(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, '…', total];
  if (current >= total - 3) return [1, '…', total - 4, total - 3, total - 2, total - 1, total];
  return [1, '…', current - 1, current, current + 1, '…', total];
}
