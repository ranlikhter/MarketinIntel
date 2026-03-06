
import { Spinner } from './UI';

const pulse = { animation: 'skel-pulse 1.6s ease-in-out infinite', background: 'linear-gradient(90deg, #16161E 25%, #1E1E2E 50%, #16161E 75%)', backgroundSize: '200% 100%' };

export function LoadingSpinner({ size = 'md' }) {
  const sz = { sm: 16, md: 28, lg: 44, xl: 60 }[size] || 28;
  return <Spinner size={sz} />;
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
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', gap: '16px', background: '#0A0A0F' }}>
      <Spinner size={40} />
      <p style={{ fontSize: '13px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace' }}>{message}</p>
      <style jsx global>{`@keyframes skel-pulse { 0%,100%{background-position:200% 0} 50%{background-position:-200% 0} }`}</style>
    <div className="flex flex-col items-center justify-center min-h-screen" style={{ background: 'var(--bg-base)' }}>
      <LoadingSpinner size="xl" />
      <p className="mt-4 text-base" style={{ color: 'var(--text-muted)' }}>{message}</p>
    </div>
  );
}

function Skel({ w = '100%', h = '14px', r = '6px', style: s = {} }) {
  return <div style={{ width: w, height: h, borderRadius: r, flexShrink: 0, ...pulse, ...s }} />;
}

export function SkeletonStats() {
  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '16px' }}>
        {[0,1,2].map(i => (
          <div key={i} style={{ background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px', padding: '24px 28px' }}>
            <Skel w="60%" h="10px" style={{ marginBottom: '16px' }} />
            <Skel w="40%" h="40px" r="8px" style={{ marginBottom: '12px' }} />
            <Skel w="30%" h="10px" />
          </div>
        ))}
      </div>
      <style jsx global>{`@keyframes skel-pulse { 0%,100%{background-position:200% 0} 50%{background-position:-200% 0} }`}</style>
    </>
  const widthClass = widthClasses[width] || 'w-full';
  return (
    <div className={`h-4 rounded animate-pulse ${widthClass}`} style={{ background: 'var(--bg-elevated)' }} />
  );
}

export function SkeletonCard() {
  return (
    <div style={{ background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px', padding: '24px' }}>
      <Skel w="50%" h="14px" style={{ marginBottom: '20px' }} />
      <Skel h="120px" r="8px" style={{ marginBottom: '16px' }} />
      <Skel w="80%" h="12px" style={{ marginBottom: '8px' }} />
      <Skel w="60%" h="12px" />
      <style jsx global>{`@keyframes skel-pulse { 0%,100%{background-position:200% 0} 50%{background-position:-200% 0} }`}</style>
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

export function SkeletonChart() {
  return (
    <div style={{ background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px', padding: '24px' }}>
      <Skel w="30%" h="14px" style={{ marginBottom: '24px' }} />
      <Skel h="200px" r="8px" />
      <style jsx global>{`@keyframes skel-pulse { 0%,100%{background-position:200% 0} 50%{background-position:-200% 0} }`}</style>
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

export function SkeletonTable({ rows = 5 }) {
  return (
    <div style={{ background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px', overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid #1E1E2E', display: 'flex', gap: '24px' }}>
        {[40,20,20,20].map((w, i) => <Skel key={i} w={w+'%'} h="10px" />)}
      </div>
      {Array(rows).fill(0).map((_, i) => (
        <div key={i} style={{ padding: '16px 20px', borderBottom: i < rows-1 ? '1px solid #1E1E2E' : 'none', display: 'flex', gap: '24px', alignItems: 'center' }}>
          {[40,20,20,20].map((w, j) => <Skel key={j} w={w+'%'} h="12px" />)}
        </div>
      ))}
      <style jsx global>{`@keyframes skel-pulse { 0%,100%{background-position:200% 0} 50%{background-position:-200% 0} }`}</style>
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <SkeletonStats />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        <SkeletonChart /><SkeletonChart />
      </div>
      <SkeletonTable />
    </div>
  );
}
