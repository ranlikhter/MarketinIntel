// MarketIntel Design System — light theme primitives

export function Spinner({ size = 20, color = '#2563EB' }) {
  return (
    <>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
        style={{ animation: 'ui-spin 0.7s linear infinite', flexShrink: 0 }}>
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
    fontFamily: 'inherit', letterSpacing: '0.01em', fontWeight: 600,
    transition: 'opacity 0.15s, box-shadow 0.15s, background 0.15s',
    opacity: disabled || loading ? 0.5 : 1,
    textDecoration: 'none', whiteSpace: 'nowrap',
  };
  const sizes = {
    sm: { padding: '6px 14px',  fontSize: '12px', borderRadius: '8px' },
    md: { padding: '9px 20px',  fontSize: '13px', borderRadius: '10px' },
    lg: { padding: '12px 28px', fontSize: '14px', borderRadius: '10px' },
  };
  const variants = {
    primary:   { background: '#2563EB', color: '#FFFFFF', boxShadow: '0 1px 4px rgba(37,99,235,0.3)' },
    secondary: { background: '#FFFFFF', color: '#374151', border: '1px solid #D1D5DB' },
    danger:    { background: '#FFFFFF', color: '#EF4444', border: '1px solid #FECACA' },
    ghost:     { background: 'transparent', color: '#6B7280' },
    outline:   { background: 'transparent', color: '#2563EB', border: '1px solid #BFDBFE' },
    success:   { background: '#ECFDF5', color: '#10B981', border: '1px solid #A7F3D0' },
  };
  return (
    <button type={type} onClick={onClick} disabled={disabled || loading}
      style={{ ...base, ...sizes[size], ...variants[variant], ...s }}>
      {loading ? <Spinner size={size === 'sm' ? 12 : 15} /> : children}
    </button>
  );
}

export function Input({ id, name, type = 'text', value, onChange, placeholder, required, autoComplete, style: s = {}, monospace }) {
  return (
    <input
      id={id} name={name} type={type} value={value} onChange={onChange}
      placeholder={placeholder} required={required} autoComplete={autoComplete}
      style={{
        width: '100%', background: '#FFFFFF', border: '1px solid #D1D5DB',
        borderRadius: '8px', padding: '9px 14px', color: '#111827',
        fontFamily: monospace ? 'ui-monospace, monospace' : 'inherit',
        fontSize: '14px', outline: 'none', boxSizing: 'border-box',
        transition: 'border-color 0.15s, box-shadow 0.15s', ...s,
      }}
      onFocus={e => { e.target.style.borderColor = '#2563EB'; e.target.style.boxShadow = '0 0 0 3px rgba(37,99,235,0.1)'; }}
      onBlur={e => { e.target.style.borderColor = '#D1D5DB'; e.target.style.boxShadow = 'none'; }}
    />
  );
}

export function Textarea({ id, name, value, onChange, placeholder, rows = 3, style: s = {} }) {
  return (
    <textarea
      id={id} name={name} value={value} onChange={onChange}
      placeholder={placeholder} rows={rows}
      style={{
        width: '100%', background: '#FFFFFF', border: '1px solid #D1D5DB',
        borderRadius: '8px', padding: '9px 14px', color: '#111827',
        fontFamily: 'inherit', fontSize: '14px',
        outline: 'none', resize: 'vertical', boxSizing: 'border-box',
        transition: 'border-color 0.15s, box-shadow 0.15s', ...s,
      }}
      onFocus={e => { e.target.style.borderColor = '#2563EB'; e.target.style.boxShadow = '0 0 0 3px rgba(37,99,235,0.1)'; }}
      onBlur={e => { e.target.style.borderColor = '#D1D5DB'; e.target.style.boxShadow = 'none'; }}
    />
  );
}

export function Select({ id, name, value, onChange, children, style: s = {} }) {
  return (
    <select
      id={id} name={name} value={value} onChange={onChange}
      style={{
        width: '100%', background: '#FFFFFF', border: '1px solid #D1D5DB',
        borderRadius: '8px', padding: '9px 36px 9px 14px', color: '#111827',
        fontFamily: 'inherit', fontSize: '14px',
        outline: 'none', cursor: 'pointer', boxSizing: 'border-box',
        appearance: 'none', WebkitAppearance: 'none',
        transition: 'border-color 0.15s', ...s,
      }}
      onFocus={e => { e.target.style.borderColor = '#2563EB'; }}
      onBlur={e => { e.target.style.borderColor = '#D1D5DB'; }}
    >
      {children}
    </select>
  );
}

export function Label({ htmlFor, children, required }) {
  return (
    <label htmlFor={htmlFor} style={{
      display: 'block', fontSize: '13px', fontWeight: 500,
      color: '#374151', marginBottom: '6px',
    }}>
      {children}{required && <span style={{ color: '#EF4444', marginLeft: '4px' }}>*</span>}
    </label>
  );
}

