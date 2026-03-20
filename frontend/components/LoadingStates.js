import { Spinner } from './UI';

const pulseStyle = {
  animation: 'loading-pulse 1.6s ease-in-out infinite',
  background: 'linear-gradient(90deg, var(--bg-surface) 25%, var(--bg-elevated) 50%, var(--bg-surface) 75%)',
  backgroundSize: '200% 100%',
};

function PulseKeyframes() {
  return (
    <style jsx global>{`
      @keyframes loading-pulse {
        0%, 100% { background-position: 200% 0; }
        50% { background-position: -200% 0; }
      }
    `}</style>
  );
}

function Skel({ w = '100%', h = '14px', r = '8px', style = {} }) {
  return (
    <div
      style={{
        width: w,
        height: h,
        borderRadius: r,
        flexShrink: 0,
        ...pulseStyle,
        ...style,
      }}
    />
  );
}

export function LoadingSpinner({ size = 'md', color = '#2563EB' }) {
  const sizes = { sm: 16, md: 28, lg: 44, xl: 60 };
  return <Spinner size={sizes[size] || sizes.md} color={color} />;
}

export function LoadingScreen({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4" style={{ background: 'var(--bg-base)' }}>
      <LoadingSpinner size="xl" />
      <p className="text-base" style={{ color: 'var(--text-muted)' }}>{message}</p>
      <PulseKeyframes />
    </div>
  );
}

export function SkeletonStats() {
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[0, 1, 2].map((i) => (
          <div key={i} className="rounded-2xl p-6" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <Skel w="55%" h="10px" style={{ marginBottom: '16px' }} />
            <Skel w="35%" h="36px" r="10px" style={{ marginBottom: '12px' }} />
            <Skel w="28%" h="10px" />
          </div>
        ))}
      </div>
      <PulseKeyframes />
    </>
  );
}

export function SkeletonCard() {
  return (
    <>
      <div className="rounded-2xl p-6 space-y-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
        <Skel w="38%" h="22px" />
        <Skel h="128px" r="12px" />
        <Skel w="100%" h="14px" />
        <Skel w="74%" h="14px" />
        <div className="flex items-center justify-between pt-4" style={{ borderTop: '1px solid var(--border)' }}>
          <Skel w="80px" h="32px" r="10px" />
          <Skel w="96px" h="32px" r="10px" />
        </div>
      </div>
      <PulseKeyframes />
    </>
  );
}

export function SkeletonChart() {
  return (
    <>
      <div className="rounded-2xl p-6" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
        <Skel w="28%" h="22px" style={{ marginBottom: '24px' }} />
        <Skel h="256px" r="12px" />
      </div>
      <PulseKeyframes />
    </>
  );
}

export function SkeletonTable({ rows = 5 }) {
  return (
    <>
      <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
        <div className="px-6 py-4" style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-elevated)' }}>
          <div className="flex gap-4">
            {[40, 20, 20, 20].map((w, i) => (
              <Skel key={i} w={`${w}%`} h="12px" />
            ))}
          </div>
        </div>
        <div>
          {[...Array(rows)].map((_, i) => (
            <div key={i} className="px-6 py-4" style={{ borderBottom: i < rows - 1 ? '1px solid var(--border)' : 'none' }}>
              <div className="flex gap-4">
                {[40, 20, 20, 20].map((w, j) => (
                  <Skel key={j} w={`${w}%`} h="14px" />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      <PulseKeyframes />
    </>
  );
}

export function PageLoadingState() {
  return (
    <div className="flex flex-col gap-6">
      <SkeletonStats />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SkeletonChart />
        <SkeletonChart />
      </div>
      <SkeletonTable />
    </div>
  );
}
