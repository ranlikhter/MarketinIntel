"""Write all redesigned page files."""
import os, sys

BASE = 'C:/Users/ranli/Scrape/frontend'

def w(path, content):
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  ok {path}')

# =========================================================
# AUTH PAGES  (no Layout — full-screen dark)
# =========================================================

AUTH_SHELL_OPEN = r"""
function AuthShell({ title, subtitle, tag, children }) {
  return (
    <div style={{ minHeight: '100vh', background: '#0A0A0F', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '32px 16px',
      backgroundImage: 'linear-gradient(rgba(255,255,255,0.02) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.02) 1px,transparent 1px)',
      backgroundSize: '32px 32px' }}>
      <div style={{ width: '100%', maxWidth: '420px' }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <div style={{ width: '40px', height: '40px', background: '#F59E0B', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
            <svg width="22" height="22" viewBox="0 0 16 16" fill="none"><path d="M2 11L6 6.5l3 3L14 3" stroke="#0A0A0F" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </div>
          {tag && <div style={{ fontSize: '10px', color: '#F59E0B', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.12em', marginBottom: '12px' }}>{tag}</div>}
          <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '26px', color: '#F0F0FA', letterSpacing: '-0.03em', marginBottom: '8px' }}>{title}</h1>
          {subtitle && <p style={{ fontSize: '14px', color: '#9090B8' }}>{subtitle}</p>}
        </div>
        {/* Card */}
        <div style={{ background: '#111118', border: '1px solid #1E1E2E', borderRadius: '12px', padding: '32px', boxShadow: '0 24px 64px rgba(0,0,0,0.5)' }}>
          {children}
        </div>
      </div>
    </div>
  );
}
"""

w('pages/auth/login.js', r"""
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../../context/AuthContext';
import { Btn, Input, Field, Alert, Divider } from '../../components/UI';

""" + AUTH_SHELL_OPEN + r"""
export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const r = await login(email, password);
      if (r.success) router.push(router.query.redirect || '/dashboard');
      else setError(r.error || 'Login failed');
    } catch { setError('An unexpected error occurred'); }
    finally { setLoading(false); }
  };

  return (
    <AuthShell tag="MARKETINTEL" title="Welcome back" subtitle="Sign in to your account">
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {error && <Alert type="error">{error}</Alert>}

        <Field label="Email" htmlFor="email" required>
          <Input id="email" name="email" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@company.com" required autoComplete="email" />
        </Field>

        <Field label="Password" htmlFor="password" required>
          <div style={{ position: 'relative' }}>
            <Input id="password" name="password" type={showPw ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" required autoComplete="current-password" style={{ paddingRight: '44px' }} />
            <button type="button" onClick={() => setShowPw(v => !v)} style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#606080', padding: 0 }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d={showPw ? 'M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24M1 1l22 22' : 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z'} />{!showPw && <circle cx="12" cy="12" r="3" />}</svg>
            </button>
          </div>
        </Field>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '-8px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input type="checkbox" style={{ accentColor: '#F59E0B' }} />
            <span style={{ fontSize: '12px', color: '#9090B8' }}>Remember me</span>
          </label>
          <Link href="/auth/forgot-password" style={{ fontSize: '12px', color: '#F59E0B', textDecoration: 'none', fontFamily: 'IBM Plex Mono, monospace' }}>FORGOT?</Link>
        </div>

        <Btn type="submit" variant="primary" size="lg" loading={loading} style={{ width: '100%', marginTop: '4px' }}>Sign in</Btn>

        <Divider label="NEW HERE?" />

        <Link href="/auth/signup" style={{ display: 'block', textAlign: 'center', fontSize: '13px', color: '#9090B8', textDecoration: 'none' }}>
          Create an account — <span style={{ color: '#F59E0B' }}>Start free trial</span>
        </Link>
      </form>
    </AuthShell>
  );
}
""")

w('pages/auth/signup.js', r"""
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../../context/AuthContext';
import { Btn, Input, Field, Alert, Divider, Badge } from '../../components/UI';

""" + AUTH_SHELL_OPEN + r"""
const PERKS = ['5 products monitored', '10 AI-powered matches', '1 price alert', 'Basic analytics'];

export default function Signup() {
  const [form, setForm] = useState({ fullName: '', email: '', password: '', confirmPassword: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { signup } = useAuth();

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault(); setError('');
    if (form.password !== form.confirmPassword) return setError('Passwords do not match');
    if (form.password.length < 8) return setError('Password must be at least 8 characters');
    setLoading(true);
    try {
      const r = await signup(form.email, form.password, form.fullName);
      if (r.success) router.push('/dashboard');
      else setError(r.error || 'Signup failed');
    } catch { setError('An unexpected error occurred'); }
    finally { setLoading(false); }
  };

  return (
    <AuthShell tag="FREE TRIAL" title="Start monitoring" subtitle="No credit card required">
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
        {error && <Alert type="error">{error}</Alert>}

        <Field label="Full name" htmlFor="fullName" required>
          <Input id="fullName" name="fullName" value={form.fullName} onChange={set('fullName')} placeholder="Jane Smith" required />
        </Field>
        <Field label="Email" htmlFor="email" required>
          <Input id="email" name="email" type="email" value={form.email} onChange={set('email')} placeholder="you@company.com" required autoComplete="email" />
        </Field>
        <Field label="Password" htmlFor="password" required hint="Minimum 8 characters">
          <Input id="password" name="password" type="password" value={form.password} onChange={set('password')} placeholder="••••••••" required autoComplete="new-password" />
        </Field>
        <Field label="Confirm password" htmlFor="confirmPassword" required>
          <Input id="confirmPassword" name="confirmPassword" type="password" value={form.confirmPassword} onChange={set('confirmPassword')} placeholder="••••••••" required autoComplete="new-password" />
        </Field>

        {/* Free plan perks */}
        <div style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: '8px', padding: '14px 16px' }}>
          <div style={{ fontSize: '10px', color: '#F59E0B', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '10px' }}>FREE PLAN INCLUDES</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {PERKS.map((p, i) => <Badge key={i} variant="amber">{p}</Badge>)}
          </div>
        </div>

        <Btn type="submit" variant="primary" size="lg" loading={loading} style={{ width: '100%' }}>Create account</Btn>

        <Divider label="ALREADY HAVE AN ACCOUNT?" />

        <Link href="/auth/login" style={{ display: 'block', textAlign: 'center', fontSize: '13px', color: '#F59E0B', textDecoration: 'none', fontFamily: 'IBM Plex Mono, monospace' }}>
          SIGN IN INSTEAD
        </Link>
      </form>
    </AuthShell>
  );
}
""")

