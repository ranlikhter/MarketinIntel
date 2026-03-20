import { useState } from 'react';

// MarketIntel Design System — shared UI primitives

export const C = {
  // Using CSS custom properties for theming
  bg: 'var(--color-light-background)',
  surface: 'var(--color-light-surface)',
  surface2: 'var(--color-light-surface)', // Using surface for consistency in light theme
  border: 'var(--color-light-border)',
  muted: 'var(--color-ink-100)', // A lighter muted tone
  amber: 'var(--color-amber-500)',
  amberBright: 'var(--color-amber-300)',
  text: 'var(--color-light-text)',
  textMuted: 'var(--color-light-textMuted)',
  textDim: 'var(--color-ink-300)',
  textFaint: 'var(--color-ink-400)',
  up: 'var(--color-signal-up)',
  down: 'var(--color-signal-down)',
};

export function Spinner({ size = 20, color = 'var(--color-amber-500)' }) {
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
    primary:   { background: 'var(--color-amber-500)', color: 'var(--color-ink-900)', boxShadow: 'var(--box-shadow-gradient-lg)' },
    secondary: { background: 'var(--color-glass-light)', color: 'var(--color-light-textMuted)', border: '1px solid var(--color-glass-borderLight)', backdropFilter: 'blur(5px)' },
    danger:    { background: 'rgba(239,68,68,0.1)',  color: 'var(--color-signal-down)', border: '1px solid rgba(239,68,68,0.2)', backdropFilter: 'blur(5px)' },
    ghost:     { background: 'transparent', color: 'var(--color-ink-300)' },
    outline:   { background: 'rgba(245,158,11,0.1)', color: 'var(--color-amber-500)', border: '1px solid rgba(245,158,11,0.2)', backdropFilter: 'blur(5px)' },
    success:   { background: 'rgba(16,185,129,0.1)', color: 'var(--color-signal-up)', border: '1px solid rgba(16,185,129,0.2)', backdropFilter: 'blur(5px)' },
  };
  const iconColor = variant === 'primary' ? 'var(--color-ink-900)' : 'var(--color-amber-500)';
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
        width: '100%', background: 'var(--color-glass-light)', border: '1px solid var(--color-glass-borderLight)',
        borderRadius: '8px', padding: '10px 14px', color: 'var(--color-light-text)',
        fontFamily: monospace ? 'IBM Plex Mono, monospace' : 'IBM Plex Sans, sans-serif',
        fontSize: '13px', outline: 'none', boxSizing: 'border-box',
        transition: 'border-color 0.15s, box-shadow 0.15s', ...s,
        backdropFilter: 'blur(5px)', // Glassmorphism effect
      }}
      onFocus={e => { e.target.style.borderColor = 'var(--color-amber-500)'; e.target.style.boxShadow = '0 0 0 2px rgba(245,158,11,0.12)'; }}
      onBlur={e => { e.target.style.borderColor = 'var(--color-glass-borderLight)'; e.target.style.boxShadow = 'none'; }}
    />
  );
}

export function Textarea({ id, name, value, onChange, placeholder, rows = 3, style: s = {} }) {
  return (
    <textarea id={id} name={name} value={value} onChange={onChange}
      placeholder={placeholder} rows={rows}
      style={{
        width: '100%', background: 'var(--color-glass-light)', border: '1px solid var(--color-glass-borderLight)',
        borderRadius: '8px', padding: '10px 14px', color: 'var(--color-light-text)',
        fontFamily: 'IBM Plex Mono, monospace', fontSize: '12px',
        outline: 'none', resize: 'vertical', boxSizing: 'border-box',
        transition: 'border-color 0.15s, box-shadow 0.15s', ...s,
        backdropFilter: 'blur(5px)', // Glassmorphism effect
      }}
      onFocus={e => { e.target.style.borderColor = 'var(--color-amber-500)'; e.target.style.boxShadow = '0 0 0 2px rgba(245,158,11,0.12)'; }}
      onBlur={e => { e.target.style.borderColor = 'var(--color-glass-borderLight)'; e.target.style.boxShadow = 'none'; }}
    />
  );
}

