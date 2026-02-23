export function LoadingSpinner({ size = 'md', color = 'primary' }) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
    xl: 'h-16 w-16'
  };

  const colorClasses = {
    primary: 'border-amber-500',
    white:   'border-white',
    gray:    'border-white/30'
  };

  return (
    <div className={`animate-spin rounded-full border-2 border-t-transparent ${sizeClasses[size]} ${colorClasses[color]}`} />
  );
}

export function LoadingScreen({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen" style={{ background: 'var(--bg-base)' }}>
      <LoadingSpinner size="xl" />
      <p className="mt-4 text-base" style={{ color: 'var(--text-muted)' }}>{message}</p>
    </div>
  );
}

export function SkeletonLine({ width = 'full' }) {
  const widthClasses = {
    full: 'w-full',
    '3/4': 'w-3/4',
    '1/2': 'w-1/2',
    '1/4': 'w-1/4',
    '1/3': 'w-1/3'
  };

  return (
    <div className={`h-4 rounded animate-pulse ${widthClasses[width]}`} style={{ background: 'var(--bg-elevated)' }} />
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded-2xl p-6 space-y-4 animate-pulse" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
      <div className="flex items-center justify-between">
        <div className="h-6 rounded w-1/3" style={{ background: 'var(--bg-elevated)' }} />
        <div className="h-5 rounded w-16" style={{ background: 'var(--bg-elevated)' }} />
      </div>
      <div className="h-32 rounded" style={{ background: 'var(--bg-elevated)' }} />
      <div className="space-y-2">
        <div className="h-4 rounded w-full" style={{ background: 'var(--bg-elevated)' }} />
        <div className="h-4 rounded w-3/4" style={{ background: 'var(--bg-elevated)' }} />
      </div>
      <div className="flex justify-between items-center pt-4" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="h-8 rounded w-20" style={{ background: 'var(--bg-elevated)' }} />
        <div className="h-8 rounded w-24" style={{ background: 'var(--bg-elevated)' }} />
      </div>
    </div>
  );
}

export function SkeletonTable({ rows = 5 }) {
  return (
    <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
      <div className="px-6 py-4" style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-elevated)' }}>
        <div className="flex gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-4 rounded flex-1 animate-pulse" style={{ background: 'var(--bg-surface)' }} />
          ))}
        </div>
      </div>
      <div>
        {[...Array(rows)].map((_, i) => (
          <div key={i} className="px-6 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <div className="flex gap-4">
              {[...Array(4)].map((_, j) => (
                <div key={j} className="h-4 rounded flex-1 animate-pulse" style={{ background: 'var(--bg-elevated)' }} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonStats() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="rounded-2xl p-6 animate-pulse" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="flex items-center justify-between mb-4">
            <div className="h-12 w-12 rounded-xl" style={{ background: 'var(--bg-elevated)' }} />
            <div className="h-6 w-16 rounded" style={{ background: 'var(--bg-elevated)' }} />
          </div>
          <div className="h-8 rounded w-20 mb-2" style={{ background: 'var(--bg-elevated)' }} />
          <div className="h-4 rounded w-32" style={{ background: 'var(--bg-elevated)' }} />
        </div>
      ))}
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="rounded-2xl p-6" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
      <div className="h-6 rounded w-1/4 mb-6 animate-pulse" style={{ background: 'var(--bg-elevated)' }} />
      <div className="h-64 rounded animate-pulse" style={{ background: 'var(--bg-elevated)' }} />
    </div>
  );
}

export function PageLoadingState() {
  return (
    <div className="space-y-6">
      <SkeletonStats />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SkeletonChart />
        <SkeletonChart />
      </div>
      <SkeletonTable />
    </div>
  );
}