w('pages/auth/forgot-password.js', r"""
import { useState } from 'react';
import Link from 'next/link';
import { Btn, Input, Field, Alert } from '../../components/UI';

""" + AUTH_SHELL_OPEN + r"""
export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault(); setLoading(true);
    await new Promise(r => setTimeout(r, 1000));
    setSent(true); setLoading(false);
  };

  return (
    <AuthShell tag="ACCOUNT RECOVERY" title="Reset password" subtitle={sent ? 'Check your inbox' : 'Enter your email to receive a reset link'}>
      {sent ? (
        <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto' }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2"><path d="M20 6L9 17l-5-5"/></svg>
          </div>
          <Alert type="success">Reset link sent to <strong>{email}</strong></Alert>
          <Link href="/auth/login" style={{ fontSize: '13px', color: '#F59E0B', textDecoration: 'none', fontFamily: 'IBM Plex Mono, monospace' }}>BACK TO SIGN IN</Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <Field label="Email" htmlFor="email" required hint="We'll send a one-time reset link">
            <Input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@company.com" required />
          </Field>
          <Btn type="submit" variant="primary" size="lg" loading={loading} style={{ width: '100%' }}>Send reset link</Btn>
          <Link href="/auth/login" style={{ display: 'block', textAlign: 'center', fontSize: '12px', color: '#606080', textDecoration: 'none', fontFamily: 'IBM Plex Mono, monospace' }}>BACK TO SIGN IN</Link>
        </form>
      )}
    </AuthShell>
  );
}
""")

w('pages/auth/reset-password.js', r"""
import { useState } from 'react';
import { useRouter } from 'next/router';
import { Btn, Input, Field, Alert } from '../../components/UI';

""" + AUTH_SHELL_OPEN + r"""
export default function ResetPassword() {
  const [form, setForm] = useState({ password: '', confirm: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e) => {
    e.preventDefault(); setError('');
    if (form.password !== form.confirm) return setError('Passwords do not match');
    if (form.password.length < 8) return setError('Password must be at least 8 characters');
    setLoading(true);
    await new Promise(r => setTimeout(r, 1000));
    setDone(true); setLoading(false);
    setTimeout(() => router.push('/auth/login'), 2000);
  };

  return (
    <AuthShell tag="NEW PASSWORD" title="Set new password" subtitle="Choose a strong password">
      {done ? (
        <Alert type="success">Password updated! Redirecting to sign in...</Alert>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {error && <Alert type="error">{error}</Alert>}
          <Field label="New password" htmlFor="password" required hint="Minimum 8 characters">
            <Input id="password" type="password" value={form.password} onChange={e => setForm(f => ({...f, password: e.target.value}))} placeholder="••••••••" required />
          </Field>
          <Field label="Confirm password" htmlFor="confirm" required>
            <Input id="confirm" type="password" value={form.confirm} onChange={e => setForm(f => ({...f, confirm: e.target.value}))} placeholder="••••••••" required />
          </Field>
          <Btn type="submit" variant="primary" size="lg" loading={loading} style={{ width: '100%' }}>Update password</Btn>
        </form>
      )}
    </AuthShell>
  );
}
""")

print("Auth pages done.")

# =========================================================
# PRODUCTS
# =========================================================