export function Select({ id, name, value, onChange, children, style: s = {} }) {
  return (
    <select id={id} name={name} value={value} onChange={onChange}
      style={{
        width: '100%', background: 'var(--color-glass-light)', border: '1px solid var(--color-glass-borderLight)',
        borderRadius: '8px', padding: '10px 36px 10px 14px', color: 'var(--color-light-text)',
        fontFamily: 'IBM Plex Sans, sans-serif', fontSize: '13px',
        outline: 'none', cursor: 'pointer', boxSizing: 'border-box',
        appearance: 'none', WebkitAppearance: 'none',
        transition: 'border-color 0.15s', ...s,
        backdropFilter: 'blur(5px)', // Glassmorphism effect
      }}
      onFocus={e => { e.target.style.borderColor = 'var(--color-amber-500)'; }}
      onBlur={e => { e.target.style.borderColor = 'var(--color-glass-borderLight)'; }}
    >
      {children}
    </select>
  );
}

export function Label({ htmlFor, children, required }) {
  return (
    <label htmlFor={htmlFor} style={{
      display: 'block', fontSize: '10px', fontFamily: 'IBM Plex Mono, monospace',
      color: 'var(--color-light-textMuted)', letterSpacing: '0.1em', marginBottom: '8px',
      textTransform: 'uppercase',
    }}>
      {children}{required && <span style={{ color: 'var(--color-amber-500)', marginLeft: '4px' }}>*</span>}
    </label>
  );
}

export function Field({ label, htmlFor, hint, required, error, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {label && <Label htmlFor={htmlFor} required={required}>{label}</Label>}
      {children}
      {hint && !error && <p style={{ marginTop: '6px', fontSize: '11px', color: 'var(--color-ink-300)', fontFamily: 'IBM Plex Mono, monospace' }}>{hint}</p>}
      {error && <p style={{ marginTop: '6px', fontSize: '11px', color: 'var(--color-signal-down)', fontFamily: 'IBM Plex Mono, monospace' }}>{error}</p>}
    </div>
  );
}

export function Card({ children, style: s = {}, hover = false, padding = '24px' }) {
  return (
    <div style={{
        background: 'var(--color-glass-light)',
        border: '1px solid var(--color-glass-borderLight)',
        borderRadius: '10px',
        padding,
        transition: 'border-color 0.2s, box-shadow 0.2s',
        backdropFilter: 'blur(10px)', // Glassmorphism effect
        ...s
      }}
      onMouseEnter={hover ? e => { e.currentTarget.style.borderColor = 'var(--color-amber-500)'; e.currentTarget.style.boxShadow = 'var(--box-shadow-glass)'; } : undefined}
      onMouseLeave={hover ? e => { e.currentTarget.style.borderColor = 'var(--color-glass-borderLight)'; e.currentTarget.style.boxShadow = 'none'; } : undefined}
    >
      {children}
    </div>
  );
}

export function Badge({ children, variant = 'neutral' }) {
  const vs = {
    neutral: { background: 'rgba(255,255,255,0.05)', color: 'var(--color-light-textMuted)', border: '1px solid var(--color-glass-borderLight)' },
    success: { background: 'rgba(16,185,129,0.1)', color: 'var(--color-signal-up)', border: '1px solid rgba(16,185,129,0.2)' },
    danger:  { background: 'rgba(239,68,68,0.1)',  color: 'var(--color-signal-down)', border: '1px solid rgba(239,68,68,0.2)' },
    amber:   { background: 'rgba(245,158,11,0.1)', color: 'var(--color-amber-500)', border: '1px solid rgba(245,158,11,0.2)' },
    purple:  { background: 'rgba(129,140,248,0.1)', color: 'var(--color-ink-200)', border: '1px solid rgba(129,140,248,0.2)' },
    blue:    { background: 'rgba(56,189,248,0.1)', color: 'var(--color-ink-200)', border: '1px solid rgba(56,189,248,0.2)' },
  };
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', padding: '3px 10px', borderRadius: '20px', fontSize: '10px', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.06em', whiteSpace: 'nowrap', backdropFilter: 'blur(5px)', ...vs[variant] }}>
      {children}
    </span>
  );
}