export function Field({ label, htmlFor, hint, required, error, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {label && <Label htmlFor={htmlFor} required={required}>{label}</Label>}
      {children}
      {hint && !error && <p style={{ marginTop: '5px', fontSize: '12px', color: '#9CA3AF' }}>{hint}</p>}
      {error && <p style={{ marginTop: '5px', fontSize: '12px', color: '#EF4444' }}>{error}</p>}
    </div>
  );
}

export function Card({ children, style: s = {}, hover = false, padding = '24px' }) {
  return (
    <div
      style={{ background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '12px', padding, transition: 'border-color 0.2s, box-shadow 0.2s', ...s }}
      onMouseEnter={hover ? e => { e.currentTarget.style.borderColor = '#BFDBFE'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(37,99,235,0.08)'; } : undefined}
      onMouseLeave={hover ? e => { e.currentTarget.style.borderColor = '#E5E7EB'; e.currentTarget.style.boxShadow = 'none'; } : undefined}
    >
      {children}
    </div>
  );
}

export function Badge({ children, variant = 'neutral' }) {
  const vs = {
    neutral: { background: '#F3F4F6',  color: '#6B7280', border: '1px solid #E5E7EB' },
    success: { background: '#ECFDF5',  color: '#10B981', border: '1px solid #A7F3D0' },
    danger:  { background: '#FEF2F2',  color: '#EF4444', border: '1px solid #FECACA' },
    amber:   { background: '#FFFBEB',  color: '#D97706', border: '1px solid #FDE68A' },
    purple:  { background: '#F5F3FF',  color: '#7C3AED', border: '1px solid #DDD6FE' },
    blue:    { background: '#EFF6FF',  color: '#2563EB', border: '1px solid #BFDBFE' },
  };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', padding: '2px 10px',
      borderRadius: '20px', fontSize: '11px', fontWeight: 500,
      whiteSpace: 'nowrap', ...vs[variant],
    }}>
      {children}
    </span>
  );
}

export function PageHeader({ title, subtitle, action, tag }) {
  return (
    <div style={{ marginBottom: '28px' }}>
      {tag && <div style={{ fontSize: '11px', color: '#2563EB', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '8px' }}>{tag}</div>}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
        <div>
          <h1 style={{ fontWeight: 700, fontSize: '24px', color: '#111827', letterSpacing: '-0.02em', margin: 0 }}>{title}</h1>
          {subtitle && <p style={{ marginTop: '4px', fontSize: '14px', color: '#6B7280', lineHeight: 1.6 }}>{subtitle}</p>}
        </div>
        {action && <div style={{ flexShrink: 0 }}>{action}</div>}
      </div>
    </div>
  );
}

export function SectionHeader({ title, sub, action }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}>
        <h2 style={{ fontWeight: 600, fontSize: '16px', color: '#111827', margin: 0 }}>{title}</h2>
        {sub && <span style={{ fontSize: '12px', color: '#9CA3AF' }}>{sub}</span>}
      </div>
      {action}
    </div>
  );
}

export function Alert({ type = 'info', children }) {
  const s = {
    error:   { bg: '#FEF2F2', border: '1px solid #FECACA', color: '#B91C1C' },
    warning: { bg: '#FFFBEB', border: '1px solid #FDE68A', color: '#92400E' },
    success: { bg: '#ECFDF5', border: '1px solid #A7F3D0', color: '#065F46' },
    info:    { bg: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1E40AF' },
  };
  return (
    <div style={{ background: s[type].bg, border: s[type].border, borderRadius: '8px', padding: '12px 16px', fontSize: '14px', color: s[type].color }}>
      {children}
    </div>
  );
}

export function Divider({ label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
      <div style={{ flex: 1, height: '1px', background: '#E5E7EB' }} />
      {label && <span style={{ fontSize: '12px', color: '#9CA3AF', whiteSpace: 'nowrap' }}>{label}</span>}
      <div style={{ flex: 1, height: '1px', background: '#E5E7EB' }} />
    </div>
  );
}

export function EmptyState({ icon, title, body, action }) {
  return (
    <div style={{ textAlign: 'center', padding: '56px 32px', background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '12px' }}>
      {icon && <div style={{ marginBottom: '16px', color: '#D1D5DB' }}>{icon}</div>}
      <h3 style={{ fontWeight: 600, fontSize: '18px', color: '#111827', marginBottom: '8px' }}>{title}</h3>
      {body && <p style={{ fontSize: '14px', color: '#6B7280', lineHeight: 1.65, maxWidth: '380px', margin: '0 auto 24px' }}>{body}</p>}
      {action}
    </div>
  );
}

export function StatCard({ label, value, color = '#2563EB', sub }) {
  return (
    <div style={{ background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '12px', padding: '20px 24px' }}>
      <div style={{ fontSize: '12px', fontWeight: 500, color: '#6B7280', marginBottom: '10px' }}>{label}</div>
      <div style={{ fontSize: '36px', fontWeight: 700, color, letterSpacing: '-0.03em', lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ marginTop: '6px', fontSize: '12px', color: '#9CA3AF' }}>{sub}</div>}
    </div>
  );
}