w('pages/products/index.js', r"""
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import DataTable from '../../components/DataTable';
import { ConfirmModal } from '../../components/Modal';
import { useToast } from '../../components/Toast';
import { SkeletonTable } from '../../components/LoadingStates';
import { Btn, Badge, Alert, PageHeader, StatCard } from '../../components/UI';
import api from '../../lib/api';

export default function ProductsPage() {
  const router = useRouter();
  const { addToast } = useToast();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleteModal, setDeleteModal] = useState({ isOpen: false, product: null });

  useEffect(() => { loadProducts(); }, []);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const data = await api.getProducts();
      setProducts(data); setError(null);
    } catch { setError('Failed to load products. Make sure the backend is running.'); }
    finally { setLoading(false); }
  };

  const handleDelete = async () => {
    try {
      await api.deleteProduct(deleteModal.product.id);
      setProducts(p => p.filter(x => x.id !== deleteModal.product.id));
      addToast('Product deleted', 'success');
    } catch { addToast('Failed to delete product', 'error'); }
  };

  const columns = [
    {
      header: 'Product', accessor: r => r.title, sortable: true,
      render: r => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {r.image_url && <img src={r.image_url} alt="" style={{ width: '36px', height: '36px', borderRadius: '6px', objectFit: 'cover', background: '#1E1E2E' }} onError={e => e.target.style.display='none'} />}
          <div>
            <Link href={`/products/${r.id}`} style={{ fontWeight: 500, color: '#F59E0B', textDecoration: 'none', fontSize: '13px' }}>{r.title}</Link>
            {r.brand && <div style={{ fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace', marginTop: '2px' }}>{r.brand}</div>}
          </div>
        </div>
      )
    },
    { header: 'SKU', accessor: r => r.sku || '—', sortable: true, render: r => <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '12px', color: '#9090B8' }}>{r.sku || '—'}</span> },
    {
      header: 'Matches', accessor: r => r.competitor_count || 0, sortable: true,
      render: r => <Badge variant={(r.competitor_count||0) > 0 ? 'success' : 'neutral'}>{r.competitor_count||0} matches</Badge>
    },
    { header: 'Added', accessor: r => new Date(r.created_at).toLocaleDateString(), sortable: true, render: r => <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '11px', color: '#9090B8' }}>{new Date(r.created_at).toLocaleDateString()}</span> },
    {
      header: 'Actions', accessor: r => r.id, sortable: false,
      render: r => (
        <div style={{ display: 'flex', gap: '8px' }}>
          <Btn variant="ghost" size="sm" onClick={() => router.push(`/products/${r.id}`)}>View</Btn>
          <Btn variant="danger" size="sm" onClick={() => setDeleteModal({ isOpen: true, product: r })}>Delete</Btn>
        </div>
      )
    },
  ];

  const totalMatches = products.reduce((s, p) => s + (p.competitor_count||0), 0);
  const avgMatches = products.length ? (totalMatches / products.length).toFixed(1) : '0.0';

  return (
    <Layout>
      <PageHeader
        tag="MONITORING"
        title="Products"
        subtitle="Track your catalog across competitor websites"
        action={<Link href="/products/add" style={{ textDecoration: 'none' }}><Btn variant="primary" size="md">+ Add Product</Btn></Link>}
      />

      {error ? (
        <Alert type="error">{error}</Alert>
      ) : loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '16px' }}>
            {[0,1,2].map(i => <div key={i} style={{ background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px', height: '100px', animation: 'skel-pulse 1.6s ease-in-out infinite', backgroundSize: '200% 100%', background: 'linear-gradient(90deg,#16161E 25%,#1E1E2E 50%,#16161E 75%)' }} />)}
          </div>
          <SkeletonTable rows={5} />
          <style jsx global>{`@keyframes skel-pulse{0%,100%{background-position:200% 0}50%{background-position:-200% 0}}`}</style>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '16px' }}>
            <StatCard label="Total Products"       value={products.length} color="#F59E0B" />
            <StatCard label="Total Matches"        value={totalMatches}    color="#10B981" />
            <StatCard label="Avg Matches/Product"  value={avgMatches}      color="#818CF8" />
          </div>

          {products.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '64px', background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px' }}>
              <div style={{ fontSize: '10px', color: '#3A3A58', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.12em', marginBottom: '12px' }}>NO PRODUCTS YET</div>
              <h3 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '22px', color: '#F0F0FA', marginBottom: '8px' }}>Add your first product</h3>
              <p style={{ color: '#9090B8', fontSize: '14px', marginBottom: '24px', maxWidth: '360px', margin: '0 auto 24px' }}>Start monitoring competitor prices by adding a product to your catalog.</p>
              <Link href="/products/add" style={{ textDecoration: 'none' }}><Btn variant="primary" size="lg">+ Add First Product</Btn></Link>
            </div>
          ) : (
            <DataTable columns={columns} data={products} searchable sortable pagination pageSize={10} emptyMessage="No products match your search" />
          )}
        </div>
      )}

      <ConfirmModal isOpen={deleteModal.isOpen} onClose={() => setDeleteModal({ isOpen: false, product: null })} onConfirm={handleDelete}
        title="Delete Product" message={`Delete "${deleteModal.product?.title}"? This will remove all competitor matches and price history.`}
        confirmText="Delete" type="danger" />
    </Layout>
  );
}
""")

w('pages/products/add.js', r"""
import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { Btn, Input, Field, Alert, PageHeader, Card } from '../../components/UI';
import api from '../../lib/api';

export default function AddProductPage() {
  const router = useRouter();
  const [form, setForm] = useState({ title: '', brand: '', sku: '', image_url: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault(); setLoading(true); setError(null);
    try {
      const product = await api.createProduct(form);
      router.push(`/products/${product.id}`);
    } catch (err) { setError(err.message || 'Failed to create product'); setLoading(false); }
  };

  return (
    <Layout>
      <PageHeader tag="PRODUCTS" title="Add New Product" subtitle="Define what to monitor across competitor websites" />

      <div style={{ maxWidth: '680px' }}>
        {error && <div style={{ marginBottom: '20px' }}><Alert type="error">{error}</Alert></div>}

        <Card padding="32px">
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <Field label="Product Title" htmlFor="title" required hint="The full product name used for competitor matching">
              <Input id="title" name="title" value={form.title} onChange={set('title')} placeholder="e.g. Sony WH-1000XM5 Wireless Headphones" required />
            </Field>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <Field label="Brand" htmlFor="brand">
                <Input id="brand" name="brand" value={form.brand} onChange={set('brand')} placeholder="e.g. Sony" />
              </Field>
              <Field label="SKU / Product Code" htmlFor="sku">
                <Input id="sku" name="sku" value={form.sku} onChange={set('sku')} placeholder="e.g. WH1000XM5-B" monospace />
              </Field>
            </div>
            <Field label="Image URL" htmlFor="image_url" hint="Optional product image URL for visual reference">
              <Input id="image_url" name="image_url" type="url" value={form.image_url} onChange={set('image_url')} placeholder="https://example.com/image.jpg" />
            </Field>

            {/* What happens next */}
            <div style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: '8px', padding: '16px' }}>
              <div style={{ fontSize: '10px', color: '#F59E0B', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '10px' }}>WHAT HAPPENS NEXT</div>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {['Product added to monitoring list', 'Search for it on Amazon or custom competitors', 'Price changes tracked automatically', 'View competitor prices and history on product page'].map((t, i) => (
                  <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#9090B8' }}>
                    <span style={{ width: '16px', height: '16px', borderRadius: '50%', background: 'rgba(245,158,11,0.15)', color: '#F59E0B', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', flexShrink: 0, fontWeight: 700 }}>{i+1}</span>
                    {t}
                  </li>
                ))}
              </ul>
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', paddingTop: '8px', borderTop: '1px solid #1E1E2E' }}>
              <Btn variant="secondary" onClick={() => router.back()}>Cancel</Btn>
              <Btn type="submit" variant="primary" loading={loading}>Create Product</Btn>
            </div>
          </form>
        </Card>
      </div>
    </Layout>
  );
}
""")

print("Products pages done.")

# =========================================================
# COMPETITORS
# =========================================================

