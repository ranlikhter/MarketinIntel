import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/Toast';
import api from '../../lib/api';

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  return api.request(path, options);
}

// ─── Shared UI primitives ─────────────────────────────────────────────────────

function Section({ title, description, children }) {
  return (
    <div className="rounded-2xl shadow-glass overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
      <div className="px-6 py-5" style={{ borderBottom: '1px solid var(--border)' }}>
        <h3 className="text-base font-semibold text-white">{title}</h3>
        {description && <p className="mt-0.5 text-sm" style={{ color: 'var(--text-muted)' }}>{description}</p>}
      </div>
      <div className="px-6 py-5">{children}</div>
    </div>
  );
}

function Field({ label, hint, children }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-8 py-3 first:pt-0 last:pb-0">
      <div className="sm:w-48 shrink-0">
        <label className="block text-sm font-medium text-white/70">{label}</label>
        {hint && <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{hint}</p>}
      </div>
      <div className="flex-1">{children}</div>
    </div>
  );
}

function Input({ className = '', ...props }) {
  return (
    <input
      className={`glass-input block w-full rounded-lg px-3 py-2 text-sm text-white placeholder-white/30
        focus:outline-none transition-shadow ${className}`}
      {...props}
    />
  );
}

function SaveButton({ loading, children = 'Save Changes' }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg gradient-brand text-white text-sm font-medium
        hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity shadow-gradient focus:outline-none
        focus:ring-2 focus:ring-amber-400"
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
    blue:   { bar: 'bg-blue-500'   },
    green:  { bar: 'bg-green-500'  },
    purple: { bar: 'bg-purple-500' },
  };
  const c = colorMap[color] ?? colorMap.blue;
  const barColor = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : c.bar;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-white/70">{label}</span>
        <span style={{ color: 'var(--text-muted)' }}>
          {limit >= 9999 ? `${used} / Unlimited` : `${used} / ${limit}`}
        </span>
      </div>
      {limit < 9999 && (
        <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-elevated)' }}>
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
      {limit < 9999 && pct >= 90 && (
        <p className="text-xs text-red-400 font-medium">
          {pct === 100 ? 'Limit reached — upgrade to add more' : `${100 - pct}% remaining`}
        </p>
      )}
    </div>
  );
}

// ─── TIER CONFIG ──────────────────────────────────────────────────────────────

