
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
