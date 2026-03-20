import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../../context/AuthContext';

export default function SsoCompletePage() {
  const router = useRouter();
  const { completeSSOLogin } = useAuth();
  const [message, setMessage] = useState('Completing sign-in...');

  useEffect(() => {
    const finishLogin = async () => {
      if (typeof window === 'undefined') return;

      const hash = window.location.hash.startsWith('#')
        ? window.location.hash.slice(1)
        : window.location.hash;
      const params = new URLSearchParams(hash);
      const error = params.get('error');
      const redirect = params.get('redirect') || '/dashboard';
      const safeRedirect = redirect.startsWith('/') && !redirect.startsWith('//')
        ? redirect
        : '/dashboard';

      if (error) {
        router.replace(`/auth/login?error=${encodeURIComponent(error)}`);
        return;
      }

      const result = await completeSSOLogin();
      if (!result.success) {
        setMessage(result.error || 'SSO sign-in failed.');
        return;
      }

      router.replace(safeRedirect);
    };

    finishLogin();
  }, [completeSSOLogin, router]);

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'var(--bg-base)' }}>
      <div className="rounded-2xl p-8 w-full max-w-md text-center" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
        <div className="mx-auto w-12 h-12 rounded-full flex items-center justify-center mb-4" style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}>
          <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
        <h1 className="text-lg font-semibold text-white">Signing you in</h1>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>{message}</p>
      </div>
    </div>
  );
}
