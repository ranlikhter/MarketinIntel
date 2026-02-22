import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/Toast';

const API_BASE = 'http://localhost:8000';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function authHeader() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...authHeader(), ...(options.headers || {}) },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

// ─── Shared UI primitives ─────────────────────────────────────────────────────

function Section({ title, description, children }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-100">
        <h3 className="text-base font-semibold text-gray-900">{title}</h3>
        {description && <p className="mt-0.5 text-sm text-gray-500">{description}</p>}
      </div>
      <div className="px-6 py-5">{children}</div>
    </div>
  );
}

function Field({ label, hint, children }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-8 py-3 first:pt-0 last:pb-0">
      <div className="sm:w-48 shrink-0">
        <label className="block text-sm font-medium text-gray-700">{label}</label>
        {hint && <p className="text-xs text-gray-400 mt-0.5">{hint}</p>}
      </div>
      <div className="flex-1">{children}</div>
    </div>
  );
}

function Input({ className = '', ...props }) {
  return (
    <input
      className={`block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-400
        focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none transition-shadow ${className}`}
      {...props}
    />
  );
}

function SaveButton({ loading, children = 'Save Changes' }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium
        hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none
        focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
    >
      {loading && (
        <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children}
    </button>
  );
}

function UsageMeter({ label, used, limit, color = 'blue' }) {
  const pct = limit >= 9999 ? 0 : Math.min(100, Math.round((used / limit) * 100));
  const colorMap = {
    blue:   { bar: 'bg-blue-500',   bg: 'bg-blue-50',   text: 'text-blue-700'   },
    green:  { bar: 'bg-green-500',  bg: 'bg-green-50',  text: 'text-green-700'  },
    purple: { bar: 'bg-purple-500', bg: 'bg-purple-50', text: 'text-purple-700' },
  };
  const c = colorMap[color] ?? colorMap.blue;
  const barColor = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : c.bar;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-gray-500">
          {limit >= 9999 ? `${used} / Unlimited` : `${used} / ${limit}`}
        </span>
      </div>
      {limit < 9999 && (
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
      {limit < 9999 && pct >= 90 && (
        <p className="text-xs text-red-600 font-medium">
          {pct === 100 ? 'Limit reached — upgrade to add more' : `${100 - pct}% remaining`}
        </p>
      )}
    </div>
  );
}

// ─── TIER CONFIG ──────────────────────────────────────────────────────────────

const TIERS = {
  free:       { label: 'Free',       gradient: 'from-gray-500 to-gray-600',     badge: 'bg-gray-100 text-gray-700'    },
  pro:        { label: 'Pro',        gradient: 'from-blue-500 to-blue-700',     badge: 'bg-blue-100 text-blue-700'    },
  business:   { label: 'Business',   gradient: 'from-purple-500 to-purple-700', badge: 'bg-purple-100 text-purple-700'},
  enterprise: { label: 'Enterprise', gradient: 'from-amber-500 to-amber-600',   badge: 'bg-amber-100 text-amber-700'  },
};

// ─── TAB COMPONENTS ───────────────────────────────────────────────────────────

function ProfileTab({ user, updateUser }) {
  const { addToast } = useToast();
  const [name, setName] = useState(user?.full_name ?? '');
  const [savingName, setSavingName] = useState(false);

  const [pw, setPw] = useState({ current: '', next: '', confirm: '' });
  const [showPw, setShowPw] = useState({ current: false, next: false, confirm: false });
  const [savingPw, setSavingPw] = useState(false);
  const [pwError, setPwError] = useState('');

  const handleSaveName = async (e) => {
    e.preventDefault();
    setSavingName(true);
    try {
      const updated = await apiFetch('/api/auth/me', {
        method: 'PUT',
        body: JSON.stringify({ full_name: name }),
      });
      updateUser({ full_name: updated.full_name });
      addToast('Profile updated', 'success');
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setSavingName(false);
    }
  };

  const handleChangePw = async (e) => {
    e.preventDefault();
    setPwError('');
    if (pw.next.length < 8) { setPwError('New password must be at least 8 characters'); return; }
    if (pw.next !== pw.confirm) { setPwError('Passwords do not match'); return; }
    setSavingPw(true);
    try {
      await apiFetch('/api/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({ current_password: pw.current, new_password: pw.next }),
      });
      setPw({ current: '', next: '', confirm: '' });
      addToast('Password changed successfully', 'success');
    } catch (err) {
      setPwError(err.message);
    } finally {
      setSavingPw(false);
    }
  };

  const eyeBtn = (key) => (
    <button
      type="button"
      onClick={() => setShowPw(p => ({ ...p, [key]: !p[key] }))}
      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
      tabIndex={-1}
    >
      {showPw[key] ? (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
        </svg>
      ) : (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
        </svg>
      )}
    </button>
  );

  const memberSince = user?.created_at
    ? new Date(user.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
    : '—';

  return (
    <div className="space-y-6">
      {/* Profile info */}
      <Section title="Profile Information" description="Update your display name visible across the platform.">
        {/* Avatar */}
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 rounded-full bg-primary-600 flex items-center justify-center text-white text-2xl font-bold select-none ring-4 ring-primary-100">
            {(user?.full_name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)) ||
             user?.email?.[0]?.toUpperCase() || '?'}
          </div>
          <div>
            <p className="font-semibold text-gray-900">{user?.full_name || 'No name set'}</p>
            <p className="text-sm text-gray-500">{user?.email}</p>
            <div className="flex items-center gap-1.5 mt-1">
              {user?.is_verified ? (
                <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 px-2 py-0.5 rounded-full font-medium">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Verified
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full font-medium">
                  Email not verified
                </span>
              )}
              <span className="text-xs text-gray-400">Member since {memberSince}</span>
            </div>
          </div>
        </div>

        <form onSubmit={handleSaveName} className="divide-y divide-gray-100">
          <Field label="Full Name" hint="Shown in your account menu">
            <Input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Jane Smith"
            />
          </Field>
          <Field label="Email Address" hint="Cannot be changed">
            <Input value={user?.email ?? ''} readOnly disabled className="bg-gray-50 text-gray-500 cursor-not-allowed" />
          </Field>
          <div className="pt-4">
            <SaveButton loading={savingName} />
          </div>
        </form>
      </Section>

      {/* Change password */}
      <Section title="Change Password" description="Use a strong, unique password.">
        <form onSubmit={handleChangePw} className="divide-y divide-gray-100">
          <Field label="Current Password">
            <div className="relative">
              <Input
                type={showPw.current ? 'text' : 'password'}
                value={pw.current}
                onChange={e => setPw(p => ({ ...p, current: e.target.value }))}
                placeholder="Enter current password"
                required
              />
              {eyeBtn('current')}
            </div>
          </Field>
          <Field label="New Password" hint="At least 8 characters">
            <div className="relative">
              <Input
                type={showPw.next ? 'text' : 'password'}
                value={pw.next}
                onChange={e => setPw(p => ({ ...p, next: e.target.value }))}
                placeholder="Enter new password"
                required
              />
              {eyeBtn('next')}
            </div>
            {pw.next.length > 0 && (
              <div className="mt-2 flex gap-1">
                {[8, 12, 16].map((len, i) => (
                  <div key={i} className={`h-1 flex-1 rounded-full ${pw.next.length >= len ? 'bg-green-500' : 'bg-gray-200'}`} />
                ))}
                <span className="text-xs text-gray-400 ml-2">
                  {pw.next.length < 8 ? 'Too short' : pw.next.length < 12 ? 'OK' : pw.next.length < 16 ? 'Good' : 'Strong'}
                </span>
              </div>
            )}
          </Field>
          <Field label="Confirm Password">
            <div className="relative">
              <Input
                type={showPw.confirm ? 'text' : 'password'}
                value={pw.confirm}
                onChange={e => setPw(p => ({ ...p, confirm: e.target.value }))}
                placeholder="Repeat new password"
                required
              />
              {eyeBtn('confirm')}
            </div>
            {pw.confirm && pw.next && pw.confirm !== pw.next && (
              <p className="text-xs text-red-500 mt-1">Passwords do not match</p>
            )}
            {pw.confirm && pw.next && pw.confirm === pw.next && (
              <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Passwords match
              </p>
            )}
          </Field>
          {pwError && (
            <div className="pt-3">
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{pwError}</p>
            </div>
          )}
          <div className="pt-4">
            <SaveButton loading={savingPw}>Change Password</SaveButton>
          </div>
        </form>
      </Section>
    </div>
  );
}

