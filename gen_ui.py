"""Generate all redesigned frontend files for MarketIntel."""
import os

BASE = 'C:/Users/ranli/Scrape/frontend'

def w(path, content):
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  ok {path}')

# ═══════════════════════════════════════════════════════════
# 1. components/UI.js — Design System Primitives
# ═══════════════════════════════════════════════════════════
w('components/UI.js', r"""
// MarketIntel Design System — shared UI primitives

export const C = {
  bg: '#0A0A0F', surface: '#111118', surface2: '#16161E',
  border: '#1E1E2E', muted: '#2A2A3E',
  amber: '#F59E0B', amberBright: '#FCD34D',
  text: '#F0F0FA', textMuted: '#9090B8', textDim: '#606080', textFaint: '#3A3A58',
  up: '#10B981', down: '#EF4444',
};

export function Spinner({ size = 20, color = '#F59E0B' }) {
  return (
    <>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ animation: 'ui-spin 0.7s linear infinite', flexShrink: 0 }}>
        <circle cx="12" cy="12" r="9" stroke={color} strokeWidth="2" strokeOpacity="0.2" />
        <path d="M21 12a9 9 0 00-9-9" stroke={color} strokeWidth="2" strokeLinecap="round" />
      </svg>
      <style jsx global>{`@keyframes ui-spin { to { transform: rotate(360deg); } }`}</style>
    </>
  );
}

export function Btn({ children, variant = 'primary', size = 'md', disabled, loading, onClick, type = 'button', style: s = {} }) {
  const base = {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '7px',
    border: 'none', cursor: disabled || loading ? 'not-allowed' : 'pointer',
    fontFamily: 'Syne, sans-serif', letterSpacing: '0.01em',
    transition: 'opacity 0.15s, box-shadow 0.15s', opacity: disabled || loading ? 0.5 : 1,
    textDecoration: 'none', whiteSpace: 'nowrap',
  };
  const sizes = {
    sm: { padding: '6px 14px', fontSize: '12px', borderRadius: '6px', fontWeight: 600 },
    md: { padding: '9px 20px', fontSize: '13px', borderRadius: '8px', fontWeight: 700 },
    lg: { padding: '12px 28px', fontSize: '14px', borderRadius: '9px', fontWeight: 700 },
  };
  const variants = {
    primary:   { background: '#F59E0B', color: '#0A0A0F', boxShadow: '0 0 20px rgba(245,158,11,0.22)' },
    secondary: { background: 'transparent', color: '#9090B8', border: '1px solid #2A2A3E' },
    danger:    { background: 'transparent', color: '#EF4444', border: '1px solid rgba(239,68,68,0.3)' },
    ghost:     { background: 'transparent', color: '#606080' },
    outline:   { background: 'transparent', color: '#F59E0B', border: '1px solid rgba(245,158,11,0.35)' },
    success:   { background: 'rgba(16,185,129,0.12)', color: '#10B981', border: '1px solid rgba(16,185,129,0.25)' },
  };
  const iconColor = variant === 'primary' ? '#0A0A0F' : '#F59E0B';
  return (
    <button type={type} onClick={onClick} disabled={disabled || loading}
      style={{ ...base, ...sizes[size], ...variants[variant], ...s }}>
      {loading ? <Spinner size={size === 'sm' ? 12 : 15} color={iconColor} /> : children}
    </button>
  );
}

export function Input({ id, name, type = 'text', value, onChange, placeholder, required, autoComplete, style: s = {}, monospace }) {
  return (
    <input id={id} name={name} type={type} value={value} onChange={onChange}
      placeholder={placeholder} required={required} autoComplete={autoComplete}
      style={{
        width: '100%', background: '#0A0A0F', border: '1px solid #1E1E2E',
        borderRadius: '8px', padding: '10px 14px', color: '#F0F0FA',
        fontFamily: monospace ? 'IBM Plex Mono, monospace' : 'IBM Plex Sans, sans-serif',
        fontSize: '13px', outline: 'none', boxSizing: 'border-box',
        transition: 'border-color 0.15s, box-shadow 0.15s', ...s,
      }}
      onFocus={e => { e.target.style.borderColor = '#F59E0B'; e.target.style.boxShadow = '0 0 0 2px rgba(245,158,11,0.12)'; }}
      onBlur={e => { e.target.style.borderColor = '#1E1E2E'; e.target.style.boxShadow = 'none'; }}
    />
  );
}

export function Textarea({ id, name, value, onChange, placeholder, rows = 3, style: s = {} }) {
  return (
    <textarea id={id} name={name} value={value} onChange={onChange}
      placeholder={placeholder} rows={rows}
      style={{
        width: '100%', background: '#0A0A0F', border: '1px solid #1E1E2E',
        borderRadius: '8px', padding: '10px 14px', color: '#F0F0FA',
        fontFamily: 'IBM Plex Mono, monospace', fontSize: '12px',
        outline: 'none', resize: 'vertical', boxSizing: 'border-box',
        transition: 'border-color 0.15s, box-shadow 0.15s', ...s,
      }}
      onFocus={e => { e.target.style.borderColor = '#F59E0B'; e.target.style.boxShadow = '0 0 0 2px rgba(245,158,11,0.12)'; }}
      onBlur={e => { e.target.style.borderColor = '#1E1E2E'; e.target.style.boxShadow = 'none'; }}
    />
  );
}

export function Select({ id, name, value, onChange, children, style: s = {} }) {
  return (
    <select id={id} name={name} value={value} onChange={onChange}
      style={{
        width: '100%', background: '#0A0A0F', border: '1px solid #1E1E2E',
        borderRadius: '8px', padding: '10px 36px 10px 14px', color: '#F0F0FA',
        fontFamily: 'IBM Plex Sans, sans-serif', fontSize: '13px',
        outline: 'none', cursor: 'pointer', boxSizing: 'border-box',
        appearance: 'none', WebkitAppearance: 'none',
        transition: 'border-color 0.15s', ...s,
      }}
      onFocus={e => { e.target.style.borderColor = '#F59E0B'; }}
      onBlur={e => { e.target.style.borderColor = '#1E1E2E'; }}
    >
      {children}
    </select>
  );
}

export function Label({ htmlFor, children, required }) {
  return (
    <label htmlFor={htmlFor} style={{
      display: 'block', fontSize: '10px', fontFamily: 'IBM Plex Mono, monospace',
      color: '#9090B8', letterSpacing: '0.1em', marginBottom: '8px',
      textTransform: 'uppercase',
    }}>
      {children}{required && <span style={{ color: '#F59E0B', marginLeft: '4px' }}>*</span>}
    </label>
  );
}

export function Field({ label, htmlFor, hint, required, error, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {label && <Label htmlFor={htmlFor} required={required}>{label}</Label>}
      {children}
      {hint && !error && <p style={{ marginTop: '6px', fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace' }}>{hint}</p>}
      {error && <p style={{ marginTop: '6px', fontSize: '11px', color: '#EF4444', fontFamily: 'IBM Plex Mono, monospace' }}>{error}</p>}
    </div>
  );
}

export function Card({ children, style: s = {}, hover = false, padding = '24px' }) {
  return (
    <div style={{ background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px', padding, transition: 'border-color 0.2s, box-shadow 0.2s', ...s }}
      onMouseEnter={hover ? e => { e.currentTarget.style.borderColor = 'rgba(245,158,11,0.25)'; e.currentTarget.style.boxShadow = '0 0 24px rgba(245,158,11,0.06)'; } : undefined}
      onMouseLeave={hover ? e => { e.currentTarget.style.borderColor = '#1E1E2E'; e.currentTarget.style.boxShadow = 'none'; } : undefined}
    >
      {children}
    </div>
  );
}

export function Badge({ children, variant = 'neutral' }) {
  const vs = {
    neutral: { background: 'rgba(255,255,255,0.05)', color: '#9090B8', border: '1px solid #1E1E2E' },
    success: { background: 'rgba(16,185,129,0.1)', color: '#10B981', border: '1px solid rgba(16,185,129,0.2)' },
    danger:  { background: 'rgba(239,68,68,0.1)',  color: '#EF4444', border: '1px solid rgba(239,68,68,0.2)' },
    amber:   { background: 'rgba(245,158,11,0.1)', color: '#F59E0B', border: '1px solid rgba(245,158,11,0.2)' },
    purple:  { background: 'rgba(129,140,248,0.1)', color: '#818CF8', border: '1px solid rgba(129,140,248,0.2)' },
    blue:    { background: 'rgba(56,189,248,0.1)', color: '#38BDF8', border: '1px solid rgba(56,189,248,0.2)' },
  };
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', padding: '3px 10px', borderRadius: '20px', fontSize: '10px', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.06em', whiteSpace: 'nowrap', ...vs[variant] }}>
      {children}
    </span>
  );
}

export function PageHeader({ title, subtitle, action, tag }) {
  return (
    <div style={{ marginBottom: '32px' }}>
      {tag && <div style={{ fontSize: '10px', color: '#F59E0B', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.12em', marginBottom: '10px' }}>{tag}</div>}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
        <div>
          <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '28px', color: '#F0F0FA', letterSpacing: '-0.03em', margin: 0 }}>{title}</h1>
          {subtitle && <p style={{ marginTop: '6px', fontSize: '14px', color: '#9090B8', lineHeight: 1.6, margin: '6px 0 0' }}>{subtitle}</p>}
        </div>
        {action && <div style={{ flexShrink: 0 }}>{action}</div>}
      </div>
    </div>
  );
}

export function SectionHeader({ title, sub, action }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
        <h2 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '18px', color: '#F0F0FA', letterSpacing: '-0.02em', margin: 0 }}>{title}</h2>
        {sub && <span style={{ fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace' }}>{sub}</span>}
      </div>
      {action}
    </div>
  );
}

export function Alert({ type = 'info', children }) {
  const s = {
    error:   { bg: 'rgba(239,68,68,0.08)',   border: '1px solid rgba(239,68,68,0.25)',   color: '#EF4444' },
    warning: { bg: 'rgba(245,158,11,0.08)',  border: '1px solid rgba(245,158,11,0.25)',  color: '#F59E0B' },
    success: { bg: 'rgba(16,185,129,0.08)',  border: '1px solid rgba(16,185,129,0.25)',  color: '#10B981' },
    info:    { bg: 'rgba(129,140,248,0.08)', border: '1px solid rgba(129,140,248,0.25)', color: '#818CF8' },
  };
  return (
    <div style={{ background: s[type].bg, border: s[type].border, borderRadius: '8px', padding: '12px 16px', fontSize: '13px', color: s[type].color }}>
      {children}
    </div>
  );
}

export function Divider({ label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
      <div style={{ flex: 1, height: '1px', background: '#1E1E2E' }} />
      {label && <span style={{ fontSize: '11px', color: '#3A3A58', fontFamily: 'IBM Plex Mono, monospace', whiteSpace: 'nowrap' }}>{label}</span>}
      <div style={{ flex: 1, height: '1px', background: '#1E1E2E' }} />
    </div>
  );
}

export function EmptyState({ icon, title, body, action }) {
  return (
    <div style={{ textAlign: 'center', padding: '64px 32px', background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px' }}>
      {icon && <div style={{ marginBottom: '16px', color: '#3A3A58' }}>{icon}</div>}
      <div style={{ fontSize: '10px', color: '#3A3A58', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.12em', marginBottom: '12px' }}>EMPTY STATE</div>
      <h3 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '22px', color: '#F0F0FA', letterSpacing: '-0.02em', marginBottom: '8px' }}>{title}</h3>
      {body && <p style={{ fontSize: '14px', color: '#9090B8', lineHeight: 1.65, maxWidth: '380px', margin: '0 auto 24px' }}>{body}</p>}
      {action}
    </div>
  );
}

export function StatCard({ label, value, color = '#F59E0B', sub, mono = true }) {
  return (
    <div style={{ background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px', padding: '24px 28px' }}>
      <div style={{ fontSize: '10px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '12px' }}>{label.toUpperCase()}</div>
      <div style={{ fontSize: '40px', fontFamily: mono ? 'IBM Plex Mono, monospace' : 'Syne, sans-serif', fontWeight: 700, color, letterSpacing: '-0.03em', lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ marginTop: '8px', fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace' }}>{sub}</div>}
    </div>
  );
}
""")

