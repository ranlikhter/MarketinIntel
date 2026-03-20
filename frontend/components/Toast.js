import { createContext, useCallback, useContext, useRef, useState } from 'react';

const ToastCtx = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const idCounter = useRef(0);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback((message, type = 'info') => {
    const id = ++idCounter.current;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 5000);
  }, []);

  return (
    <ToastCtx.Provider value={{ addToast, removeToast }}>
      {children}
      <div className="fixed top-20 right-4 z-50 space-y-2 max-w-sm w-full">
        {toasts.map((toast) => (
          <ToastItem
            key={toast.id}
            {...toast}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastCtx);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}

function ToastItem({ message, type, onClose }) {
  const styles = {
    success: { bg: 'rgba(5,150,105,0.15)', border: 'rgba(5,150,105,0.25)', iconColor: '#34d399' },
    error: { bg: 'rgba(239,68,68,0.15)', border: 'rgba(239,68,68,0.25)', iconColor: '#f87171' },
    warning: { bg: 'rgba(245,158,11,0.15)', border: 'rgba(245,158,11,0.25)', iconColor: '#fbbf24' },
    info: { bg: 'rgba(37,99,235,0.15)', border: 'rgba(37,99,235,0.25)', iconColor: '#60a5fa' },
  };

  const icons = {
    success: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    error: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    warning: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    info: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  };

  const style = styles[type] || styles.info;

  return (
    <div
      className="rounded-xl px-4 py-3 flex items-start gap-3 shadow-glass"
      style={{ background: style.bg, border: `1px solid ${style.border}` }}
    >
      <div className="flex-shrink-0 mt-0.5" style={{ color: style.iconColor }}>
        {icons[type] || icons.info}
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium text-white">{message}</p>
      </div>
      <button
        onClick={onClose}
        className="flex-shrink-0 text-white/30 hover:text-white transition-colors"
        aria-label="Close notification"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}