// ─── BILLING TAB ──────────────────────────────────────────────────────────────

function BillingTab({ user }) {
  const { addToast } = useToast();
  const [subscription, setSubscription] = useState(null);
  const [usage, setUsage] = useState({ products: 0, alerts: 0 });
  const [loadingPortal, setLoadingPortal] = useState(false);
  const [loadingCheckout, setLoadingCheckout] = useState(null);

  const tier = user?.subscription_tier ?? 'free';
  const tierCfg = TIERS[tier] ?? TIERS.free;

  useEffect(() => {
    // Load subscription info
    apiFetch('/api/billing/subscription').then(setSubscription).catch(() => {});
    // Load usage counts
    Promise.all([
      apiFetch('/products/').catch(() => []),
      apiFetch('/api/alerts/').catch(() => []),
    ]).then(([products, alerts]) => {
      setUsage({ products: products.length, alerts: alerts.length });
    });
  }, []);

  const openPortal = async () => {
    setLoadingPortal(true);
    try {
      const { url } = await apiFetch('/api/billing/create-portal-session', {
        method: 'POST',
        body: JSON.stringify({ return_url: window.location.href }),
      });
      window.location.href = url;
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setLoadingPortal(false);
    }
  };

  const UPGRADE_PLANS = [
    {
      key: 'pro',
      name: 'Pro',
      price: '$49',
      priceId: 'price_pro_monthly',
      gradient: 'from-blue-500 to-blue-700',
      badge: 'bg-blue-100 text-blue-700',
      features: ['50 products', '100 competitor matches', '10 alerts', 'Priority scraping', 'Advanced analytics'],
    },
    {
      key: 'business',
      name: 'Business',
      price: '$149',
      priceId: 'price_business_monthly',
      gradient: 'from-purple-500 to-purple-700',
      badge: 'bg-purple-100 text-purple-700',
      features: ['200 products', '500 competitor matches', '50 alerts', 'Team workspace', 'API access', 'White-label reports'],
    },
    {
      key: 'enterprise',
      name: 'Enterprise',
      price: '$499',
      priceId: 'price_enterprise_monthly',
      gradient: 'from-amber-500 to-amber-600',
      badge: 'bg-amber-100 text-amber-700',
      features: ['Unlimited products', 'Unlimited matches', 'Unlimited alerts', 'Dedicated support', 'Custom integrations'],
    },
  ];

  const startCheckout = async (priceId, planKey) => {
    setLoadingCheckout(planKey);
    try {
      const { url } = await apiFetch('/api/billing/create-checkout-session', {
        method: 'POST',
        body: JSON.stringify({
          price_id: priceId,
          success_url: `${window.location.origin}/settings?tab=billing&success=true`,
          cancel_url: `${window.location.origin}/settings?tab=billing`,
        }),
      });
      window.location.href = url;
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setLoadingCheckout(null);
    }
  };

  const periodEnd = subscription?.current_period_end
    ? new Date(subscription.current_period_end).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
    : null;

  return (
    <div className="space-y-6">
      {/* Current plan card */}
      <div className={`bg-gradient-to-br ${tierCfg.gradient} rounded-xl p-6 text-white shadow-lg`}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-white/70 text-sm font-medium uppercase tracking-wider">Current Plan</p>
            <h2 className="text-3xl font-bold mt-1">{tierCfg.label}</h2>
            {subscription?.status && (
              <span className={`inline-flex items-center mt-2 px-2.5 py-0.5 rounded-full text-xs font-medium bg-white/20 text-white`}>
                {subscription.status.charAt(0).toUpperCase() + subscription.status.slice(1)}
              </span>
            )}
          </div>
          <svg className="w-12 h-12 text-white/30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>

        {periodEnd && (
          <p className="text-white/70 text-sm mt-4">
            {subscription?.cancel_at_period_end ? 'Cancels on' : 'Renews on'} {periodEnd}
          </p>
        )}

        {subscription?.cancel_at_period_end && (
          <div className="mt-3 bg-white/10 rounded-lg px-4 py-3 text-sm">
            Your plan will be downgraded to Free on {periodEnd}. Reactivate anytime before then.
          </div>
        )}

        <div className="mt-4 flex gap-3">
          {tier !== 'free' && subscription?.stripe_customer_id && (
            <button
              onClick={openPortal}
              disabled={loadingPortal}
              className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50"
            >
              {loadingPortal ? 'Loading…' : 'Manage Billing'}
            </button>
          )}
          {tier === 'free' && (
            <Link
              href="/pricing"
              className="px-4 py-2 bg-white text-blue-700 hover:bg-white/90 rounded-lg text-sm font-medium transition-colors"
            >
              Upgrade Plan
            </Link>
          )}
        </div>
      </div>

      {/* Usage meters */}
      <Section title="Plan Usage" description="How much of your plan limits you're using this month.">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <UsageMeter label="Products" used={usage.products} limit={user?.products_limit ?? 5} color="blue" />
          <UsageMeter label="Competitor Matches" used={0} limit={user?.matches_limit ?? 10} color="green" />
          <UsageMeter label="Alert Rules" used={usage.alerts} limit={user?.alerts_limit ?? 1} color="purple" />
        </div>
      </Section>

      {/* Upgrade options (only for free/pro) */}
      {(tier === 'free' || tier === 'pro') && (
        <Section title="Available Upgrades" description="Scale up as your business grows.">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {UPGRADE_PLANS.filter(p =>
              (tier === 'free') ||
              (tier === 'pro' && p.key !== 'pro')
            ).map(plan => (
              <div key={plan.key} className="border border-gray-200 rounded-xl overflow-hidden">
                <div className={`bg-gradient-to-br ${plan.gradient} px-4 py-4 text-white`}>
                  <p className="font-bold text-lg">{plan.name}</p>
                  <p className="text-white/80 text-sm">{plan.price}<span className="text-xs">/mo</span></p>
                </div>
                <div className="px-4 py-4 space-y-2">
                  {plan.features.map(f => (
                    <div key={f} className="flex items-center gap-2 text-sm text-gray-600">
                      <svg className="w-4 h-4 text-green-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      {f}
                    </div>
                  ))}
                  <button
                    onClick={() => startCheckout(plan.priceId, plan.key)}
                    disabled={loadingCheckout === plan.key}
                    className={`w-full mt-3 py-2 rounded-lg text-sm font-medium transition-colors bg-gradient-to-r ${plan.gradient} text-white hover:opacity-90 disabled:opacity-50`}
                  >
                    {loadingCheckout === plan.key ? 'Loading…' : `Upgrade to ${plan.name}`}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

// ─── NOTIFICATIONS TAB ────────────────────────────────────────────────────────

const PREFS_KEY = 'marketintel_notification_prefs';

const DEFAULT_PREFS = {
  defaultEmail: '',
  digestFrequency: 'instant',
  enableEmail: true,
  enableSlack: false,
  slackWebhook: '',
  enableDiscord: false,
  discordWebhook: '',
  quietHours: false,
  quietStart: 22,
  quietEnd: 8,
};

function NotificationsTab({ user }) {
  const { addToast } = useToast();
  const [prefs, setPrefs] = useState(DEFAULT_PREFS);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(PREFS_KEY) || '{}');
      setPrefs(p => ({ ...p, ...stored, defaultEmail: stored.defaultEmail || user?.email || '' }));
    } catch {
      setPrefs(p => ({ ...p, defaultEmail: user?.email || '' }));
    }
  }, [user]);

  const set = (key, val) => setPrefs(p => ({ ...p, [key]: val }));

  const handleSave = (e) => {
    e.preventDefault();
    setSaving(true);
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
    setTimeout(() => {
      setSaving(false);
      addToast('Notification preferences saved', 'success');
    }, 400);
  };

  const Toggle = ({ value, onChange, disabled }) => (
    <button
      type="button"
      role="switch"
      aria-checked={value}
      onClick={() => !disabled && onChange(!value)}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors
        focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
        ${value ? 'bg-primary-600' : 'bg-gray-200'}
        ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
    >
      <span className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-md transform transition-transform ${value ? 'translate-x-5' : 'translate-x-0'}`} />
    </button>
  );

  return (
    <form onSubmit={handleSave} className="space-y-6">
      <Section title="Default Notification Settings" description="These defaults apply when you create new alert rules.">
        <div className="divide-y divide-gray-100">
          <Field label="Notification Email" hint="Where alerts will be sent by default">
            <Input
              type="email"
              value={prefs.defaultEmail}
              onChange={e => set('defaultEmail', e.target.value)}
              placeholder="you@example.com"
            />
          </Field>
          <Field label="Delivery Frequency" hint="How often to bundle alert notifications">
            <div className="flex flex-col sm:flex-row gap-3 mt-1">
              {[
                { value: 'instant', label: 'Instant', desc: 'As they happen' },
                { value: 'daily',   label: 'Daily Digest', desc: '8 AM summary' },
                { value: 'weekly',  label: 'Weekly Digest', desc: 'Monday summary' },
              ].map(opt => (
                <label key={opt.value} className={`flex-1 flex items-center gap-3 rounded-lg border-2 px-4 py-3 cursor-pointer transition-colors
                  ${prefs.digestFrequency === opt.value ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'}`}>
                  <input
                    type="radio"
                    name="digestFrequency"
                    value={opt.value}
                    checked={prefs.digestFrequency === opt.value}
                    onChange={() => set('digestFrequency', opt.value)}
                    className="text-primary-600"
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{opt.label}</p>
                    <p className="text-xs text-gray-500">{opt.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </Field>
        </div>
      </Section>

      <Section title="Notification Channels" description="Enable extra channels for alert delivery.">
        <div className="divide-y divide-gray-100">
          <Field label="Email">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Send email notifications</span>
              <Toggle value={prefs.enableEmail} onChange={v => set('enableEmail', v)} />
            </div>
          </Field>
          <Field label="Slack">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Send Slack notifications</span>
                <Toggle value={prefs.enableSlack} onChange={v => set('enableSlack', v)} />
              </div>
              {prefs.enableSlack && (
                <Input
                  type="url"
                  value={prefs.slackWebhook}
                  onChange={e => set('slackWebhook', e.target.value)}
                  placeholder="https://hooks.slack.com/services/..."
                />
              )}
            </div>
          </Field>
          <Field label="Discord">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Send Discord notifications</span>
                <Toggle value={prefs.enableDiscord} onChange={v => set('enableDiscord', v)} />
              </div>
              {prefs.enableDiscord && (
                <Input
                  type="url"
                  value={prefs.discordWebhook}
                  onChange={e => set('discordWebhook', e.target.value)}
                  placeholder="https://discord.com/api/webhooks/..."
                />
              )}
            </div>
          </Field>
        </div>
      </Section>

      <Section title="Quiet Hours" description="Suppress notifications during off hours.">
        <div className="divide-y divide-gray-100">
          <Field label="Enable Quiet Hours">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Pause all alerts during set hours</span>
              <Toggle value={prefs.quietHours} onChange={v => set('quietHours', v)} />
            </div>
          </Field>
          {prefs.quietHours && (
            <Field label="Hours" hint="Your local time">
              <div className="flex items-center gap-3 mt-1">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">From</label>
                  <select
                    value={prefs.quietStart}
                    onChange={e => set('quietStart', Number(e.target.value))}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none"
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={i}>{String(i).padStart(2, '0')}:00</option>
                    ))}
                  </select>
                </div>
                <span className="text-gray-400 mt-5">to</span>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Until</label>
                  <select
                    value={prefs.quietEnd}
                    onChange={e => set('quietEnd', Number(e.target.value))}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none"
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={i}>{String(i).padStart(2, '0')}:00</option>
                    ))}
                  </select>
                </div>
              </div>
            </Field>
          )}
        </div>
      </Section>

      <div className="flex justify-end">
        <SaveButton loading={saving}>Save Preferences</SaveButton>
      </div>
    </form>
  );
}

