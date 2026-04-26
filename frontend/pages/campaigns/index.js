import { useState, useEffect, useCallback } from 'react';
import Layout from '../../components/Layout';
import api from '../../lib/api';

const TEMPLATES = [
  { id: 'black_friday', label: 'Black Friday', emoji: '🛍️', discount: 20, color: '#f59e0b', bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.3)' },
  { id: 'flash_sale',   label: 'Flash Sale',   emoji: '⚡', discount: 15, color: '#06b6d4', bg: 'rgba(6,182,212,0.1)',  border: 'rgba(6,182,212,0.3)' },
  { id: 'clearance',    label: 'Clearance',    emoji: '📦', discount: 30, color: '#8b5cf6', bg: 'rgba(139,92,246,0.1)', border: 'rgba(139,92,246,0.3)' },
  { id: 'custom',       label: 'Custom',       emoji: '✏️', discount: 10, color: '#6b7280', bg: 'rgba(107,114,128,0.1)', border: 'rgba(107,114,128,0.3)' },
];

const STATUS_CONFIG = {
  scheduled: { label: 'Scheduled',  color: '#f59e0b', pulse: false },
  running:   { label: 'Live',       color: '#10b981', pulse: true  },
  completed: { label: 'Ended',      color: '#6b7280', pulse: false },
  paused:    { label: 'Paused',     color: '#f59e0b', pulse: false },
  cancelled: { label: 'Cancelled',  color: '#ef4444', pulse: false },
};

function pad2(n) { return String(n).padStart(2, '0'); }