w('pages/competitors/index.js', r"""
import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { useToast } from '../../components/Toast';
import { Btn, Badge, Alert, PageHeader, Card } from '../../components/UI';
import api from '../../lib/api';

const FILTERS = ['all', 'active', 'inactive'];

export default function CompetitorsPage() {
  const { addToast } = useToast();
  const [competitors, setCompetitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');

  useEffect(() => { loadCompetitors(); }, [filter]);

  const loadCompetitors = async () => {
    try {
      setLoading(true);
      const activeOnly = filter === 'active' ? true : filter === 'inactive' ? false : undefined;
      setCompetitors(await api.getCompetitors(activeOnly));
      setError(null);
    } catch { setError('Failed to load competitors.'); }
    finally { setLoading(false); }
  };

  const handleToggle = async (id, status) => {
    try {
      await api.toggleCompetitorStatus(id);
      setCompetitors(c => c.map(x => x.id === id ? {...x, is_active: !status} : x));
      addToast(`Competitor ${status ? 'deactivated' : 'activated'}`, 'success');
    } catch { addToast('Failed to update status', 'error'); }
  };

  const handleDelete = async (id, name) => {
    if (!confirm(`Delete "${name}"? This removes all associated data.`)) return;
    try {
      await api.deleteCompetitor(id);
      setCompetitors(c => c.filter(x => x.id !== id));
      addToast('Competitor deleted', 'success');
    } catch { addToast('Failed to delete', 'error'); }
  };

  return (
    <Layout>
      <PageHeader tag="COMPETITORS" title="Competitor Websites"
        subtitle="Manage scraped websites and CSS selectors"
        action={<Link href="/competitors/add" style={{ textDecoration: 'none' }}><Btn variant="primary">+ Add Competitor</Btn></Link>}
      />

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: '0', borderBottom: '1px solid #1E1E2E', marginBottom: '24px' }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: '10px 18px', background: 'none', border: 'none', cursor: 'pointer',
            fontFamily: 'IBM Plex Mono, monospace', fontSize: '11px', letterSpacing: '0.08em',
            color: filter === f ? '#F59E0B' : '#606080', textTransform: 'uppercase',
            borderBottom: filter === f ? '2px solid #F59E0B' : '2px solid transparent',
            transition: 'color 0.15s',
          }}>{f} {f === 'all' ? `(${competitors.length})` : ''}</button>
        ))}
      </div>

      {error ? <Alert type="error">{error}</Alert> : loading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: '16px' }}>
          {[0,1,2].map(i => <div key={i} style={{ height: '220px', borderRadius: '10px', animation: 'skel-pulse 1.6s ease-in-out infinite', background: 'linear-gradient(90deg,#16161E 25%,#1E1E2E 50%,#16161E 75%)', backgroundSize: '200% 100%' }} />)}
          <style jsx global>{`@keyframes skel-pulse{0%,100%{background-position:200% 0}50%{background-position:-200% 0}}`}</style>
        </div>
      ) : competitors.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '64px', background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px' }}>
          <div style={{ fontSize: '10px', color: '#3A3A58', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.12em', marginBottom: '12px' }}>NO COMPETITORS</div>
          <h3 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '22px', color: '#F0F0FA', marginBottom: '8px' }}>Add your first competitor</h3>
          <p style={{ color: '#9090B8', fontSize: '14px', marginBottom: '24px', maxWidth: '360px', margin: '0 auto 24px' }}>Configure any website to scrape using CSS selectors.</p>
          <Link href="/competitors/add" style={{ textDecoration: 'none' }}><Btn variant="primary" size="lg">+ Add Competitor</Btn></Link>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: '16px' }}>
          {competitors.map(c => (
            <Card key={c.id} padding="0" hover>
              <div style={{ padding: '20px 20px 16px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <h3 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: '#F0F0FA', margin: 0, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.name}</h3>
                  <Badge variant={c.is_active ? 'success' : 'neutral'}>{c.is_active ? 'ACTIVE' : 'OFF'}</Badge>
                </div>
                <a href={c.base_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '11px', color: '#F59E0B', fontFamily: 'IBM Plex Mono, monospace', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: '12px', textDecoration: 'none' }}>{c.base_url}</a>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                  <Badge variant="neutral">{c.website_type || 'custom'}</Badge>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {[['Price', c.price_selector], ['Title', c.title_selector]].map(([label, sel]) => (
                    <div key={label} style={{ fontSize: '11px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <span style={{ color: '#606080', fontFamily: 'IBM Plex Mono, monospace', flexShrink: 0 }}>{label}:</span>
                      <code style={{ color: '#9090B8', background: '#1E1E2E', padding: '1px 6px', borderRadius: '4px', fontSize: '10px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{sel || 'not set'}</code>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ borderTop: '1px solid #1E1E2E', padding: '12px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Btn variant="ghost" size="sm" onClick={() => handleToggle(c.id, c.is_active)}>{c.is_active ? 'Deactivate' : 'Activate'}</Btn>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <Btn variant="ghost" size="sm">Edit</Btn>
                  <Btn variant="danger" size="sm" onClick={() => handleDelete(c.id, c.name)}>Delete</Btn>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </Layout>
  );
}
""")

