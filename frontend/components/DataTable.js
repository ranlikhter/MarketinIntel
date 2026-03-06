
import { useState, useMemo } from 'react';
import { Input } from './UI';

export default function DataTable({ columns, data, searchable = true, sortable = true, pagination = true, pageSize = 10, emptyMessage = 'No data' }) {
  const [search, setSearch] = useState('');
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    if (!search) return data;
    return data.filter(row => columns.some(c => c.accessor(row)?.toString().toLowerCase().includes(search.toLowerCase())));
  }, [data, search, columns]);

  const sorted = useMemo(() => {
    if (!sortCol) return filtered;
    return [...filtered].sort((a, b) => {
      const av = sortCol.accessor(a), bv = sortCol.accessor(b);
      return av < bv ? (sortDir === 'asc' ? -1 : 1) : av > bv ? (sortDir === 'asc' ? 1 : -1) : 0;
    });
  }, [filtered, sortCol, sortDir]);

  const totalPages = Math.ceil(sorted.length / pageSize);
  const paged = useMemo(() => pagination ? sorted.slice((page-1)*pageSize, page*pageSize) : sorted, [sorted, page, pageSize, pagination]);

  const handleSort = col => {
    if (!sortable || !col.sortable) return;
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('asc'); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {searchable && (
        <div style={{ position: 'relative', maxWidth: '320px' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#606080" strokeWidth="2"
            style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
          <Input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} placeholder="Search..." style={{ paddingLeft: '36px' }} />
        </div>
      )}

      <div style={{ background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px', overflow: 'hidden' }}>
        {/* Head */}
        <div style={{ display: 'grid', gridTemplateColumns: columns.map(() => '1fr').join(' '), padding: '10px 20px', borderBottom: '1px solid #1E1E2E', gap: '16px' }}>
          {columns.map((col, i) => (
            <div key={i} onClick={() => handleSort(col)} style={{
              fontSize: '10px', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em',
              color: sortCol === col ? '#F59E0B' : '#606080', textTransform: 'uppercase',
              cursor: sortable && col.sortable ? 'pointer' : 'default',
              display: 'flex', alignItems: 'center', gap: '4px', userSelect: 'none',
            }}>
              {col.header}
              {sortable && col.sortable && sortCol === col && (
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d={sortDir === 'asc' ? 'M18 15l-6-6-6 6' : 'M6 9l6 6 6-6'} />
                </svg>
              )}
            </div>
          ))}
        </div>

        {/* Rows */}
        {paged.length === 0 ? (
          <div style={{ padding: '48px', textAlign: 'center', color: '#3A3A58', fontSize: '13px', fontFamily: 'IBM Plex Mono, monospace' }}>{emptyMessage}</div>
        ) : paged.map((row, ri) => (
          <div key={ri} style={{
            display: 'grid', gridTemplateColumns: columns.map(() => '1fr').join(' '),
            padding: '14px 20px', borderBottom: ri < paged.length-1 ? '1px solid #1E1E2E' : 'none',
            gap: '16px', alignItems: 'center', transition: 'background 0.1s',
          }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(245,158,11,0.03)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            {columns.map((col, ci) => (
              <div key={ci} style={{ fontSize: '13px', color: '#F0F0FA', minWidth: 0 }}>
                {col.render ? col.render(row) : <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block' }}>{col.accessor(row)}</span>}
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Pagination */}
      {pagination && totalPages > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace' }}>
            {(page-1)*pageSize+1}–{Math.min(page*pageSize, sorted.length)} of {sorted.length}
          </span>
          <div style={{ display: 'flex', gap: '4px' }}>
            {[...Array(totalPages)].map((_, i) => {
              const p = i+1;
              const show = p === 1 || p === totalPages || Math.abs(p - page) <= 1;
              const ellipsis = Math.abs(p - page) === 2 && p !== 1 && p !== totalPages;
              if (ellipsis) return <span key={p} style={{ padding: '6px 4px', color: '#3A3A58', fontSize: '12px' }}>…</span>;
              if (!show) return null;
              return (
                <button key={p} onClick={() => setPage(p)} style={{
                  width: '32px', height: '32px', borderRadius: '6px', border: 'none',
                  background: p === page ? '#F59E0B' : 'transparent',
                  color: p === page ? '#0A0A0F' : '#9090B8',
                  fontFamily: 'IBM Plex Mono, monospace', fontSize: '12px', cursor: 'pointer',
                  transition: 'background 0.15s',
                }}>{p}</button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
