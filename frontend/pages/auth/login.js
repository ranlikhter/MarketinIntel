import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuth } from '../../context/AuthContext';
import GoogleSignInButton from '../../components/GoogleSignInButton';
import MicrosoftSignInButton from '../../components/MicrosoftSignInButton';

const inputCls = 'glass-input appearance-none block w-full px-4 py-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/50 transition text-sm';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { login, loginWithGoogle, googleClientId, microsoftClientId, getMicrosoftLoginUrl } = useAuth();

  useEffect(() => {
    if (typeof router.query.error === 'string' && router.query.error) {
      setError(router.query.error);
    }
  }, [router.query.error]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = await login(email, password);
      if (result.success) {
        const redirect = router.query.redirect;
        const safeRedirect = (typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//'))
          ? redirect
          : '/dashboard';
        router.push(safeRedirect);
      } else {
        setError(result.error || 'Login failed');
      }
    } catch {
      setError('An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async (credential) => {
    setError('');
    setLoading(true);
    try {
      const result = await loginWithGoogle(credential);
      if (result.success) {
        const redirect = router.query.redirect;
        const safeRedirect = (typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//'))
          ? redirect
          : '/dashboard';
        router.push(safeRedirect);
      } else {
        setError(result.error || 'Google sign-in failed');
      }
    } catch {
      setError('Google sign-in failed');
    } finally {
      setLoading(false);
    }
  };

  const handleMicrosoftLogin = () => {
    const redirect = router.query.redirect;
    const safeRedirect = (typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//'))
      ? redirect
      : '/dashboard';
    window.location.href = getMicrosoftLoginUrl(safeRedirect);
  };

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8" style={{ background: 'var(--bg-base)' }}>
      <div className="max-w-md w-full space-y-6">
        {/* Logo */}
        <div className="text-center">
          <div className="mx-auto h-14 w-14 rounded-2xl flex items-center justify-center shadow-sm gradient-brand">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h1 className="mt-5 text-2xl font-bold text-white">Welcome back</h1>
          <p className="mt-1.5 text-sm" style={{ color: 'var(--text-muted)' }}>Sign in to your MarketIntel account</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl p-8" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <form className="space-y-5" onSubmit={handleSubmit}>
            {error && (
              <div className="flex items-start gap-3 rounded-xl p-3.5" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}>
                <svg className="w-4 h-4 text-red-400 mt-0.5 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-white/70 mb-1.5">Email address</label>
              <input id="email" name="email" type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputCls} placeholder="you@example.com" />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-white/70 mb-1.5">Password</label>
              <input id="password" name="password" type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} className={inputCls} placeholder="••••••••" />
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm cursor-pointer select-none" style={{ color: 'var(--text-muted)' }}>
                <input type="checkbox" className="h-4 w-4 border-white/20 rounded focus:ring-amber-500" style={{ accentColor: '#f59e0b' }} />
                Remember me
              </label>
              <Link href="/auth/forgot-password" className="text-sm font-medium text-amber-400 hover:text-amber-300">Forgot password?</Link>
            </div>

            <button
              type="submit" disabled={loading}
              className="w-full flex justify-center items-center gap-2 py-2.5 px-4 gradient-brand text-white text-sm font-medium rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? <span className="w-4 h-4 border-2 border-white/30 border-t-amber-500 rounded-full animate-spin" /> : null}
              {loading ? 'Signing in…' : 'Sign in'}
            </button>

            {(googleClientId || microsoftClientId) && (
              <>
                <div className="flex items-center gap-3">
                  <div className="h-px flex-1" style={{ background: 'var(--border)' }} />
                  <span className="text-xs uppercase tracking-[0.2em]" style={{ color: 'var(--text-muted)' }}>or</span>
                  <div className="h-px flex-1" style={{ background: 'var(--border)' }} />
                </div>
                <div className="space-y-3">
                  {googleClientId && (
                    <div className="flex justify-center">
                      <GoogleSignInButton
                        onCredential={handleGoogleLogin}
                        disabled={loading}
                        text="signin_with"
                      />
                    </div>
                  )}
                  {microsoftClientId && (
                    <MicrosoftSignInButton
                      onClick={handleMicrosoftLogin}
                      disabled={loading}
                      label="Continue with Microsoft"
                    />
                  )}
                </div>
              </>
            )}
          </form>

          <div className="mt-6 pt-5 text-center" style={{ borderTop: '1px solid var(--border)' }}>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>New to MarketIntel?{' '}
              <Link href="/auth/signup" className="font-medium text-amber-400 hover:text-amber-300">Create a free account</Link>
            </p>
          </div>
        </div>

        <p className="text-center text-xs" style={{ color: 'var(--text-muted)' }}>
          By signing in, you agree to our{' '}
          <a href="#" className="text-amber-400 hover:text-amber-300">Terms</a> and{' '}
          <a href="#" className="text-amber-400 hover:text-amber-300">Privacy Policy</a>
        </p>
      </div>
    </div>
  );
}