export function PageHeader({ title, subtitle, action, tag }) {
  return (
    <div style={{ marginBottom: '32px' }}>
      {tag && <div style={{ fontSize: '10px', color: 'var(--color-amber-500)', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.12em', marginBottom: '10px' }}>{tag}</div>}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
        <div>
          <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '28px', color: 'var(--color-light-text)', letterSpacing: '-0.03em', margin: 0 }}>{title}</h1>
          {subtitle && <p style={{ marginTop: '6px', fontSize: '14px', color: 'var(--color-light-textMuted)', lineHeight: 1.6, margin: '6px 0 0' }}>{subtitle}</p>}
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
        <h2 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '18px', color: 'var(--color-light-text)', letterSpacing: '-0.02em', margin: 0 }}>{title}</h2>
        {sub && <span style={{ fontSize: '11px', color: 'var(--color-ink-300)', fontFamily: 'IBM Plex Mono, monospace' }}>{sub}</span>}
      </div>
      {action}
    </div>
  );
}

export function Alert({ type = 'info', children }) {
  const s = {
    error:   { bg: 'rgba(239,68,68,0.08)',   border: '1px solid rgba(239,68,68,0.25)',   color: 'var(--color-signal-down)' },
    warning: { bg: 'rgba(245,158,11,0.08)',  border: '1px solid rgba(245,158,11,0.25)',  color: 'var(--color-amber-500)' },
    success: { bg: 'rgba(16,185,129,0.08)',  border: '1px solid rgba(16,185,129,0.25)',  color: 'var(--color-signal-up)' },
    info:    { bg: 'rgba(129,140,248,0.08)', border: '1px solid rgba(129,140,248,0.25)', color: 'var(--color-ink-200)' }, // Using ink-200 for info for a lighter feel
  };
  return (
    <div style={{ background: s[type].bg, border: s[type].border, borderRadius: '8px', padding: '12px 16px', fontSize: '13px', color: s[type].color, backdropFilter: 'blur(5px)' }}>
      {children}
    </div>
  );
}

export function Divider({ label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
      <div style={{ flex: 1, height: '1px', background: 'var(--color-light-border)' }} />
      {label && <span style={{ fontSize: '11px', color: 'var(--color-ink-400)', fontFamily: 'IBM Plex Mono, monospace', whiteSpace: 'nowrap' }}>{label}</span>}
      <div style={{ flex: 1, height: '1px', background: 'var(--color-light-border)' }} />
    </div>
  );
}

export function EmptyState({ icon, title, body, action }) {
  return (
    <div style={{ textAlign: 'center', padding: '64px 32px', background: 'var(--color-glass-light)', border: '1px solid var(--color-glass-borderLight)', borderRadius: '10px', backdropFilter: 'blur(10px)' }}>
      {icon && <div style={{ marginBottom: '16px', color: 'var(--color-ink-400)' }}>{icon}</div>}
      <div style={{ fontSize: '10px', color: 'var(--color-ink-400)', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.12em', marginBottom: '12px' }}>EMPTY STATE</div>
      <h3 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '22px', color: 'var(--color-light-text)', letterSpacing: '-0.02em', marginBottom: '8px' }}>{title}</h3>
      {body && <p style={{ fontSize: '14px', color: 'var(--color-light-textMuted)', lineHeight: 1.65, maxWidth: '380px', margin: '0 auto 24px' }}>{body}</p>}
      {action}
    </div>
  );
}

export function StatCard({ label, value, color = 'var(--color-amber-500)', sub, mono = true }) {
  return (
    <div style={{ background: 'var(--color-glass-light)', border: '1px solid var(--color-glass-borderLight)', borderRadius: '10px', padding: '24px 28px', backdropFilter: 'blur(10px)' }}>
      <div style={{ fontSize: '10px', color: 'var(--color-ink-300)', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '12px' }}>{label.toUpperCase()}</div>
      <div style={{ fontSize: '40px', fontFamily: mono ? 'IBM Plex Mono, monospace' : 'Syne, sans-serif', fontWeight: 700, color, letterSpacing: '-0.03em', lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--color-ink-300)', fontFamily: 'IBM Plex Mono, monospace' }}>{sub}</div>}
    </div>
  );
}
