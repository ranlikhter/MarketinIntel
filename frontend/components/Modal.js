
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