w('pages/competitors/add.js', r"""
import { useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import { Btn, Input, Textarea, Select, Field, Alert, PageHeader, Card } from '../../components/UI';
import api from '../../lib/api';

const SELECTOR_FIELDS = [
  { key: 'price_selector',  label: 'Price Selector',        placeholder: '.price, .a-price-whole, #product-price' },
  { key: 'title_selector',  label: 'Title Selector',        placeholder: 'h1.product-title, #productTitle' },
  { key: 'stock_selector',  label: 'Stock Status Selector', placeholder: '.stock-status, #availability' },
  { key: 'image_selector',  label: 'Image Selector',        placeholder: 'img.product-image, #landingImage' },
];

export default function AddCompetitorPage() {
  const router = useRouter();
  const [form, setForm] = useState({ name: '', base_url: '', website_type: 'custom', price_selector: '', title_selector: '', stock_selector: '', image_selector: '', notes: '' });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault(); setSubmitting(true); setError(null);
    if (!form.name || !form.base_url) { setError('Name and Base URL are required'); setSubmitting(false); return; }
    try {
      await api.createCompetitor(form);
      router.push('/competitors');
    } catch (err) { setError(err.message || 'Failed to create competitor'); setSubmitting(false); }
  };

  return (
    <Layout>
      <PageHeader tag="COMPETITORS" title="Add Competitor Website" subtitle="Configure CSS selectors for data extraction from any site" />

      <div style={{ maxWidth: '720px' }}>
        {error && <div style={{ marginBottom: '20px' }}><Alert type="error">{error}</Alert></div>}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <Card padding="28px">
            <div style={{ fontSize: '11px', color: '#F59E0B', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '20px' }}>BASIC INFORMATION</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px' }}>
                <Field label="Competitor Name" htmlFor="name" required hint="A friendly label for this competitor">
                  <Input id="name" name="name" value={form.name} onChange={set('name')} placeholder="CompetitorStore" required />
                </Field>
                <Field label="Website Type" htmlFor="website_type">
                  <Select id="website_type" name="website_type" value={form.website_type} onChange={set('website_type')}>
                    <option value="custom">Custom</option>
                    <option value="ecommerce">E-commerce</option>
                    <option value="marketplace">Marketplace</option>
                    <option value="retail">Retail</option>
                  </Select>
                </Field>
              </div>
              <Field label="Base URL" htmlFor="base_url" required hint="Must start with https://">
                <Input id="base_url" name="base_url" type="url" value={form.base_url} onChange={set('base_url')} placeholder="https://www.competitor.com" required />
              </Field>
            </div>
          </Card>

          <Card padding="28px">
            <div style={{ fontSize: '11px', color: '#F59E0B', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '4px' }}>CSS SELECTORS</div>
            <p style={{ fontSize: '12px', color: '#9090B8', marginBottom: '20px' }}>Right-click any element on the competitor site → Inspect → Copy selector</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {SELECTOR_FIELDS.map(sf => (
                <Field key={sf.key} label={sf.label} htmlFor={sf.key}>
                  <Input id={sf.key} name={sf.key} value={form[sf.key]} onChange={set(sf.key)} placeholder={sf.placeholder} monospace />
                </Field>
              ))}
            </div>
            <div style={{ marginTop: '20px', background: 'rgba(129,140,248,0.06)', border: '1px solid rgba(129,140,248,0.2)', borderRadius: '8px', padding: '14px 16px' }}>
              <div style={{ fontSize: '10px', color: '#818CF8', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '8px' }}>HOW TO FIND SELECTORS</div>
              {['Open competitor product page in Chrome', 'Right-click the price/title element → Inspect', 'In DevTools, right-click the HTML → Copy → Copy selector', 'Paste the selector above'].map((s, i) => (
                <div key={i} style={{ display: 'flex', gap: '8px', fontSize: '12px', color: '#9090B8', marginBottom: '4px' }}>
                  <span style={{ color: '#818CF8', fontFamily: 'IBM Plex Mono, monospace', flexShrink: 0 }}>{i+1}.</span>{s}
                </div>
              ))}
            </div>
          </Card>

          <Card padding="28px">
            <Field label="Notes (optional)" htmlFor="notes">
              <Textarea id="notes" name="notes" value={form.notes} onChange={set('notes')} placeholder="Any additional context about this competitor..." rows={3} />
            </Field>
          </Card>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
            <Btn variant="secondary" onClick={() => router.push('/competitors')}>Cancel</Btn>
            <Btn type="submit" variant="primary" loading={submitting}>Create Competitor</Btn>
          </div>
        </form>
      </div>
    </Layout>
  );
}
""")

print("Competitors pages done.")

# =========================================================
# PRICING PAGE
# =========================================================

