
import { Spinner } from './UI';

const pulse = { animation: 'skel-pulse 1.6s ease-in-out infinite', background: 'linear-gradient(90deg, #16161E 25%, #1E1E2E 50%, #16161E 75%)', backgroundSize: '200% 100%' };

export function LoadingSpinner({ size = 'md' }) {
  const sz = { sm: 16, md: 28, lg: 44, xl: 60 }[size] || 28;
  return <Spinner size={sz} />;
}

export function LoadingScreen({ message = 'Loading...' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', gap: '16px', background: '#0A0A0F' }}>
      <Spinner size={40} />
      <p style={{ fontSize: '13px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace' }}>{message}</p>
      <style jsx global>{`@keyframes skel-pulse { 0%,100%{background-position:200% 0} 50%{background-position:-200% 0} }`}</style>
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
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div style={{ background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px', padding: '24px' }}>
      <Skel w="30%" h="14px" style={{ marginBottom: '24px' }} />
      <Skel h="200px" r="8px" />
      <style jsx global>{`@keyframes skel-pulse { 0%,100%{background-position:200% 0} 50%{background-position:-200% 0} }`}</style>
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
