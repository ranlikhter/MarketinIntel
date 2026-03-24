import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

/**
 * /integrations/shopify-callback
 *
 * Landing page after the Shopify OAuth flow.
 * The backend redirects here with:
 *   ?success=true&store=mystore.myshopify.com
 *   ?success=false&error=<reason>
 */
export default function ShopifyCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState('loading'); // 'loading' | 'success' | 'error'
  const [store, setStore] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (!router.isReady) return;

    const { success, store: s, error } = router.query;

    if (success === 'true') {
      setStore(s || '');
      setStatus('success');
    } else {
      const messages = {
        invalid_hmac:          'Security check failed. Please try again.',
        invalid_state:         'Session expired. Please start the connection again.',
        invalid_shop:          'Invalid shop URL. Please check and try again.',
        token_exchange_failed: 'Could not exchange the authorization code. Please try again.',
        no_token:              'Shopify did not return an access token. Please try again.',
      };
      setErrorMsg(messages[error] || 'Something went wrong. Please try again.');
      setStatus('error');
    }
  }, [router.isReady, router.query]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'var(--bg-base, #0f1117)' }}>
      <div className="w-full max-w-md rounded-2xl p-8 text-center shadow-xl"
        style={{ background: 'var(--bg-surface, #1a1d27)', border: '1px solid var(--border, rgba(255,255,255,0.08))' }}>

        {status === 'loading' && (
          <>
            <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5"
              style={{ background: 'rgba(245,158,11,0.12)' }}>
              <svg className="animate-spin w-8 h-8 text-amber-400" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
            </div>
            <h1 className="text-xl font-bold text-white mb-2">Connecting…</h1>
            <p className="text-sm" style={{ color: 'var(--text-muted, rgba(255,255,255,0.5))' }}>
              Finalising your Shopify connection.
            </p>
          </>
        )}

        {status === 'success' && (
          <>
            {/* Success icon */}
            <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5"
              style={{ background: 'rgba(16,185,129,0.15)' }}>
              <svg className="w-9 h-9 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>

            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium mb-4"
              style={{ background: 'rgba(16,185,129,0.12)', color: '#10b981', border: '1px solid rgba(16,185,129,0.25)' }}>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
              Connected
            </div>

            <h1 className="text-xl font-bold text-white mb-2">Shopify Connected!</h1>
            <p className="text-sm mb-1" style={{ color: 'var(--text-muted, rgba(255,255,255,0.5))' }}>
              Successfully connected to
            </p>
            {store && (
              <p className="text-sm font-semibold text-white mb-6">{store}</p>
            )}
            <p className="text-xs mb-8" style={{ color: 'var(--text-muted, rgba(255,255,255,0.4))' }}>
              Your products will sync automatically every 4 hours. You can also trigger a manual sync from the Integrations page.
            </p>

            <div className="flex flex-col gap-3">
              <Link href="/integrations"
                className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-white text-sm font-semibold rounded-xl transition-opacity hover:opacity-90"
                style={{ background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' }}>
                View Integrations
              </Link>
              <Link href="/products"
                className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-medium rounded-xl transition-colors hover:bg-white/10"
                style={{ color: 'rgba(255,255,255,0.6)', border: '1px solid rgba(255,255,255,0.1)' }}>
                Go to Products
              </Link>
            </div>
          </>
        )}

        {status === 'error' && (
          <>
            {/* Error icon */}
            <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5"
              style={{ background: 'rgba(239,68,68,0.12)' }}>
              <svg className="w-9 h-9 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>

            <h1 className="text-xl font-bold text-white mb-2">Connection Failed</h1>
            <p className="text-sm mb-8" style={{ color: 'var(--text-muted, rgba(255,255,255,0.5))' }}>
              {errorMsg}
            </p>

            <div className="flex flex-col gap-3">
              <Link href="/integrations"
                className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-white text-sm font-semibold rounded-xl transition-opacity hover:opacity-90"
                style={{ background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' }}>
                Try Again
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
