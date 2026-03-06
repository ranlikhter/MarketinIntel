
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
import { useState, useEffect, useMemo } from 'react';

export default function DataTable({
  columns,
  data,
  searchable = true,
  sortable = true,
  pagination = true,
  pageSize = 10,
  emptyMessage = 'No data available'
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc');
  const [currentPage, setCurrentPage] = useState(1);

  // Reset to page 1 when data changes
  useEffect(() => { setCurrentPage(1); }, [data]);

  const filteredData = useMemo(() => {
    if (!searchTerm) return data;
    return data.filter(row =>
      columns.some(col => {
        const value = col.accessor(row);
        return value?.toString().toLowerCase().includes(searchTerm.toLowerCase());
      })
    );
  }, [data, searchTerm, columns]);

  const sortedData = useMemo(() => {
    if (!sortColumn) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aVal = sortColumn.accessor(a);
      const bVal = sortColumn.accessor(b);
      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredData, sortColumn, sortDirection]);

  const totalPages = Math.ceil(sortedData.length / pageSize);
  const paginatedData = useMemo(() => {
    if (!pagination) return sortedData;
    const start = (currentPage - 1) * pageSize;
    return sortedData.slice(start, start + pageSize);
  }, [sortedData, currentPage, pageSize, pagination]);

  const handleSort = (column) => {
    if (!sortable || !column.sortable) return;
    if (sortColumn === column) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  return (
    <div className="space-y-4">
      {searchable && (
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg className="h-4 w-4" style={{ color: 'var(--text-muted)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
              placeholder="Search..."
              className="block w-full pl-9 pr-3 py-2 glass-input rounded-xl text-sm focus:outline-none"
            />
          </div>
          <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {paginatedData.length} of {filteredData.length}
          </div>
        </div>
      )}

      <div className="rounded-2xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
        <table className="min-w-full dark-table">
          <thead>
            <tr>
              {columns.map((column, idx) => (
                <th
                  key={idx}
                  className={`text-left ${sortable && column.sortable !== false ? 'cursor-pointer hover:bg-white/5 select-none' : ''}`}
                  onClick={() => handleSort(column)}
                >
                  <div className="flex items-center gap-2">
                    <span>{column.header}</span>
                    {sortable && column.sortable !== false && sortColumn === column && (
                      <svg
                        className={`w-3.5 h-3.5 text-amber-400 transition-transform ${sortDirection === 'desc' ? 'rotate-180' : ''}`}
                        fill="none" viewBox="0 0 24 24" stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                      </svg>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-6 py-12 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                  <div className="flex flex-col items-center">
                    <svg className="w-10 h-10 mb-3" style={{ color: 'var(--text-dim)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                    </svg>
                    {emptyMessage}
                  </div>
                </td>
              </tr>
            ) : (
              paginatedData.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  {columns.map((column, colIdx) => (
                    <td key={colIdx} className="whitespace-nowrap text-white text-sm">
                      {column.render ? column.render(row) : column.accessor(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {pagination && totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 rounded-xl" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Showing <span className="font-medium text-white">{(currentPage - 1) * pageSize + 1}</span>–
            <span className="font-medium text-white">{Math.min(currentPage * pageSize, sortedData.length)}</span> of{' '}
            <span className="font-medium text-white">{sortedData.length}</span>
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1.5 rounded-lg text-sm text-white/50 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              style={{ border: '1px solid var(--border)' }}
            >
              Prev
            </button>
            {(() => {
              const maxVisible = 5;
              let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
              let end = start + maxVisible - 1;
              if (end > totalPages) { end = totalPages; start = Math.max(1, end - maxVisible + 1); }
              return [...Array(end - start + 1)].map((_, idx) => {
                const page = start + idx;
                return (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      currentPage === page ? 'gradient-brand text-white shadow-gradient' : 'text-white/50 hover:text-white hover:bg-white/5'
                    }`}
                    style={currentPage !== page ? { border: '1px solid var(--border)' } : {}}
                  >
                    {page}
                  </button>
                );
              });
            })()}
            <button
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1.5 rounded-lg text-sm text-white/50 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              style={{ border: '1px solid var(--border)' }}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
