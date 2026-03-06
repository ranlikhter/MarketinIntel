
import { createContext, useContext, useState, useCallback } from 'react';

const ToastCtx = createContext();

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const addToast = useCallback((message, type = 'info') => {
    const id = Date.now();
    setToasts(p => [...p, { id, message, type }]);
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 5000);
  }, []);
  const remove = useCallback((id) => setToasts(p => p.filter(t => t.id !== id)), []);
  return (
    <ToastCtx.Provider value={{ addToast }}>
      {children}
      <div style={{ position: 'fixed', top: '16px', right: '16px', zIndex: 9999, display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '360px', width: '100%' }}>
        {toasts.map(t => <ToastItem key={t.id} {...t} onClose={() => remove(t.id)} />)}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

function ToastItem({ message, type, onClose }) {
  const cfg = {
    success: { border: 'rgba(16,185,129,0.35)',  icon: '#10B981', label: 'ok' },
    error:   { border: 'rgba(239,68,68,0.35)',   icon: '#EF4444', label: '✕' },
    warning: { border: 'rgba(245,158,11,0.35)',  icon: '#F59E0B', label: '!' },
    info:    { border: 'rgba(129,140,248,0.35)', icon: '#818CF8', label: 'i' },
  }[type] || { border: 'rgba(255,255,255,0.1)', icon: '#9090B8', label: 'i' };

  return (
    <div style={{
      background: '#16161E', border: `1px solid ${cfg.border}`,
      borderRadius: '10px', padding: '14px 16px',
      display: 'flex', alignItems: 'flex-start', gap: '12px',
      animation: 'toast-in 0.3s ease-out both',
      boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
    }}>
      <div style={{
        width: '24px', height: '24px', borderRadius: '50%', flexShrink: 0,
        background: `rgba(${type === 'success' ? '16,185,129' : type === 'error' ? '239,68,68' : type === 'warning' ? '245,158,11' : '129,140,248'},0.15)`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '12px', fontWeight: 700, color: cfg.icon,
      }}>{cfg.label}</div>
      <p style={{ flex: 1, fontSize: '13px', color: '#F0F0FA', lineHeight: 1.5, margin: 0 }}>{message}</p>
      <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#3A3A58', padding: '0', lineHeight: 1, flexShrink: 0, fontSize: '16px' }}>×</button>
      <style jsx global>{`
        @keyframes toast-in {
          from { opacity: 0; transform: translateX(16px); }
          to   { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </div>
  );
}