function toLocalDateTimeInput(date) {
  const d = new Date(date);
  return `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

function defaultStartsAt() {
  const d = new Date(Date.now() + 60 * 60 * 1000);
  return toLocalDateTimeInput(d);
}

function defaultEndsAt() {
  const d = new Date(Date.now() + 25 * 60 * 60 * 1000);
  return toLocalDateTimeInput(d);
}

function timeUntil(dateStr) {
  const diff = new Date(dateStr) - Date.now();
  if (diff <= 0) return null;
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  if (h >= 48) return `${Math.floor(h / 24)}d`;
  if (h >= 1)  return `${h}h ${m}m`;
  return `${m}m`;
}

// ── Campaign card ─────────────────────────────────────────────────────────────

function CampaignCard({ campaign, onPause, onCancel, onDelete }) {
  const [acting, setActing] = useState(false);
  const cfg = STATUS_CONFIG[campaign.status] || STATUS_CONFIG.scheduled;
  const tmpl = TEMPLATES.find(t => t.id === campaign.template) || TEMPLATES[3];
  const untilStart = timeUntil(campaign.starts_at);
  const untilEnd = campaign.status === 'running' ? timeUntil(campaign.ends_at) : null;

  const act = async (fn) => {
    setActing(true);
    try { await fn(); } finally { setActing(false); }
  };

  return (
    <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: `1px solid ${tmpl.border}` }}>
      {/* Header */}
      <div className="flex items-start justify-between px-5 py-4" style={{ background: tmpl.bg, borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-3">
          <span className="text-xl">{tmpl.emoji}</span>
          <div>
            <p className="text-sm font-semibold text-white">{campaign.name}</p>
            {campaign.description && (
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{campaign.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {cfg.pulse && (
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ background: cfg.color }} />
              <span className="relative inline-flex rounded-full h-2 w-2" style={{ background: cfg.color }} />
            </span>
          )}
          <span className="text-xs font-medium px-2 py-0.5 rounded-full" style={{ background: `${cfg.color}22`, color: cfg.color }}>
            {cfg.label}
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="px-5 py-3 space-y-2">
        <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs" style={{ color: 'var(--text-muted)' }}>
          <span>
            {campaign.rules?.map(r => {
              if (r.type === 'discount_pct') return `−${r.value}%`;
              if (r.type === 'discount_fixed') return `−$${r.value}`;
              if (r.type === 'set_price') return `Set $${r.value}`;
              return '';
            }).join(' · ')}
          </span>
          <span>{campaign.products_affected > 0 ? `${campaign.products_affected} products` : 'All products'}</span>
          <span>
            {new Date(campaign.starts_at).toLocaleDateString()} → {new Date(campaign.ends_at).toLocaleDateString()}
          </span>
          {untilStart && campaign.status === 'scheduled' && (
            <span className="text-amber-400">Starts in {untilStart}</span>
          )}
          {untilEnd && (
            <span className="text-emerald-400">Ends in {untilEnd}</span>
          )}
        </div>
      </div>

      {/* Actions */}
      {(campaign.status === 'running' || campaign.status === 'scheduled' || campaign.status === 'paused') && (
        <div className="flex items-center gap-3 px-5 py-3" style={{ borderTop: '1px solid var(--border)' }}>
          {campaign.status === 'running' && (
            <button onClick={() => act(() => onPause(campaign.id))} disabled={acting}
              className="text-xs font-medium text-amber-400 hover:text-amber-300 disabled:opacity-50">
              {acting ? 'Pausing…' : 'Pause'}
            </button>
          )}
          <button onClick={() => act(() => onCancel(campaign.id))} disabled={acting}
            className="text-xs font-medium text-red-400/70 hover:text-red-400 disabled:opacity-50">
            {acting ? 'Cancelling…' : campaign.status === 'running' ? 'End now' : 'Cancel'}
          </button>
        </div>
      )}
      {(campaign.status === 'completed' || campaign.status === 'cancelled') && (
        <div className="flex items-center gap-3 px-5 py-3" style={{ borderTop: '1px solid var(--border)' }}>
          <button onClick={() => act(() => onDelete(campaign.id))} disabled={acting}
            className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {acting ? '…' : 'Remove'}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Create drawer ─────────────────────────────────────────────────────────────

function CreateDrawer({ open, onClose, onCreate }) {
  const [step, setStep] = useState(0); // 0=template, 1=details, 2=preview
  const [template, setTemplate] = useState(null);
  const [form, setForm] = useState({
    name: '', description: '',
    discount_type: 'discount_pct', discount_value: '20',
    filter_type: 'all', filter_value: '',
    starts_at: defaultStartsAt(),
    ends_at: defaultEndsAt(),
  });
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const reset = () => {
    setStep(0); setTemplate(null); setPreview(null); setError('');
    setForm({ name: '', description: '', discount_type: 'discount_pct', discount_value: '20',
              filter_type: 'all', filter_value: '', starts_at: defaultStartsAt(), ends_at: defaultEndsAt() });
  };

  const handleClose = () => { reset(); onClose(); };

  const pickTemplate = (tmpl) => {
    setTemplate(tmpl);
    setForm(f => ({
      ...f,
      name: f.name || tmpl.label,
      discount_value: String(tmpl.discount),
    }));
    setStep(1);
  };

  const buildPayload = () => {
    const rules = [{ type: form.discount_type, value: parseFloat(form.discount_value) }];
    let product_filter = null;
    if (form.filter_type === 'category' && form.filter_value.trim())
      product_filter = { category: form.filter_value.trim() };
    else if (form.filter_type === 'tags' && form.filter_value.trim())
      product_filter = { tags: form.filter_value.split(',').map(t => t.trim()).filter(Boolean) };
    else if (form.filter_type === 'skus' && form.filter_value.trim())
      product_filter = { skus: form.filter_value.split(',').map(s => s.trim()).filter(Boolean) };
    else
      product_filter = { all: true };
    return {
      name: form.name.trim() || template?.label || 'Campaign',
      description: form.description.trim() || null,
      template: template?.id !== 'custom' ? template?.id : null,
      starts_at: new Date(form.starts_at).toISOString(),
      ends_at: new Date(form.ends_at).toISOString(),
      rules,
      product_filter,
    };
  };

  const handlePreview = async () => {
    setPreviewLoading(true);
    setError('');
    try {
      // Create a temporary draft to preview (use the create + preview + delete pattern)
      const draft = await api.createCampaign({ ...buildPayload(), starts_at: new Date(Date.now() + 999999000).toISOString() });
      const p = await api.previewCampaign(draft.id);
      await api.deleteCampaign(draft.id);
      setPreview(p);
      setStep(2);
    } catch (e) {
      setError(e.message || 'Preview failed');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleCreate = async () => {
    setCreating(true);
    setError('');
    try {
      await onCreate(buildPayload());
      handleClose();
    } catch (e) {
      setError(e.message || 'Failed to create campaign');
      setCreating(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex" style={{ background: 'rgba(0,0,0,0.6)' }}>
      <div className="ml-auto h-full w-full max-w-md flex flex-col" style={{ background: 'var(--bg-surface)', borderLeft: '1px solid var(--border)' }}>
        {/* Drawer header */}
        <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
          <p className="text-sm font-semibold text-white">
            {step === 0 ? 'Choose a template' : step === 1 ? 'Campaign details' : 'Preview'}
          </p>
          <button onClick={handleClose} className="text-lg" style={{ color: 'var(--text-muted)' }}>×</button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {error && <p className="text-xs text-red-400 bg-red-400/10 rounded-lg px-3 py-2">{error}</p>}

          {/* Step 0 — Template picker */}
          {step === 0 && (
            <div className="grid grid-cols-2 gap-3">
              {TEMPLATES.map(t => (
                <button key={t.id} onClick={() => pickTemplate(t)}
                  className="rounded-xl p-4 text-left transition-all hover:scale-105"
                  style={{ background: t.bg, border: `1px solid ${t.border}` }}>
                  <div className="text-2xl mb-2">{t.emoji}</div>
                  <p className="text-sm font-semibold text-white">{t.label}</p>
                  {t.id !== 'custom' && (
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>−{t.discount}% off</p>
                  )}
                </button>
              ))}
            </div>
          )}

          {/* Step 1 — Details form */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-white block mb-1">Campaign name</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder={template?.label || 'My Campaign'}
                  className="w-full px-3 py-2 rounded-lg text-sm text-white"
                  style={{ background: 'var(--bg-input,#1a1a2e)', border: '1px solid var(--border)' }} />
              </div>

              <div>
                <label className="text-xs font-medium text-white block mb-1">Discount</label>
                <div className="flex gap-2">
                  <select value={form.discount_type} onChange={e => setForm(f => ({ ...f, discount_type: e.target.value }))}
                    className="px-3 py-2 rounded-lg text-sm text-white"
                    style={{ background: 'var(--bg-input,#1a1a2e)', border: '1px solid var(--border)' }}>
                    <option value="discount_pct">% off</option>
                    <option value="discount_fixed">$ off</option>
                    <option value="set_price">Set price to</option>
                  </select>
                  <input type="number" min="0" step="0.1" value={form.discount_value}
                    onChange={e => setForm(f => ({ ...f, discount_value: e.target.value }))}
                    className="flex-1 px-3 py-2 rounded-lg text-sm text-white"
                    style={{ background: 'var(--bg-input,#1a1a2e)', border: '1px solid var(--border)' }} />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-white block mb-1">Products</label>
                <select value={form.filter_type} onChange={e => setForm(f => ({ ...f, filter_type: e.target.value, filter_value: '' }))}
                  className="w-full px-3 py-2 rounded-lg text-sm text-white mb-2"
                  style={{ background: 'var(--bg-input,#1a1a2e)', border: '1px solid var(--border)' }}>
                  <option value="all">All active products</option>
                  <option value="category">By category</option>
                  <option value="tags">By tag(s)</option>
                  <option value="skus">By SKU list</option>
                </select>
                {form.filter_type !== 'all' && (
                  <input value={form.filter_value} onChange={e => setForm(f => ({ ...f, filter_value: e.target.value }))}
                    placeholder={form.filter_type === 'category' ? 'Electronics' : form.filter_type === 'tags' ? 'sale, clearance' : 'SKU-001, SKU-002'}
                    className="w-full px-3 py-2 rounded-lg text-sm text-white"
                    style={{ background: 'var(--bg-input,#1a1a2e)', border: '1px solid var(--border)' }} />
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-white block mb-1">Starts</label>
                  <input type="datetime-local" value={form.starts_at}
                    onChange={e => setForm(f => ({ ...f, starts_at: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg text-xs text-white"
                    style={{ background: 'var(--bg-input,#1a1a2e)', border: '1px solid var(--border)', colorScheme: 'dark' }} />
                </div>
                <div>
                  <label className="text-xs font-medium text-white block mb-1">Ends</label>
                  <input type="datetime-local" value={form.ends_at}
                    onChange={e => setForm(f => ({ ...f, ends_at: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg text-xs text-white"
                    style={{ background: 'var(--bg-input,#1a1a2e)', border: '1px solid var(--border)', colorScheme: 'dark' }} />
                </div>
              </div>
            </div>
          )}

          {/* Step 2 — Preview */}
          {step === 2 && preview && (
            <div>
              <div className="rounded-xl px-4 py-3 mb-4" style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
                <p className="text-sm font-semibold text-white">{preview.products_matched} products will be repriced</p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Sample of up to 20 shown below. Margin floor is respected — prices won't breach it.
                </p>
              </div>
              <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
                <table className="w-full">
                  <thead>
                    <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border)' }}>
                      <th className="px-3 py-2 text-left text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Product</th>
                      <th className="px-3 py-2 text-right text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Now</th>
                      <th className="px-3 py-2 text-right text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Sale</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.sample.map(p => (
                      <tr key={p.product_id} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td className="px-3 py-2 text-xs text-white truncate max-w-[160px]">
                          {p.title}
                          {p.floor_clamped && <span className="ml-1 text-amber-400" title="Clamped to floor">⌊</span>}
                        </td>
                        <td className="px-3 py-2 text-xs text-right" style={{ color: 'var(--text-muted)' }}>${p.current_price.toFixed(2)}</td>
                        <td className="px-3 py-2 text-xs text-right text-emerald-400 font-medium">${p.new_price.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 flex gap-3" style={{ borderTop: '1px solid var(--border)' }}>
          {step > 0 && (
            <button onClick={() => setStep(s => s - 1)}
              className="px-4 py-2 rounded-lg text-sm" style={{ background: 'var(--bg-input,#1a1a2e)', color: 'var(--text-muted)' }}>
              Back
            </button>
          )}
          {step === 1 && (
            <button onClick={handlePreview} disabled={previewLoading}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
              style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981', border: '1px solid rgba(16,185,129,0.3)' }}>
              {previewLoading ? 'Loading…' : 'Preview →'}
            </button>
          )}
          {step === 2 && (
            <button onClick={handleCreate} disabled={creating}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-semibold disabled:opacity-50"
              style={{ background: '#10b981', color: '#fff' }}>
              {creating ? 'Launching…' : 'Launch campaign'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDrawer, setShowDrawer] = useState(false);

  const loadCampaigns = useCallback(async () => {
    try {
      const data = await api.getCampaigns();
      setCampaigns(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadCampaigns(); }, [loadCampaigns]);

  const handleCreate = async (payload) => {
    const created = await api.createCampaign(payload);
    setCampaigns(cs => [created, ...cs]);
  };

  const handlePause = async (id) => {
    const updated = await api.pauseCampaign(id);
    setCampaigns(cs => cs.map(c => c.id === id ? updated : c));
  };

  const handleCancel = async (id) => {
    const updated = await api.cancelCampaign(id);
    setCampaigns(cs => cs.map(c => c.id === id ? updated : c));
  };

  const handleDelete = async (id) => {
    await api.deleteCampaign(id);
    setCampaigns(cs => cs.filter(c => c.id !== id));
  };

  const active = campaigns.filter(c => ['scheduled', 'running', 'paused'].includes(c.status));
  const past = campaigns.filter(c => ['completed', 'cancelled'].includes(c.status));

  return (
    <Layout>
      <CreateDrawer open={showDrawer} onClose={() => setShowDrawer(false)} onCreate={handleCreate} />

      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">Campaign Scheduler</h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Schedule bulk price events — Black Friday, flash sales, clearance. Prices auto-revert when the campaign ends.
            </p>
          </div>
          <button onClick={() => setShowDrawer(true)}
            className="px-4 py-2 rounded-lg text-sm font-semibold"
            style={{ background: '#10b981', color: '#fff' }}>
            + New campaign
          </button>
        </div>

        {/* Info banner */}
        <div className="rounded-xl p-4 mb-6 flex items-start gap-3" style={{ background: 'rgba(16,185,129,0.07)', border: '1px solid rgba(16,185,129,0.2)' }}>
          <svg className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            <span className="text-emerald-400 font-medium">How it works: </span>
            Campaign prices are pushed to your connected Shopify / WooCommerce store automatically. Margin floors are always respected —
            no product will be discounted below its cost floor. Prices revert exactly to their pre-campaign values when the campaign ends.
          </p>
        </div>

        {loading ? (
          <div className="text-center py-16 text-sm" style={{ color: 'var(--text-muted)' }}>Loading…</div>
        ) : (
          <>
            {/* Active campaigns */}
            {active.length > 0 && (
              <div className="mb-8">
                <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>Active</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {active.map(c => (
                    <CampaignCard key={c.id} campaign={c} onPause={handlePause} onCancel={handleCancel} onDelete={handleDelete} />
                  ))}
                </div>
              </div>
            )}

            {/* Past campaigns */}
            {past.length > 0 && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>Past</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {past.map(c => (
                    <CampaignCard key={c.id} campaign={c} onPause={handlePause} onCancel={handleCancel} onDelete={handleDelete} />
                  ))}
                </div>
              </div>
            )}

            {campaigns.length === 0 && (
              <div className="text-center py-20">
                <p className="text-4xl mb-3">🗓️</p>
                <p className="text-sm font-medium text-white mb-1">No campaigns yet</p>
                <p className="text-xs mb-5" style={{ color: 'var(--text-muted)' }}>
                  Launch your first campaign to run time-limited price events.
                </p>
                <button onClick={() => setShowDrawer(true)}
                  className="px-5 py-2.5 rounded-xl text-sm font-semibold"
                  style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981', border: '1px solid rgba(16,185,129,0.3)' }}>
                  Create your first campaign
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}