// ─── API ACCESS TAB ───────────────────────────────────────────────────────────

function ApiAccessTab({ user }) {
  const { addToast } = useToast();
  const tier = user?.subscription_tier ?? 'free';
  const hasAccess = tier !== 'free';

  const [apiKey, setApiKey] = useState(null);
  const [showKey, setShowKey] = useState(false);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('marketintel_api_key');
    if (stored) setApiKey(stored);
  }, []);

  const generateKey = () => {
    setGenerating(true);
    setTimeout(() => {
      const key = 'mi_live_' + Array.from(crypto.getRandomValues(new Uint8Array(24)))
        .map(b => b.toString(16).padStart(2, '0')).join('');
      localStorage.setItem('marketintel_api_key', key);
      setApiKey(key);
      setShowKey(true);
      setGenerating(false);
      addToast('API key generated', 'success');
    }, 600);
  };

  const copyKey = () => {
    if (apiKey) {
      navigator.clipboard.writeText(apiKey);
      addToast('API key copied to clipboard', 'success');
    }
  };

  const revokeKey = () => {
    localStorage.removeItem('marketintel_api_key');
    setApiKey(null);
    setShowKey(false);
    addToast('API key revoked', 'success');
  };

  if (!hasAccess) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">API Access — Business Plan</h3>
        <p className="text-gray-500 text-sm mb-6 max-w-md mx-auto">
          Programmatic access to your MarketIntel data requires a Business or Enterprise plan.
          Automate repricing, sync data to your stack, or build custom dashboards.
        </p>
        <Link href="/pricing" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors">
          View Upgrade Options
        </Link>
      </div>
    );
  }

  const maskedKey = apiKey ? apiKey.slice(0, 10) + '•'.repeat(20) + apiKey.slice(-4) : '';

  return (
    <div className="space-y-6">
      <Section title="API Key" description="Use this key to authenticate requests to the MarketIntel API.">
        {apiKey ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex-1 font-mono text-sm bg-gray-50 border border-gray-200 rounded-lg px-4 py-2.5 text-gray-700 overflow-auto">
                {showKey ? apiKey : maskedKey}
              </div>
              <button
                onClick={() => setShowKey(s => !s)}
                className="px-3 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                {showKey ? 'Hide' : 'Show'}
              </button>
              <button
                onClick={copyKey}
                className="px-3 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Copy
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={revokeKey}
                className="text-sm text-red-600 hover:text-red-700 font-medium"
              >
                Revoke Key
              </button>
              <span className="text-gray-300">·</span>
              <button
                onClick={generateKey}
                disabled={generating}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                Regenerate
              </button>
            </div>
            <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              Keep your API key secret. If compromised, revoke it immediately and generate a new one.
            </p>
          </div>
        ) : (
          <div className="text-center py-6">
            <p className="text-gray-500 text-sm mb-4">No active API key. Generate one to get started.</p>
            <button
              onClick={generateKey}
              disabled={generating}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50"
            >
              {generating && <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>}
              Generate API Key
            </button>
          </div>
        )}
      </Section>

      <Section title="Quick Reference" description="Authentication and base URL for API requests.">
        <div className="space-y-4">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">Base URL</p>
            <code className="block bg-gray-900 text-green-400 text-sm font-mono rounded-lg px-4 py-3">
              http://localhost:8000
            </code>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">Authentication Header</p>
            <code className="block bg-gray-900 text-green-400 text-sm font-mono rounded-lg px-4 py-3">
              Authorization: Bearer YOUR_API_KEY
            </code>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">Example Request</p>
            <pre className="bg-gray-900 text-green-400 text-sm font-mono rounded-lg px-4 py-3 overflow-x-auto">{`curl http://localhost:8000/products/ \\
  -H "Authorization: Bearer YOUR_API_KEY"`}</pre>
          </div>
        </div>
      </Section>
    </div>
  );
}

