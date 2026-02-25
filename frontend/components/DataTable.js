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