const TIERS = {
  free:       { label: 'Free',       gradient: 'from-gray-500 to-gray-600',     badge: 'bg-gray-700 text-gray-300'    },
  pro:        { label: 'Pro',        gradient: 'from-blue-500 to-blue-700',     badge: 'bg-blue-900/60 text-blue-300'    },
  business:   { label: 'Business',   gradient: 'from-purple-500 to-purple-700', badge: 'bg-purple-900/60 text-purple-300'},
  enterprise: { label: 'Enterprise', gradient: 'from-amber-500 to-amber-600',   badge: 'bg-amber-900/60 text-amber-300'  },
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
      className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60"
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
  const providerLabel = user?.auth_provider === 'google'
    ? 'Google SSO'
    : user?.auth_provider === 'microsoft'
      ? 'Microsoft SSO'
      : 'Email & Password';
  const signInMethodLabel =
    user?.password_login_enabled && ['google', 'microsoft'].includes(user?.auth_provider)
      ? `${providerLabel} + Password`
      : providerLabel;

  return (
    <div className="space-y-6">
      {/* Profile info */}
      <Section title="Profile Information" description="Update your display name visible across the platform.">
        {/* Avatar */}
        <div className="flex items-center gap-4 mb-6">
          {user?.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.full_name || user.email || 'Profile'}
              className="w-16 h-16 rounded-full object-cover ring-4 ring-blue-900/60"
            />
          ) : (
            <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-white text-2xl font-bold select-none ring-4 ring-blue-900/60">
              {(user?.full_name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)) ||
               user?.email?.[0]?.toUpperCase() || '?'}
            </div>
          )}
          <div>
            <p className="font-semibold text-white">{user?.full_name || 'No name set'}</p>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{user?.email}</p>
            <div className="flex items-center gap-1.5 mt-1">
              {user?.is_verified ? (
                <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full" style={{ background: 'rgba(16,185,129,0.15)', color: '#34d399' }}>
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Verified
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full" style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}>
                  Email not verified
                </span>
              )}
              <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full" style={{ background: 'rgba(59,130,246,0.15)', color: '#93c5fd' }}>
                {signInMethodLabel}
              </span>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Member since {memberSince}</span>
            </div>
          </div>
        </div>

        <form onSubmit={handleSaveName} className="divide-y" style={{ '--tw-divide-opacity': 1 }}>
          <div style={{ borderBottom: '1px solid var(--border)' }}>
            <Field label="Full Name" hint="Shown in your account menu">
              <Input
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Jane Smith"
              />
            </Field>
          </div>
          <div style={{ borderBottom: '1px solid var(--border)' }}>
            <Field label="Email Address" hint="Cannot be changed">
              <Input value={user?.email ?? ''} readOnly disabled className="opacity-50 cursor-not-allowed" />
            </Field>
          </div>
          <div style={{ borderBottom: '1px solid var(--border)' }}>
            <Field label="Sign-in Method" hint="How this account authenticates">
              <Input value={signInMethodLabel} readOnly disabled className="opacity-50 cursor-not-allowed" />
            </Field>
          </div>
          <div className="pt-4">
            <SaveButton loading={savingName} />
          </div>
        </form>
      </Section>

      {/* Change password */}
      <Section title="Change Password" description="Use a strong, unique password.">
        {!user?.password_login_enabled ? (
          <div className="rounded-xl px-4 py-3 text-sm" style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', color: '#bfdbfe' }}>
            This account signs in with {signInMethodLabel}. Password changes are disabled because this account does not have a local password.
          </div>
        ) : (
        <form onSubmit={handleChangePw} className="divide-y">
          <div style={{ borderBottom: '1px solid var(--border)' }}>
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
          </div>
          <div style={{ borderBottom: '1px solid var(--border)' }}>
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
                    <div key={i} className={`h-1 flex-1 rounded-full ${pw.next.length >= len ? 'bg-green-500' : 'bg-white/10'}`} />
                  ))}
                  <span className="text-xs ml-2" style={{ color: 'var(--text-muted)' }}>
                    {pw.next.length < 8 ? 'Too short' : pw.next.length < 12 ? 'OK' : pw.next.length < 16 ? 'Good' : 'Strong'}
                  </span>
                </div>
              )}
            </Field>
          </div>
          <div style={{ borderBottom: '1px solid var(--border)' }}>
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
                <p className="text-xs text-red-400 mt-1">Passwords do not match</p>
              )}
              {pw.confirm && pw.next && pw.confirm === pw.next && (
                <p className="text-xs text-green-400 mt-1 flex items-center gap-1">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Passwords match
                </p>
              )}
            </Field>
          </div>
          {pwError && (
            <div className="pt-3">
              <p className="text-sm text-red-400 rounded-lg px-3 py-2" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}>{pwError}</p>
            </div>
          )}
          <div className="pt-4">
            <SaveButton loading={savingPw}>Change Password</SaveButton>
          </div>
        </form>
        )}
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
      features: ['50 products', '100 competitor matches', '10 alerts', 'Priority scraping', 'Advanced analytics'],
    },
    {
      key: 'business',
      name: 'Business',
      price: '$149',
      priceId: 'price_business_monthly',
      gradient: 'from-purple-500 to-purple-700',
      features: ['200 products', '500 competitor matches', '50 alerts', 'Team workspace', 'API access', 'White-label reports'],
    },
    {
      key: 'enterprise',
      name: 'Enterprise',
      price: '$499',
      priceId: 'price_enterprise_monthly',
      gradient: 'from-amber-500 to-amber-600',
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
              className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium text-white transition-colors"
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
              <div key={plan.key} className="rounded-xl overflow-hidden" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                <div className={`bg-gradient-to-br ${plan.gradient} px-4 py-4 text-white`}>
                  <p className="font-bold text-lg">{plan.name}</p>
                  <p className="text-white/80 text-sm">{plan.price}<span className="text-xs">/mo</span></p>
                </div>
                <div className="px-4 py-4 space-y-2">
                  {plan.features.map(f => (
                    <div key={f} className="flex items-center gap-2 text-sm text-white/70">
                      <svg className="w-4 h-4 text-green-400 shrink-0" fill="currentColor" viewBox="0 0 20 20">
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
  const [testingSend, setTestingSend] = useState(false);

  // ── Push notification state ─────────────────────────────────────────────────
  const [pushSupported, setPushSupported] = useState(false);
  const [pushSubscribed, setPushSubscribed] = useState(false);
  const [pushLoading, setPushLoading] = useState(false);

  // ── Webhook test state ──────────────────────────────────────────────────────
  const [testingSlack, setTestingSlack] = useState(false);
  const [testingDiscord, setTestingDiscord] = useState(false);
  const [slackStatus, setSlackStatus] = useState(null);   // 'ok' | 'error'
  const [discordStatus, setDiscordStatus] = useState(null);

  // Check push support and current subscription status on mount
  useEffect(() => {
    const supported = 'serviceWorker' in navigator && 'PushManager' in window;
    setPushSupported(supported);
    if (!supported) return;
    navigator.serviceWorker.ready.then(reg => {
      reg.pushManager.getSubscription().then(sub => {
        setPushSubscribed(!!sub);
      });
    }).catch(() => {});
  }, []);

  const handlePushToggle = async () => {
    if (!pushSupported) return;
    setPushLoading(true);
    try {
      const reg = await navigator.serviceWorker.ready;
      const existing = await reg.pushManager.getSubscription();

      if (existing) {
        // Unsubscribe
        await existing.unsubscribe();
        await api.unsubscribePush(existing.endpoint);
        setPushSubscribed(false);
        addToast('Browser push notifications disabled', 'info');
      } else {
        // Subscribe — fetch VAPID key first
        const { vapid_public_key: vapidKey } = await api.getPushVapidKey();
        if (!vapidKey) throw new Error('VAPID key unavailable');

        const sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: vapidKey,
        });
        const json = sub.toJSON();
        await api.subscribePush(
          json.endpoint,
          json.keys.p256dh,
          json.keys.auth,
          navigator.userAgent,
        );
        setPushSubscribed(true);
        addToast('Browser push notifications enabled', 'success');
      }
    } catch (err) {
      addToast(`Push setup failed: ${err.message}`, 'error');
    } finally {
      setPushLoading(false);
    }
  };

  const handleTestSlack = async () => {
    setTestingSlack(true);
    setSlackStatus(null);
    try {
      await api.testSlackWebhook();
      setSlackStatus('ok');
      addToast('Test message sent to Slack', 'success');
    } catch (err) {
      setSlackStatus('error');
      addToast(`Slack test failed: ${err.message}`, 'error');
    } finally {
      setTestingSlack(false);
    }
  };

  const handleTestDiscord = async () => {
    setTestingDiscord(true);
    setDiscordStatus(null);
    try {
      await api.testDiscordWebhook();
      setDiscordStatus('ok');
      addToast('Test message sent to Discord', 'success');
    } catch (err) {
      setDiscordStatus('error');
      addToast(`Discord test failed: ${err.message}`, 'error');
    } finally {
      setTestingDiscord(false);
    }
  };

  const handleTestPush = async () => {
    setPushLoading(true);
    try {
      await api.sendTestPush();
      addToast('Test push notification sent', 'success');
    } catch (err) {
      addToast(`Failed: ${err.message}`, 'error');
    } finally {
      setPushLoading(false);
    }
  };

  useEffect(() => {
    // Try to load from backend first, fall back to localStorage
    apiFetch('/api/notifications/preferences')
      .then(data => {
        setPrefs(p => ({ ...p, ...data }));
        localStorage.setItem(PREFS_KEY, JSON.stringify({ ...DEFAULT_PREFS, ...data }));
      })
      .catch(() => {
        try {
          const stored = JSON.parse(localStorage.getItem(PREFS_KEY) || '{}');
          setPrefs(p => ({ ...p, ...stored, defaultEmail: stored.defaultEmail || user?.email || '' }));
        } catch {
          setPrefs(p => ({ ...p, defaultEmail: user?.email || '' }));
        }
      });
  }, [user]);

  const set = (key, val) => setPrefs(p => ({ ...p, [key]: val }));

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
    try {
      await apiFetch('/api/notifications/preferences', {
        method: 'POST',
        body: JSON.stringify(prefs),
      });
      addToast('Notification preferences saved', 'success');
    } catch {
      addToast('Saved locally (backend unavailable)', 'info');
    } finally {
      setSaving(false);
    }
  };

  const handleTestEmail = async () => {
    if (!prefs.defaultEmail) { addToast('Enter a notification email first', 'error'); return; }
    setTestingSend(true);
    try {
      await apiFetch('/api/notifications/test-email', {
        method: 'POST',
        body: JSON.stringify({ email: prefs.defaultEmail }),
      });
      addToast(`Test email sent to ${prefs.defaultEmail}`, 'success');
    } catch (err) {
      addToast(`Failed: ${err.message}`, 'error');
    } finally {
      setTestingSend(false);
    }
  };

  const Toggle = ({ value, onChange, disabled }) => (
    <button
      type="button"
      role="switch"
      aria-checked={value}
      onClick={() => !disabled && onChange(!value)}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors
        focus:outline-none focus:ring-2 focus:ring-amber-500
        ${value ? 'bg-amber-500' : 'bg-white/20'}
        ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
    >
      <span className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-md transform transition-transform ${value ? 'translate-x-5' : 'translate-x-0'}`} />
    </button>
  );

  return (
    <form onSubmit={handleSave} className="space-y-6">
      <Section title="Default Notification Settings" description="These defaults apply when you create new alert rules.">
        <div className="divide-y" style={{ '--tw-divide-color': 'var(--border)' }}>
          <div style={{ borderBottom: '1px solid var(--border)' }}>
            <Field label="Notification Email" hint="Where alerts will be sent by default">
              <div className="flex gap-2">
                <Input
                  type="email"
                  value={prefs.defaultEmail}
                  onChange={e => set('defaultEmail', e.target.value)}
                  placeholder="you@example.com"
                  className="flex-1"
                />
                <button
                  type="button"
                  onClick={handleTestEmail}
                  disabled={testingSend || !prefs.defaultEmail}
                  className="shrink-0 inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-white/60 hover:bg-white/5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ border: '1px solid var(--border)' }}
                  title="Send a test email to verify delivery"
                >
                  {testingSend ? (
                    <span className="w-3.5 h-3.5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  )}
                  Test
                </button>
              </div>
            </Field>
          </div>
          <div>
            <Field label="Delivery Frequency" hint="How often to bundle alert notifications">
              <div className="flex flex-col sm:flex-row gap-3 mt-1">
                {[
                  { value: 'instant', label: 'Instant', desc: 'As they happen' },
                  { value: 'daily',   label: 'Daily Digest', desc: '8 AM summary' },
                  { value: 'weekly',  label: 'Weekly Digest', desc: 'Monday summary' },
                ].map(opt => (
                  <label key={opt.value} className={`flex-1 flex items-center gap-3 rounded-lg border-2 px-4 py-3 cursor-pointer transition-colors
                    ${prefs.digestFrequency === opt.value ? 'border-amber-400 bg-amber-400/10' : 'hover:border-white/20'}`}
                    style={{ borderColor: prefs.digestFrequency === opt.value ? undefined : 'var(--border)' }}>
                    <input
                      type="radio"
                      name="digestFrequency"
                      value={opt.value}
                      checked={prefs.digestFrequency === opt.value}
                      onChange={() => set('digestFrequency', opt.value)}
                      className="text-amber-400"
                    />
                    <div>
                      <p className="text-sm font-medium text-white">{opt.label}</p>
                      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{opt.desc}</p>
                    </div>
                  </label>
                ))}
              </div>
            </Field>
          </div>
        </div>
      </Section>

      <Section title="Notification Channels" description="Enable extra channels for alert delivery.">
        <div className="space-y-3">

          {/* ── Email ──────────────────────────────────────────────────────── */}
          <div className="rounded-xl p-4 transition-all"
            style={{ background: prefs.enableEmail ? 'rgba(59,130,246,0.08)' : 'var(--bg-elevated)', border: `1px solid ${prefs.enableEmail ? 'rgba(59,130,246,0.3)' : 'var(--border)'}` }}>
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.25)' }}>
                  <svg className="w-4 h-4" style={{ color: '#3b82f6' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-white">Email</p>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Instant & digest alerts to your inbox</p>
                </div>
              </div>
              <Toggle value={prefs.enableEmail} onChange={v => set('enableEmail', v)} />
            </div>
          </div>

          {/* ── Slack ──────────────────────────────────────────────────────── */}
          <div className="rounded-xl p-4 transition-all"
            style={{ background: prefs.enableSlack ? 'rgba(74,196,107,0.08)' : 'var(--bg-elevated)', border: `1px solid ${prefs.enableSlack ? 'rgba(74,196,107,0.35)' : 'var(--border)'}` }}>
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: 'rgba(74,196,107,0.15)', border: '1px solid rgba(74,196,107,0.25)' }}>
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" fill="#4AC46B"/>
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-white">Slack</p>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Post alerts to a Slack channel</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {slackStatus === 'ok' && <span className="text-xs font-medium" style={{ color: '#4ac46b' }}>Connected</span>}
                {slackStatus === 'error' && <span className="text-xs font-medium" style={{ color: '#ef4444' }}>Failed</span>}
                <Toggle value={prefs.enableSlack} onChange={v => set('enableSlack', v)} />
              </div>
            </div>
            {prefs.enableSlack && (
              <div className="mt-3 space-y-2">
                <Input
                  type="url"
                  value={prefs.slackWebhook}
                  onChange={e => { set('slackWebhook', e.target.value); setSlackStatus(null); }}
                  placeholder="https://hooks.slack.com/services/..."
                />
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  Create a webhook in <strong style={{ color: 'rgba(255,255,255,0.5)' }}>Slack → Apps → Incoming Webhooks</strong>
                </p>
                {prefs.slackWebhook && (
                  <button type="button" onClick={handleTestSlack} disabled={testingSlack}
                    className="text-xs px-3 py-1.5 rounded-lg font-medium transition-all disabled:opacity-50"
                    style={{ background: 'rgba(74,196,107,0.12)', border: '1px solid rgba(74,196,107,0.3)', color: '#4ac46b' }}>
                    {testingSlack ? 'Sending…' : 'Send test message'}
                  </button>
                )}
              </div>
            )}
          </div>

          {/* ── Discord ────────────────────────────────────────────────────── */}
          <div className="rounded-xl p-4 transition-all"
            style={{ background: prefs.enableDiscord ? 'rgba(88,101,242,0.08)' : 'var(--bg-elevated)', border: `1px solid ${prefs.enableDiscord ? 'rgba(88,101,242,0.35)' : 'var(--border)'}` }}>
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: 'rgba(88,101,242,0.15)', border: '1px solid rgba(88,101,242,0.25)' }}>
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="#5865F2">
                    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-white">Discord</p>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Post alerts to a Discord server</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {discordStatus === 'ok' && <span className="text-xs font-medium" style={{ color: '#5865f2' }}>Connected</span>}
                {discordStatus === 'error' && <span className="text-xs font-medium" style={{ color: '#ef4444' }}>Failed</span>}
                <Toggle value={prefs.enableDiscord} onChange={v => set('enableDiscord', v)} />
              </div>
            </div>
            {prefs.enableDiscord && (
              <div className="mt-3 space-y-2">
                <Input
                  type="url"
                  value={prefs.discordWebhook}
                  onChange={e => { set('discordWebhook', e.target.value); setDiscordStatus(null); }}
                  placeholder="https://discord.com/api/webhooks/..."
                />
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  Create a webhook in <strong style={{ color: 'rgba(255,255,255,0.5)' }}>Discord → Server Settings → Integrations → Webhooks</strong>
                </p>
                {prefs.discordWebhook && (
                  <button type="button" onClick={handleTestDiscord} disabled={testingDiscord}
                    className="text-xs px-3 py-1.5 rounded-lg font-medium transition-all disabled:opacity-50"
                    style={{ background: 'rgba(88,101,242,0.12)', border: '1px solid rgba(88,101,242,0.3)', color: '#5865f2' }}>
                    {testingDiscord ? 'Sending…' : 'Send test message'}
                  </button>
                )}
              </div>
            )}
          </div>

          {/* ── Browser Push ───────────────────────────────────────────────── */}
          <div className="rounded-xl p-4 transition-all"
            style={{ background: pushSubscribed ? 'rgba(245,158,11,0.08)' : 'var(--bg-elevated)', border: `1px solid ${pushSubscribed ? 'rgba(245,158,11,0.3)' : 'var(--border)'}`, opacity: pushSupported ? 1 : 0.5 }}>
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.25)' }}>
                  <svg className="w-4 h-4" style={{ color: '#f59e0b' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-white">Browser Push</p>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {!pushSupported ? 'Not supported in this browser' : pushSubscribed ? 'Active on this device' : 'Instant OS-level alerts'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {pushSubscribed && (
                  <button type="button" onClick={handleTestPush} disabled={pushLoading}
                    className="text-xs px-3 py-1.5 rounded-lg font-medium transition-all disabled:opacity-50"
                    style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.3)', color: '#f59e0b' }}>
                    {pushLoading ? 'Sending…' : 'Test'}
                  </button>
                )}
                <Toggle value={pushSubscribed} onChange={handlePushToggle} disabled={!pushSupported || pushLoading} />
              </div>
            </div>
          </div>

        </div>
      </Section>

      <Section title="Quiet Hours" description="Suppress notifications during off hours.">
        <div>
          <div style={{ borderBottom: prefs.quietHours ? '1px solid var(--border)' : undefined }}>
            <Field label="Enable Quiet Hours">
              <div className="flex items-center justify-between">
                <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Pause all alerts during set hours</span>
                <Toggle value={prefs.quietHours} onChange={v => set('quietHours', v)} />
              </div>
            </Field>
          </div>
          {prefs.quietHours && (
            <Field label="Hours" hint="Your local time">
              <div className="flex items-center gap-3 mt-1">
                <div>
                  <label className="block text-xs mb-1" style={{ color: 'var(--text-muted)' }}>From</label>
                  <select
                    value={prefs.quietStart}
                    onChange={e => set('quietStart', Number(e.target.value))}
                    className="glass-input rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={i}>{String(i).padStart(2, '0')}:00</option>
                    ))}
                  </select>
                </div>
                <span className="mt-5" style={{ color: 'var(--text-muted)' }}>to</span>
                <div>
                  <label className="block text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Until</label>
                  <select
                    value={prefs.quietEnd}
                    onChange={e => set('quietEnd', Number(e.target.value))}
                    className="glass-input rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
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
  const [keys, setKeys]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [newKey, setNewKey]   = useState(null); // shows full_key once after creation
  const [creating, setCreating] = useState(false);
  const [keyName, setKeyName]   = useState('');

  useEffect(() => {
    api.request('/api/auth/api-keys')
      .then(setKeys)
      .catch(() => setKeys([]))
      .finally(() => setLoading(false));
  }, []);

  async function createKey(e) {
    e.preventDefault();
    if (!keyName.trim()) return;
    setCreating(true);
    try {
      const data = await api.request('/api/auth/api-keys', {
        method: 'POST',
        body: JSON.stringify({ name: keyName.trim() }),
      });
      setKeys((prev) => [data, ...prev]);
      setNewKey(data.full_key);
      setKeyName('');
      addToast('API key created — save it now!', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to create key', 'error');
    } finally {
      setCreating(false);
    }
  }

  async function revokeKey(id, name) {
    if (!confirm(`Revoke "${name}"?`)) return;
    try {
      await api.request(`/api/auth/api-keys/${id}`, { method: 'DELETE' });
      setKeys((prev) => prev.filter((k) => k.id !== id));
      addToast('Key revoked', 'success');
    } catch {
      addToast('Failed to revoke key', 'error');
    }
  }

  return (
    <div className="space-y-6">
      {/* New-key reveal banner */}
      {newKey && (
        <div className="rounded-xl p-4" style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.25)' }}>
          <p className="text-sm font-semibold text-emerald-400 mb-2">Save your API key — shown only once</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded-lg px-3 py-2 text-sm font-mono text-white/80 truncate" style={{ background: 'var(--bg-elevated)', border: '1px solid rgba(16,185,129,0.2)' }}>{newKey}</code>
            <button onClick={() => { navigator.clipboard.writeText(newKey); addToast('Copied!', 'success'); }}
              className="shrink-0 px-3 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors">Copy</button>
            <button onClick={() => setNewKey(null)} className="text-emerald-400 hover:text-emerald-300 text-xl leading-none">&times;</button>
          </div>
        </div>
      )}

      <Section title="API Keys" description="Keys authenticate external scripts and apps against the MarketIntel API.">
        {/* Create form */}
        <form onSubmit={createKey} className="flex gap-2 mb-5">
          <Input value={keyName} onChange={(e) => setKeyName(e.target.value)} placeholder="Key name, e.g. Zapier automation" className="flex-1" />
          <SaveButton loading={creating}>Create Key</SaveButton>
        </form>

        {/* Key list */}
        {loading ? (
          <p className="text-sm text-center py-4" style={{ color: 'var(--text-muted)' }}>Loading…</p>
        ) : keys.length === 0 ? (
          <p className="text-sm text-center py-4" style={{ color: 'var(--text-muted)' }}>No API keys yet.</p>
        ) : (
          <div>
            {keys.map((k) => (
              <div key={k.id} className="flex items-center justify-between py-3 first:pt-0" style={{ borderBottom: '1px solid var(--border)' }}>
                <div>
                  <p className="text-sm font-medium text-white">{k.name}</p>
                  <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{k.key_prefix}••••••••••••</p>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Created {new Date(k.created_at).toLocaleDateString()}</p>
                </div>
                <button onClick={() => revokeKey(k.id, k.name)}
                  className="text-xs text-red-400 hover:text-red-300 font-medium px-3 py-1.5 rounded-lg hover:bg-red-500/10 transition-colors"
                  style={{ border: '1px solid rgba(239,68,68,0.2)' }}>
                  Revoke
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="mt-4 pt-4" style={{ borderTop: '1px solid var(--border)' }}>
          <Link href="/settings/api-keys" className="text-sm text-amber-400 hover:text-amber-300 font-medium">
            Full API key management →
          </Link>
        </div>
      </Section>

      <Section title="Quick Reference" description="Authentication and base URL for API requests.">
        <div className="space-y-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-muted)' }}>Authentication Header</p>
            <code className="block text-green-400 text-sm font-mono rounded-lg px-4 py-3" style={{ background: 'var(--bg-elevated)' }}>
              Authorization: Bearer YOUR_API_KEY
            </code>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-muted)' }}>Example Request</p>
            <pre className="text-green-400 text-sm font-mono rounded-lg px-4 py-3 overflow-x-auto" style={{ background: 'var(--bg-elevated)' }}>{`curl http://localhost:8000/products/ \\
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

  const [workspaces, setWorkspaces]   = useState([]);
  const [loadingWs, setLoadingWs]     = useState(true);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole]   = useState('editor');
  const [inviting, setInviting]       = useState(false);
  const [activeWsId, setActiveWsId]   = useState(null);

  useEffect(() => {
    if (!hasAccess) { setLoadingWs(false); return; }
    apiFetch('/api/workspaces')
      .then((data) => {
        setWorkspaces(data);
        if (data.length > 0) setActiveWsId(data[0].id);
      })
      .catch(() => setWorkspaces([]))
      .finally(() => setLoadingWs(false));
  }, [hasAccess]);

  if (!hasAccess) {
    return (
      <div className="rounded-2xl shadow-glass p-12 text-center" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
        <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--bg-elevated)' }}>
          <svg className="w-8 h-8" style={{ color: 'var(--text-muted)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-white mb-2">Team Workspaces — Business Plan</h3>
        <p className="text-sm mb-6 max-w-md mx-auto" style={{ color: 'var(--text-muted)' }}>
          Collaborate with your team on competitive intelligence. Invite members, assign roles, and share
          saved views and alerts across your organization.
        </p>
        <div className="grid grid-cols-3 gap-4 max-w-sm mx-auto mb-6 text-left">
          {[
            { initial: 'P', label: 'Pro', seats: '1 seat', bg: 'rgba(59,130,246,0.15)', color: '#60a5fa' },
            { initial: 'B', label: 'Business', seats: '5 seats', bg: 'rgba(139,92,246,0.15)', color: '#a78bfa' },
            { initial: 'E', label: 'Enterprise', seats: 'Unlimited', bg: 'rgba(245,158,11,0.15)', color: '#f59e0b' },
          ].map(p => (
            <div key={p.label} className="rounded-xl p-3 text-center" style={{ background: 'var(--bg-elevated)' }}>
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold mx-auto mb-2" style={{ background: p.bg, color: p.color }}>{p.initial}</div>
              <p className="text-xs font-semibold text-white/70">{p.label}</p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{p.seats}</p>
            </div>
          ))}
        </div>
        <Link href="/pricing" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg gradient-brand text-white text-sm font-medium transition-opacity hover:opacity-90 shadow-gradient">
          Upgrade to Business
        </Link>
      </div>
    );
  }

  const ws = workspaces.find((w) => w.id === activeWsId);

  async function handleInvite(e) {
    e.preventDefault();
    if (!activeWsId) { addToast('No workspace selected', 'error'); return; }
    setInviting(true);
    try {
      await apiFetch(`/api/workspaces/${activeWsId}/members`, {
        method: 'POST',
        body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole }),
      });
      const updated = await apiFetch(`/api/workspaces/${activeWsId}`);
      setWorkspaces((prev) => prev.map((w) => (w.id === activeWsId ? updated : w)));
      setInviteEmail('');
      addToast(`Invitation sent to ${inviteEmail}`, 'success');
    } catch (err) {
      addToast(err.message || 'Failed to invite member', 'error');
    } finally {
      setInviting(false);
    }
  }

  async function handleRemoveMember(uid) {
    if (!confirm('Remove this member from the workspace?')) return;
    try {
      await apiFetch(`/api/workspaces/${activeWsId}/members/${uid}`, { method: 'DELETE' });
      setWorkspaces((prev) =>
        prev.map((w) =>
          w.id === activeWsId
            ? { ...w, members: (w.members || []).filter((m) => m.user_id !== uid) }
            : w
        )
      );
      addToast('Member removed', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to remove member', 'error');
    }
  }

  return (
    <div className="space-y-6">
      {/* Workspace switcher (if user belongs to multiple) */}
      {workspaces.length > 1 && (
        <div className="flex gap-2 flex-wrap">
          {workspaces.map((w) => (
            <button key={w.id} onClick={() => setActiveWsId(w.id)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                activeWsId === w.id ? 'gradient-brand text-white shadow-gradient' : 'text-white/70 hover:bg-white/5'
              }`}
              style={activeWsId !== w.id ? { border: '1px solid var(--border)' } : {}}>
              {w.name}
            </button>
          ))}
        </div>
      )}

      {/* Invite form */}
      <Section title="Invite Team Member" description="Send an invitation to collaborate on your workspace.">
        {loadingWs ? (
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading workspace…</p>
        ) : workspaces.length === 0 ? (
          <div className="text-center py-4">
            <p className="text-sm mb-3" style={{ color: 'var(--text-muted)' }}>No workspace yet. Create one from the full team page.</p>
            <Link href="/settings/team" className="text-sm text-amber-400 hover:text-amber-300 font-medium">
              Go to Team Management →
            </Link>
          </div>
        ) : (
          <form onSubmit={handleInvite} className="flex gap-3">
            <Input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="colleague@example.com"
              required
              className="flex-1"
            />
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="glass-input rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
            >
              <option value="editor">Editor</option>
              <option value="viewer">Viewer</option>
              <option value="admin">Admin</option>
            </select>
            <SaveButton loading={inviting}>Invite</SaveButton>
          </form>
        )}
      </Section>

      {/* Member list for active workspace */}
      {ws && (
        <Section title={`Members — ${ws.name}`} description="People with access to this workspace.">
          <div>
            {(ws.members || []).length === 0 ? (
              <p className="text-sm py-3 text-center" style={{ color: 'var(--text-muted)' }}>No members yet.</p>
            ) : (ws.members || []).map((m) => (
              <div key={m.user_id} className="flex items-center justify-between py-3 first:pt-0" style={{ borderBottom: '1px solid var(--border)' }}>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-semibold">
                    {(m.full_name?.[0] || m.email?.[0] || '?').toUpperCase()}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{m.full_name || m.email}</p>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{m.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {m.user_id === ws.owner_id ? (
                    <span className="text-xs font-medium px-2.5 py-1 rounded-full" style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}>Owner</span>
                  ) : (
                    <>
                      <span className="text-xs font-medium px-2.5 py-1 rounded-full capitalize" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>{m.role}</span>
                      <button onClick={() => handleRemoveMember(m.user_id)}
                        className="text-xs text-red-400 hover:text-red-300 font-medium px-2.5 py-1 rounded-lg hover:bg-red-500/10 transition-colors"
                        style={{ border: '1px solid rgba(239,68,68,0.2)' }}>
                        Remove
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      <div className="text-center pt-2">
        <Link href="/settings/team" className="text-sm text-amber-400 hover:text-amber-300 font-medium">
          Full team management →
        </Link>
      </div>
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
          <svg className="animate-spin w-8 h-8 border-amber-500" fill="none" viewBox="0 0 24 24">
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
      <div className="p-4 lg:p-6 space-y-5">
        {/* Page header */}
        <div>
          <h1 className="text-xl font-bold text-white">Settings</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>Manage your account, billing, and preferences.</p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar tabs — desktop */}
          <aside className="hidden lg:block w-52 shrink-0">
            <nav className="space-y-1 sticky top-6">
              {TABS.map(tab => (
                <button
                  key={tab.key}
                  onClick={() => switchTab(tab.key)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all text-left
                    ${activeTab === tab.key
                      ? 'gradient-brand text-white shadow-gradient'
                      : 'text-white/60 hover:bg-white/5 hover:text-white/90'}`}
                >
                  <span className={activeTab === tab.key ? 'text-white' : 'text-white/30'}>
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
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all shrink-0
                    ${activeTab === tab.key
                      ? 'gradient-brand text-white shadow-gradient'
                      : 'text-white/60 hover:bg-white/5'}`}
                  style={activeTab !== tab.key ? { border: '1px solid var(--border)' } : {}}
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