w('pages/pricing.js', r"""
import { useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Btn, Badge, PageHeader, Card } from '../components/UI';

const PLANS = [
  { name: 'Free', price: { monthly: 0, yearly: 0 }, priceId: {}, description: 'Try MarketIntel risk-free', cta: 'Get Started', popular: false, color: '#9090B8',
    features: ['5 products', '10 AI matches', '1 price alert', 'Basic analytics', '7-day history'] },
  { name: 'Pro', price: { monthly: 49, yearly: 490 }, description: 'For individuals & small teams', cta: 'Start Free Trial', popular: true, color: '#F59E0B',
    priceId: { monthly: 'price_pro_monthly', yearly: 'price_pro_yearly' },
    features: ['50 products', '100 AI matches', '10 alerts', 'Advanced analytics', 'Priority support', '30-day history', 'API (1k calls/mo)', 'CSV export', 'Custom schedules'] },
  { name: 'Business', price: { monthly: 149, yearly: 1490 }, description: 'For growing businesses', cta: 'Start Free Trial', popular: false, color: '#818CF8',
    priceId: { monthly: 'price_biz_monthly', yearly: 'price_biz_yearly' },
    features: ['200 products', '500 AI matches', '50 alerts', 'Advanced analytics + BI', 'Slack support', '90-day history', 'API (10k calls/mo)', 'Team workspace (5)', 'White-label reports', 'Custom integrations'] },
  { name: 'Enterprise', price: { monthly: 499, yearly: 4990 }, description: 'For large organizations', cta: 'Contact Sales', popular: false, color: '#34D399',
    priceId: {},
    features: ['Unlimited products', 'Unlimited matches', 'Unlimited alerts', 'Enterprise BI', '24/7 support + SLA', 'Unlimited history', 'Unlimited API', 'Unlimited team', 'SSO / SAML', 'Dedicated infra', 'Custom dev'] },
];

const FAQ = [
  ['Can I change plans?', 'Yes — upgrade or downgrade anytime. Changes take effect immediately.'],
  ['Is there a free trial?', 'All paid plans include a 14-day free trial. No credit card required.'],
  ['What payment methods?', 'All major credit/debit cards. ACH available for Enterprise plans.'],
  ['Can I cancel anytime?', 'Yes. You keep access until the end of your billing period.'],
];

export default function Pricing() {
  const [period, setPeriod] = useState('monthly');
  const [loadingPlan, setLoadingPlan] = useState(null);
  const { user, isAuthenticated } = useAuth();
  const router = useRouter();

  const handleSubscribe = async (plan) => {
    if (plan.name === 'Free') return router.push('/auth/signup');
    if (plan.name === 'Enterprise') return window.location.href = 'mailto:sales@marketintel.com?subject=Enterprise Plan';
    if (!isAuthenticated) return router.push(`/auth/signup?plan=${plan.name.toLowerCase()}`);
    setLoadingPlan(plan.name);
    try {
      const priceId = period === 'yearly' ? plan.priceId.yearly : plan.priceId.monthly;
      const res = await fetch('http://localhost:8000/api/billing/create-checkout-session', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('accessToken')}` },
        body: JSON.stringify({ price_id: priceId, success_url: `${window.location.origin}/dashboard?success=true`, cancel_url: `${window.location.origin}/pricing` }),
      });
      const data = await res.json();
      if (res.ok) window.location.href = data.url;
      else alert('Checkout error: ' + (data.detail || 'Unknown'));
    } catch { alert('Failed to start checkout'); }
    finally { setLoadingPlan(null); }
  };

  return (
    <Layout>
      <PageHeader tag="BILLING" title="Simple, transparent pricing" subtitle="Choose the plan that fits your monitoring needs" />

      {/* Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '40px' }}>
        <span style={{ fontSize: '13px', color: period === 'monthly' ? '#F0F0FA' : '#606080', fontFamily: 'IBM Plex Mono, monospace' }}>MONTHLY</span>
        <button onClick={() => setPeriod(p => p === 'monthly' ? 'yearly' : 'monthly')} style={{
          width: '44px', height: '24px', borderRadius: '12px', border: 'none', cursor: 'pointer', position: 'relative',
          background: period === 'yearly' ? '#F59E0B' : '#2A2A3E', transition: 'background 0.2s',
        }}>
          <span style={{ position: 'absolute', top: '3px', left: period === 'yearly' ? '23px' : '3px', width: '18px', height: '18px', borderRadius: '50%', background: period === 'yearly' ? '#0A0A0F' : '#606080', transition: 'left 0.2s' }} />
        </button>
        <span style={{ fontSize: '13px', color: period === 'yearly' ? '#F0F0FA' : '#606080', fontFamily: 'IBM Plex Mono, monospace', display: 'flex', alignItems: 'center', gap: '8px' }}>
          YEARLY <Badge variant="success">SAVE 17%</Badge>
        </span>
      </div>

      {/* Plans */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: '16px', marginBottom: '64px' }}>
        {PLANS.map(plan => (
          <div key={plan.name} style={{
            background: '#111118', border: `1px solid ${plan.popular ? 'rgba(245,158,11,0.4)' : '#1E1E2E'}`,
            borderRadius: '12px', padding: '28px', position: 'relative',
            boxShadow: plan.popular ? '0 0 40px rgba(245,158,11,0.1)' : 'none',
          }}>
            {plan.popular && <div style={{ position: 'absolute', top: '-10px', left: '50%', transform: 'translateX(-50%)', background: '#F59E0B', color: '#0A0A0F', fontSize: '10px', fontFamily: 'Syne, sans-serif', fontWeight: 700, letterSpacing: '0.08em', padding: '3px 12px', borderRadius: '20px', whiteSpace: 'nowrap' }}>MOST POPULAR</div>}

            <div style={{ fontSize: '10px', color: plan.color, fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '8px' }}>{plan.name.toUpperCase()}</div>
            <p style={{ fontSize: '13px', color: '#9090B8', marginBottom: '20px', lineHeight: 1.5 }}>{plan.description}</p>

            <div style={{ marginBottom: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontWeight: 700, fontSize: '36px', color: '#F0F0FA' }}>${plan.price[period]}</span>
                {plan.price[period] > 0 && <span style={{ fontSize: '12px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace' }}>/{period === 'yearly' ? 'yr' : 'mo'}</span>}
              </div>
              {period === 'yearly' && plan.price.yearly > 0 && (
                <div style={{ fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace', marginTop: '4px' }}>${(plan.price.yearly/12).toFixed(0)}/mo billed annually</div>
              )}
            </div>

            <Btn variant={plan.popular ? 'primary' : 'secondary'} size="md" loading={loadingPlan === plan.name} onClick={() => handleSubscribe(plan)} style={{ width: '100%', marginBottom: '24px' }}>{plan.cta}</Btn>

            <div style={{ borderTop: '1px solid #1E1E2E', paddingTop: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {plan.features.map((f, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#9090B8' }}>
                  <span style={{ color: plan.color, flexShrink: 0 }}>✓</span>{f}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* FAQ */}
      <div>
        <div style={{ fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '20px' }}>FREQUENTLY ASKED QUESTIONS</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: '16px' }}>
          {FAQ.map(([q, a], i) => (
            <Card key={i} padding="20px" hover>
              <h4 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 600, fontSize: '14px', color: '#F0F0FA', marginBottom: '8px' }}>{q}</h4>
              <p style={{ fontSize: '13px', color: '#9090B8', lineHeight: 1.6, margin: 0 }}>{a}</p>
            </Card>
          ))}
        </div>
      </div>
    </Layout>
  );
}
""")

print("Pricing done.")

# =========================================================
# SCHEDULER
# =========================================================