// ─── TEAM TAB ─────────────────────────────────────────────────────────────────

function TeamTab({ user }) {
  const { addToast } = useToast();
  const tier = user?.subscription_tier ?? 'free';
  const hasAccess = tier === 'business' || tier === 'enterprise';

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviting, setInviting] = useState(false);

  if (!hasAccess) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Team Workspaces — Business Plan</h3>
        <p className="text-gray-500 text-sm mb-6 max-w-md mx-auto">
          Collaborate with your team on competitive intelligence. Invite members, assign roles, and share
          saved views and alerts across your organization.
        </p>
        <div className="grid grid-cols-3 gap-4 max-w-sm mx-auto mb-6 text-left">
          {[
            { icon: '👤', label: 'Pro', seats: '1 seat' },
            { icon: '👥', label: 'Business', seats: '5 seats' },
            { icon: '🏢', label: 'Enterprise', seats: 'Unlimited' },
          ].map(p => (
            <div key={p.label} className="bg-gray-50 rounded-lg p-3 text-center">
              <div className="text-2xl mb-1">{p.icon}</div>
              <p className="text-xs font-semibold text-gray-700">{p.label}</p>
              <p className="text-xs text-gray-500">{p.seats}</p>
            </div>
          ))}
        </div>
        <Link href="/pricing" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors">
          Upgrade to Business
        </Link>
      </div>
    );
  }

  const handleInvite = (e) => {
    e.preventDefault();
    setInviting(true);
    setTimeout(() => {
      addToast(`Invitation sent to ${inviteEmail}`, 'success');
      setInviteEmail('');
      setInviting(false);
    }, 600);
  };

  return (
    <div className="space-y-6">
      <Section title="Invite Team Member" description="Send an invitation to collaborate on your workspace.">
        <form onSubmit={handleInvite} className="flex gap-3">
          <Input
            type="email"
            value={inviteEmail}
            onChange={e => setInviteEmail(e.target.value)}
            placeholder="colleague@example.com"
            required
            className="flex-1"
          />
          <select className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none">
            <option value="editor">Editor</option>
            <option value="viewer">Viewer</option>
            <option value="admin">Admin</option>
          </select>
          <SaveButton loading={inviting}>Invite</SaveButton>
        </form>
      </Section>

      <Section title="Current Members" description="People with access to your workspace.">
        <div className="divide-y divide-gray-100">
          {/* Owner row — always shown */}
          <div className="flex items-center justify-between py-3 first:pt-0">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center text-white text-sm font-semibold">
                {(user?.full_name?.[0] || user?.email?.[0] || '?').toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">{user?.full_name || user?.email}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
              </div>
            </div>
            <span className="text-xs font-medium bg-amber-100 text-amber-700 px-2.5 py-1 rounded-full">Owner</span>
          </div>
        </div>
        <p className="text-sm text-gray-400 mt-4 text-center">No other members yet. Invite someone above.</p>
      </Section>

      <Section title="Role Permissions" description="What each role can do in your workspace.">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-100">
                <th className="pb-3 pr-6">Permission</th>
                <th className="pb-3 pr-6 text-center">Viewer</th>
                <th className="pb-3 pr-6 text-center">Editor</th>
                <th className="pb-3 text-center">Admin</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {[
                ['View products & prices', true, true, true],
                ['Create & edit products', false, true, true],
                ['Manage alerts', false, true, true],
                ['Add competitors', false, true, true],
                ['Run scrapers', false, true, true],
                ['Invite team members', false, false, true],
                ['Manage billing', false, false, true],
              ].map(([label, viewer, editor, admin]) => (
                <tr key={label} className="text-gray-600">
                  <td className="py-2.5 pr-6">{label}</td>
                  {[viewer, editor, admin].map((has, i) => (
                    <td key={i} className="py-2.5 pr-6 text-center">
                      {has ? (
                        <svg className="w-4 h-4 text-green-500 mx-auto" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <span className="text-gray-200">—</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}

// ─── MAIN PAGE ────────────────────────────────────────────────────────────────

const TABS = [
  {
    key: 'profile',
    label: 'Profile',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
  },
  {
    key: 'billing',
    label: 'Billing',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
      </svg>
    ),
  },
  {
    key: 'notifications',
    label: 'Notifications',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    ),
  },
  {
    key: 'api',
    label: 'API Access',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
      </svg>
    ),
  },
  {
    key: 'team',
    label: 'Team',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
];

export default function SettingsPage() {
  const router = useRouter();
  const { user, loading, isAuthenticated, updateUser } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');

  // Read tab from query string
  useEffect(() => {
    const tab = router.query.tab;
    if (tab && TABS.find(t => t.key === tab)) setActiveTab(tab);
  }, [router.query.tab]);

  // Redirect unauthenticated users
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/auth/login');
    }
  }, [loading, isAuthenticated, router]);

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <svg className="animate-spin w-8 h-8 text-primary-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
      </Layout>
    );
  }

  if (!isAuthenticated) return null;

  const switchTab = (key) => {
    setActiveTab(key);
    router.replace({ pathname: '/settings', query: { tab: key } }, undefined, { shallow: true });
  };

  return (
    <Layout>
      <div className="px-4 sm:px-6 lg:px-8">
        {/* Page header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="mt-1 text-sm text-gray-500">Manage your account, billing, and preferences.</p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar tabs — desktop */}
          <aside className="hidden lg:block w-52 shrink-0">
            <nav className="space-y-1 sticky top-6">
              {TABS.map(tab => (
                <button
                  key={tab.key}
                  onClick={() => switchTab(tab.key)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors text-left
                    ${activeTab === tab.key
                      ? 'bg-primary-50 text-primary-700 border border-primary-200'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'}`}
                >
                  <span className={activeTab === tab.key ? 'text-primary-600' : 'text-gray-400'}>
                    {tab.icon}
                  </span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </aside>

          {/* Horizontal tabs — mobile */}
          <div className="lg:hidden">
            <div className="flex gap-1 overflow-x-auto pb-2 scrollbar-hide">
              {TABS.map(tab => (
                <button
                  key={tab.key}
                  onClick={() => switchTab(tab.key)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors shrink-0
                    ${activeTab === tab.key
                      ? 'bg-primary-600 text-white'
                      : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'}`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tab content */}
          <div className="flex-1 min-w-0">
            {activeTab === 'profile'       && <ProfileTab       user={user} updateUser={updateUser} />}
            {activeTab === 'billing'       && <BillingTab       user={user} />}
            {activeTab === 'notifications' && <NotificationsTab user={user} />}
            {activeTab === 'api'           && <ApiAccessTab     user={user} />}
            {activeTab === 'team'          && <TeamTab          user={user} />}
          </div>
        </div>
      </div>
    </Layout>
  );
}