# ═══════════════════════════════════════════════════════════
# 2. components/Toast.js
# ═══════════════════════════════════════════════════════════
w('components/Toast.js', r"""
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
""")

# ═══════════════════════════════════════════════════════════
# 3. components/Modal.js
# ═══════════════════════════════════════════════════════════
w('components/Modal.js', r"""
import { useEffect } from 'react';
import { Btn } from './UI';

export default function Modal({ isOpen, onClose, title, children, footer, size = 'md' }) {
  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : 'unset';
    return () => { document.body.style.overflow = 'unset'; };
  }, [isOpen]);

  if (!isOpen) return null;

  const widths = { sm: '420px', md: '560px', lg: '720px', xl: '960px' };

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
      {/* Backdrop */}
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', animation: 'modal-fade 0.2s ease-out' }} />

      {/* Panel */}
      <div onClick={e => e.stopPropagation()} style={{
        position: 'relative', width: '100%', maxWidth: widths[size],
        background: '#111118', border: '1px solid #1E1E2E', borderRadius: '12px',
        boxShadow: '0 32px 80px rgba(0,0,0,0.6)', animation: 'modal-scale 0.2s ease-out',
        maxHeight: '90vh', display: 'flex', flexDirection: 'column',
      }}>
        {/* Header */}
        <div style={{ padding: '20px 24px', borderBottom: '1px solid #1E1E2E', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
          <h3 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '17px', color: '#F0F0FA', letterSpacing: '-0.02em', margin: 0 }}>{title}</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#3A3A58', padding: '4px', display: 'flex', borderRadius: '6px', transition: 'color 0.15s' }}
            onMouseEnter={e => e.currentTarget.style.color = '#F0F0FA'} onMouseLeave={e => e.currentTarget.style.color = '#3A3A58'}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12" /></svg>
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>{children}</div>

        {/* Footer */}
        {footer && (
          <div style={{ padding: '16px 24px', borderTop: '1px solid #1E1E2E', display: 'flex', justifyContent: 'flex-end', gap: '10px', flexShrink: 0 }}>
            {footer}
          </div>
        )}
      </div>

      <style jsx global>{`
        @keyframes modal-fade  { from { opacity: 0; } to { opacity: 1; } }
        @keyframes modal-scale { from { opacity: 0; transform: scale(0.96); } to { opacity: 1; transform: scale(1); } }
      `}</style>
    </div>
  );
}

export function ConfirmModal({ isOpen, onClose, onConfirm, title, message, confirmText = 'Confirm', cancelText = 'Cancel', type = 'danger' }) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm"
      footer={<>
        <Btn variant="secondary" onClick={onClose}>{cancelText}</Btn>
        <Btn variant={type === 'danger' ? 'danger' : 'primary'} onClick={() => { onConfirm(); onClose(); }}>{confirmText}</Btn>
      </>}
    >
      <p style={{ fontSize: '14px', color: '#9090B8', lineHeight: 1.65 }}>{message}</p>
    </Modal>
  );
}
""")

# ═══════════════════════════════════════════════════════════
# 4. components/LoadingStates.js
# ═══════════════════════════════════════════════════════════
w('components/LoadingStates.js', r"""
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
""")

# ═══════════════════════════════════════════════════════════
# 5. components/DataTable.js
# ═══════════════════════════════════════════════════════════
w('components/DataTable.js', r"""
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
""")

print("Components done.")
print("Writing pages...")