w('pages/scheduler/index.js', r"""
import { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import { useToast } from '../../components/Toast';
import { Spinner } from '../../components/LoadingStates';
import { Btn, Badge, Card, PageHeader, StatCard, Alert } from '../../components/UI';
import api from '../../lib/api';

const ACTIONS = [
  { id: 'all',      label: 'Scrape All Products',    desc: 'Queue all products for fresh price data',        color: '#F59E0B', icon: '▶' },
  { id: 'priority', label: 'Priority Scrape',        desc: 'High-priority queue — runs ahead of others',    color: '#10B981', icon: '⚡' },
  { id: 'analytics',label: 'Update Analytics',       desc: 'Recalculate trends, forecasts & insights',      color: '#818CF8', icon: '~' },
  { id: 'discovery',label: 'Run Discovery',          desc: 'Find new competitor products automatically',     color: '#F472B6', icon: '+' },
];

export default function SchedulerPage() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState({});
  const [queueStats, setQueueStats] = useState(null);
  const [activeTasks, setActiveTasks] = useState([]);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 5000);
    return () => clearInterval(iv);
  }, []);

  const refresh = async () => {
    try {
      const [stats, tasks] = await Promise.all([
        api.request('/api/scheduler/queue/stats').catch(() => null),
        api.request('/api/scheduler/tasks/active').catch(() => ({ active_tasks: [] })),
      ]);
      if (stats) setQueueStats(stats);
      setActiveTasks(tasks?.active_tasks || []);
    } catch {}
  };

  const trigger = async (id) => {
    setLoading(l => ({ ...l, [id]: true }));
    const endpoints = {
      all: ['/api/scheduler/scrape/all', {}],
      priority: ['/api/scheduler/scrape/all', { body: JSON.stringify({ priority: true }) }],
      analytics: ['/api/scheduler/analytics/update', {}],
      discovery: ['/api/scheduler/discovery/run', {}],
    };
    try {
      const [url, opts] = endpoints[id];
      const result = await api.request(url, { method: 'POST', ...opts });
      addToast(`Task started! ID: ${result?.task_id || 'queued'}`, 'success');
      setHistory(h => [{ id, label: ACTIONS.find(a => a.id === id)?.label, time: new Date().toLocaleTimeString(), taskId: result?.task_id }, ...h.slice(0, 9)]);
      setTimeout(refresh, 1000);
    } catch { addToast(`Failed to start ${id} task`, 'error'); }
    finally { setLoading(l => ({ ...l, [id]: false })); }
  };

  return (
    <Layout>
      <PageHeader tag="AUTOMATION" title="Task Scheduler" subtitle="Manage scraping jobs, analytics updates, and discovery runs" />

      {/* Queue Stats */}
      {queueStats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '16px', marginBottom: '28px' }}>
          <StatCard label="Pending"    value={queueStats.pending || 0}  color="#F59E0B" />
          <StatCard label="Active"     value={queueStats.active || 0}   color="#10B981" />
          <StatCard label="Completed"  value={queueStats.completed || 0} color="#818CF8" />
          <StatCard label="Failed"     value={queueStats.failed || 0}   color="#EF4444" />
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '24px' }}>
        {/* Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '4px' }}>AVAILABLE ACTIONS</div>
          {ACTIONS.map(action => (
            <Card key={action.id} padding="20px" hover>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: `${action.color}18`, border: `1px solid ${action.color}33`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', color: action.color, flexShrink: 0 }}>{action.icon}</div>
                  <div>
                    <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 600, fontSize: '14px', color: '#F0F0FA', marginBottom: '2px' }}>{action.label}</div>
                    <div style={{ fontSize: '12px', color: '#9090B8' }}>{action.desc}</div>
                  </div>
                </div>
                <Btn variant="outline" size="sm" loading={loading[action.id]} onClick={() => trigger(action.id)}>Run</Btn>
              </div>
            </Card>
          ))}
        </div>

        {/* Sidebar: active + history */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <Card padding="20px">
            <div style={{ fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              ACTIVE TASKS
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: activeTasks.length ? '#10B981' : '#3A3A58', display: 'inline-block', animation: activeTasks.length ? 'mi-pulse 2s ease-in-out infinite' : 'none' }} />
            </div>
            {activeTasks.length === 0 ? (
              <div style={{ fontSize: '12px', color: '#3A3A58', fontFamily: 'IBM Plex Mono, monospace', textAlign: 'center', padding: '16px 0' }}>NO ACTIVE TASKS</div>
            ) : activeTasks.map((t, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 0', borderBottom: i < activeTasks.length-1 ? '1px solid #1E1E2E' : 'none' }}>
                <Spinner size={14} />
                <span style={{ fontSize: '12px', color: '#9090B8', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.name || t.id}</span>
              </div>
            ))}
          </Card>

          <Card padding="20px">
            <div style={{ fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '16px' }}>RECENT RUNS</div>
            {history.length === 0 ? (
              <div style={{ fontSize: '12px', color: '#3A3A58', fontFamily: 'IBM Plex Mono, monospace', textAlign: 'center', padding: '16px 0' }}>NO HISTORY YET</div>
            ) : history.map((h, i) => (
              <div key={i} style={{ padding: '8px 0', borderBottom: i < history.length-1 ? '1px solid #1E1E2E' : 'none' }}>
                <div style={{ fontSize: '12px', color: '#F0F0FA', marginBottom: '2px' }}>{h.label}</div>
                <div style={{ fontSize: '10px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace' }}>{h.time}</div>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </Layout>
  );
}
""")

print("Scheduler done.")

# =========================================================
# INTEGRATIONS
# =========================================================

