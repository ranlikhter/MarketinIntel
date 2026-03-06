import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuth } from '../../context/AuthContext';

const inputCls = 'glass-input appearance-none block w-full px-4 py-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/50 transition text-sm';

const CheckIco = ({ ok }) => (
  <svg className={`w-4 h-4 shrink-0 ${ok ? 'text-amber-400' : 'text-white/20'}`} fill="currentColor" viewBox="0 0 20 20">
    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
  </svg>
);

export default function Signup() {
  const [formData, setFormData] = useState({ fullName: '', email: '', password: '', confirmPassword: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { signup } = useAuth();

  const handleChange = e => setFormData(f => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (formData.password !== formData.confirmPassword) { setError('Passwords do not match'); return; }
    if (formData.password.length < 8) { setError('Password must be at least 8 characters'); return; }
    setLoading(true);
    try {
      const result = await signup(formData.email, formData.password, formData.fullName);
      if (result.success) { router.push('/dashboard'); }
      else { setError(result.error || 'Signup failed'); }
    } catch { setError('An unexpected error occurred'); }
    finally { setLoading(false); }
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
          <h1 className="mt-5 text-2xl font-bold text-white">Start your free trial</h1>
          <p className="mt-1.5 text-sm" style={{ color: 'var(--text-muted)' }}>Get started with MarketIntel today</p>
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
              <label htmlFor="fullName" className="block text-sm font-medium text-white/70 mb-1.5">Full name</label>
              <input id="fullName" name="fullName" type="text" required value={formData.fullName} onChange={handleChange} className={inputCls} placeholder="John Doe" />
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-white/70 mb-1.5">Email address</label>
              <input id="email" name="email" type="email" autoComplete="email" required value={formData.email} onChange={handleChange} className={inputCls} placeholder="you@example.com" />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-white/70 mb-1.5">Password</label>
              <input id="password" name="password" type="password" autoComplete="new-password" required value={formData.password} onChange={handleChange} className={inputCls} placeholder="••••••••" />
              <p className="mt-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>Must be at least 8 characters</p>
            </div>
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-white/70 mb-1.5">Confirm password</label>
              <input id="confirmPassword" name="confirmPassword" type="password" autoComplete="new-password" required value={formData.confirmPassword} onChange={handleChange} className={inputCls} placeholder="••••••••" />
            </div>

            {/* Free plan highlights */}
            <div className="rounded-xl p-4 space-y-2" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
              <p className="text-xs font-semibold text-amber-400 uppercase tracking-wide">Free plan includes</p>
              <ul className="space-y-1.5">
                {['Monitor up to 5 products', '10 AI-powered product matches', '1 price alert', 'Basic analytics & insights'].map(item => (
                  <li key={item} className="flex items-center gap-2 text-sm text-white/70">
                    <CheckIco ok={true} />{item}
                  </li>
                ))}
              </ul>
            </div>

            <button
              type="submit" disabled={loading}
              className="w-full flex justify-center items-center gap-2 py-2.5 px-4 gradient-brand text-white text-sm font-medium rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? <span className="w-4 h-4 border-2 border-white/30 border-t-amber-500 rounded-full animate-spin" /> : null}
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <div className="mt-6 pt-5 text-center" style={{ borderTop: '1px solid var(--border)' }}>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Already have an account?{' '}
              <Link href="/auth/login" className="font-medium text-amber-400 hover:text-amber-300">Sign in</Link>
            </p>
          </div>
        </div>

        <p className="text-center text-xs" style={{ color: 'var(--text-muted)' }}>
          By creating an account, you agree to our{' '}
          <a href="#" className="text-amber-400 hover:text-amber-300">Terms</a> and{' '}
          <a href="#" className="text-amber-400 hover:text-amber-300">Privacy Policy</a>
        </p>
      </div>
    </div>
  );
}
