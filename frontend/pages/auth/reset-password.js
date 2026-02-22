import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuth } from '../../context/AuthContext';

const inputCls = 'appearance-none block w-full px-4 py-3 border border-gray-200 placeholder-gray-400 text-gray-900 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition text-sm';

export default function ResetPassword() {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState('');
  const router = useRouter();
  const { resetPassword } = useAuth();

  useEffect(() => {
    if (router.query.token) setToken(router.query.token);
  }, [router.query]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) { setError('Passwords do not match'); return; }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return; }
    if (!token) { setError('Invalid or missing reset token'); return; }
    setLoading(true);
    try {
      const result = await resetPassword(token, password);
      if (result.success) {
        setSuccess(true);
        setTimeout(() => router.push('/auth/login'), 3000);
      } else { setError(result.error || 'Failed to reset password'); }
    } catch { setError('An unexpected error occurred'); }
    finally { setLoading(false); }
  };

  const meetsLength = password.length >= 8;
  const meetsMatch = password && confirmPassword && password === confirmPassword;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-6">
        {/* Logo */}
        <div className="text-center">
          <div className="mx-auto h-14 w-14 bg-blue-600 rounded-2xl flex items-center justify-center shadow-sm">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <h1 className="mt-5 text-2xl font-bold text-gray-900">Create new password</h1>
          <p className="mt-1.5 text-sm text-gray-500">Enter your new password below</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
          {success ? (
            <div className="text-center space-y-4 py-2">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-2xl bg-emerald-50">
                <svg className="h-6 w-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <h2 className="text-base font-semibold text-gray-900">Password reset successful!</h2>
                <p className="mt-2 text-sm text-gray-500">Your password has been updated. Redirecting to login…</p>
              </div>
              <Link href="/auth/login" className="inline-block text-sm font-medium text-blue-600 hover:text-blue-700">Go to sign in →</Link>
            </div>
          ) : (
            <form className="space-y-5" onSubmit={handleSubmit}>
              {error && (
                <div className="flex items-start gap-3 bg-red-50 border border-red-100 rounded-xl p-3.5">
                  <svg className="w-4 h-4 text-red-500 mt-0.5 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1.5">New password</label>
                <input id="password" name="password" type="password" autoComplete="new-password" required value={password} onChange={e => setPassword(e.target.value)} className={inputCls} placeholder="••••••••" />
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1.5">Confirm new password</label>
                <input id="confirmPassword" name="confirmPassword" type="password" autoComplete="new-password" required value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} className={inputCls} placeholder="••••••••" />
              </div>

              {/* Live requirements */}
              <div className="bg-gray-50 rounded-xl p-3.5 space-y-1.5">
                <ReqRow ok={meetsLength} label="At least 8 characters" />
                <ReqRow ok={meetsMatch}  label="Passwords match" />
              </div>

              <button
                type="submit" disabled={loading}
                className="w-full flex justify-center items-center gap-2 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : null}
                {loading ? 'Resetting…' : 'Reset password'}
              </button>

              <div className="text-center">
                <Link href="/auth/login" className="text-sm font-medium text-blue-600 hover:text-blue-700">← Back to sign in</Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

function ReqRow({ ok, label }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <svg className={`w-4 h-4 shrink-0 ${ok ? 'text-emerald-500' : 'text-gray-300'}`} fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
      </svg>
      <span className={ok ? 'text-gray-700' : 'text-gray-400'}>{label}</span>
    </div>
  );
}