w('pages/integrations/index.js', r"""
import { useState } from 'react';
import Layout from '../../components/Layout';
import ImportWizard from '../../components/ImportWizard';
import Modal from '../../components/Modal';
import { Btn, Badge, Card, PageHeader } from '../../components/UI';

const INTEGRATIONS = [
  { id: 'xml',        name: 'XML Feed',        color: '#F59E0B', status: 'available', desc: 'Upload a product catalog XML file. Supports Google Shopping Feed, WooCommerce exports, and custom formats.',
    features: ['Auto-detect format', 'Google Shopping Feed', 'WooCommerce XML', 'Custom formats'], icon: '{ }' },
  { id: 'woocommerce',name: 'WooCommerce',     color: '#818CF8', status: 'available', desc: 'Connect via REST API. Automatically sync all published products from your WooCommerce store.',
    features: ['Direct API', 'Bulk import', 'Category filter', 'Sync status'], icon: 'WC' },
  { id: 'shopify',    name: 'Shopify',         color: '#10B981', status: 'available', desc: 'Import products, variants, and collections using your Shopify Admin API token.',
    features: ['Admin API', 'All products', 'Variant support', 'Collection filter'], icon: 'SH' },
  { id: 'amazon',     name: 'Amazon SP-API',   color: '#F472B6', status: 'soon', desc: 'Direct product catalog sync from Seller Central via the Selling Partner API.',
    features: ['Catalog sync', 'ASIN lookup', 'Price history', 'FBA data'], icon: 'AMZ' },
  { id: 'google',     name: 'Google Shopping', color: '#38BDF8', status: 'soon', desc: 'Import your Google Merchant Center product feed for instant competitor analysis.',
    features: ['Merchant Center', 'Feed import', 'Auto-match', 'PLA insights'], icon: 'G' },
  { id: 'csv',        name: 'CSV / Excel',     color: '#34D399', status: 'available', desc: 'Bulk import products from any spreadsheet. Maps columns automatically.',
    features: ['Column mapping', 'Bulk upload', 'Dedup logic', 'Preview before import'], icon: 'CSV' },
];

export default function IntegrationsPage() {
  const [showImport, setShowImport] = useState(false);

  return (
    <Layout>
      <PageHeader tag="DATA SOURCES" title="Integrations" subtitle="Import your product catalog from any e-commerce platform" />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: '16px' }}>
        {INTEGRATIONS.map(intg => (
          <Card key={intg.id} padding="0" hover>
            <div style={{ padding: '24px 24px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: `${intg.color}18`, border: `1px solid ${intg.color}33`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', fontFamily: 'IBM Plex Mono, monospace', fontWeight: 700, color: intg.color }}>
                    {intg.icon}
                  </div>
                  <div>
                    <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: '#F0F0FA' }}>{intg.name}</div>
                  </div>
                </div>
                <Badge variant={intg.status === 'available' ? 'success' : 'neutral'}>{intg.status === 'available' ? 'READY' : 'SOON'}</Badge>
              </div>
              <p style={{ fontSize: '13px', color: '#9090B8', lineHeight: 1.6, marginBottom: '16px' }}>{intg.desc}</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {intg.features.map((f, i) => (
                  <span key={i} style={{ fontSize: '10px', color: intg.color, fontFamily: 'IBM Plex Mono, monospace', background: `${intg.color}10`, border: `1px solid ${intg.color}22`, padding: '2px 8px', borderRadius: '4px' }}>{f}</span>
                ))}
              </div>
            </div>
            <div style={{ borderTop: '1px solid #1E1E2E', padding: '14px 24px' }}>
              {intg.status === 'available' ? (
                <Btn variant="outline" size="sm" onClick={() => setShowImport(true)} style={{ width: '100%' }}>
                  Connect {intg.name}
                </Btn>
              ) : (
                <Btn variant="ghost" size="sm" style={{ width: '100%', cursor: 'not-allowed' }} disabled>Coming soon</Btn>
              )}
            </div>
          </Card>
        ))}
      </div>

      <Modal isOpen={showImport} onClose={() => setShowImport(false)} title="Import Products" size="lg">
        <ImportWizard onComplete={() => setShowImport(false)} />
      </Modal>
    </Layout>
  );
}
""")

print("Integrations done.")

# =========================================================
# INSIGHTS
# =========================================================

w('pages/insights.js', r"""
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import { Btn, Badge, Card, PageHeader, StatCard, Alert } from '../components/UI';
import { SkeletonChart, SkeletonStats } from '../components/LoadingStates';
import { useAuth } from '../context/AuthContext';

const SEVERITY = {
  high:   { color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.25)',   badge: 'danger'  },
  medium: { color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.25)',  badge: 'amber'   },
  low:    { color: '#818CF8', bg: 'rgba(129,140,248,0.08)', border: 'rgba(129,140,248,0.25)', badge: 'purple'  },
};

export default function InsightsDashboard() {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated) { router.push('/auth/login'); return; }
    (async () => {
      try {
        const res = await fetch('http://localhost:8000/api/insights/dashboard', {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('accessToken')}` },
        });
        if (!res.ok) throw new Error('Failed to fetch insights');
        setInsights(await res.json());
      } catch (err) { setError(err.message); }
      finally { setLoading(false); }
    })();
  }, [isAuthenticated]);

  if (!isAuthenticated) return null;

  return (
    <Layout>
      <PageHeader tag="INTELLIGENCE" title="Insights Dashboard" subtitle="AI-powered recommendations and competitive analysis" />

      {error ? <Alert type="error">{error}</Alert> : loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <SkeletonStats />
          <SkeletonChart />
        </div>
      ) : insights ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
          {/* Summary Stats */}
          {insights.summary && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(180px,1fr))', gap: '16px' }}>
              {Object.entries(insights.summary).map(([key, val]) => (
                <StatCard key={key} label={key.replace(/_/g,' ')} value={typeof val === 'number' ? val.toLocaleString() : val} color="#F59E0B" />
              ))}
            </div>
          )}

          {/* Insights list */}
          {insights.insights && insights.insights.length > 0 && (
            <div>
              <div style={{ fontSize: '11px', color: '#606080', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.1em', marginBottom: '16px' }}>ACTIONABLE INSIGHTS</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {insights.insights.map((insight, i) => {
                  const s = SEVERITY[insight.severity] || SEVERITY.low;
                  return (
                    <Card key={i} padding="20px" hover>
                      <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                        <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: s.bg, border: `1px solid ${s.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, color: s.color, fontSize: '16px' }}>
                          {insight.severity === 'high' ? '!' : insight.severity === 'medium' ? '~' : 'i'}
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                            <h3 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 600, fontSize: '14px', color: '#F0F0FA', margin: 0 }}>{insight.title}</h3>
                            <Badge variant={s.badge}>{insight.severity}</Badge>
                          </div>
                          <p style={{ fontSize: '13px', color: '#9090B8', lineHeight: 1.6, margin: 0 }}>{insight.description}</p>
                          {insight.action && (
                            <div style={{ marginTop: '10px' }}>
                              <Btn variant="outline" size="sm">{insight.action}</Btn>
                            </div>
                          )}
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}

          {(!insights.insights || insights.insights.length === 0) && (
            <div style={{ textAlign: 'center', padding: '64px', background: '#111118', border: '1px solid #1E1E2E', borderRadius: '10px' }}>
              <div style={{ fontSize: '10px', color: '#3A3A58', fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.12em', marginBottom: '12px' }}>ALL CLEAR</div>
              <h3 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '22px', color: '#F0F0FA', marginBottom: '8px' }}>No insights yet</h3>
              <p style={{ color: '#9090B8', fontSize: '14px' }}>Add more products and run scrapes to generate AI-powered insights.</p>
            </div>
          )}
        </div>
      ) : null}
    </Layout>
  );
}
""")

print("Insights done.")
print("All pages written successfully!")
