import { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import { useToast } from '../../components/Toast';
import api from '../../lib/api';

// ─── Icons ────────────────────────────────────────────────────────────────────
const Ico = {
  key:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" /></svg>,
  copy:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>,
  trash:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>,
  rotate: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  plus:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  eye:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>,
  shield: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
};

// ─── Newly-created key banner ─────────────────────────────────────────────────
function NewKeyBanner({ fullKey, onDismiss }) {
  const { addToast } = useToast();
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(fullKey).then(() => {
      setCopied(true);
      addToast('API key copied to clipboard', 'success');
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="rounded-xl p-4 mb-6" style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 text-emerald-400">{Ico.key}</div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-emerald-400 mb-1">
            Save your API key — it will only be shown once
          </p>
          <div className="flex items-center gap-2 mt-2">
            <code className="flex-1 rounded-lg px-3 py-2 text-sm font-mono text-white/80 truncate" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-md)' }}>
              {fullKey}
            </code>
            <button
              onClick={copy}
              className="shrink-0 flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
            >
              {Ico.copy}
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <p className="text-xs text-emerald-400/70 mt-2">
            Use this key in the <code className="px-1 rounded" style={{ background: 'rgba(16,185,129,0.12)' }}>Authorization: Bearer</code> header when calling the MarketIntel API.
          </p>
        </div>
        <button onClick={onDismiss} className="text-emerald-400/50 hover:text-emerald-400 text-lg leading-none">&times;</button>
      </div>
    </div>
  );
}

// ─── Create Key Modal ─────────────────────────────────────────────────────────
function CreateKeyModal({ onClose, onCreate }) {
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();

  async function submit(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    try {
      const result = await api.createApiKey(name.trim());
      onCreate(result);
      onClose();
    } catch (err) {
      addToast(err.message || 'Failed to create API key', 'error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="rounded-2xl shadow-2xl w-full max-w-md p-6" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-md)' }}>
        <h3 className="text-lg font-semibold text-white mb-4">Create API Key</h3>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1">Key Name</label>
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Zapier automation, Shopify app"
              className="glass-input appearance-none block w-full px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/50 transition"
            />
            <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>A label to help you remember what this key is for.</p>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-medium text-white/70 hover:text-white hover:bg-white/5 transition-colors"
              style={{ border: '1px solid var(--border-md)' }}>
              Cancel
            </button>
            <button type="submit" disabled={loading || !name.trim()}
              className="flex-1 px-4 py-2 gradient-brand text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors">
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-amber-500 rounded-full animate-spin" />
                  Creating…
                </span>
              ) : 'Create Key'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Key Row ──────────────────────────────────────────────────────────────────
function KeyRow({ apiKey, onRevoke, onRotate }) {
  const { addToast } = useToast();
  const [revoking, setRevoking] = useState(false);
  const [rotating, setRotating] = useState(false);

  async function revoke() {
    if (!confirm(`Revoke "${apiKey.name}"? This cannot be undone.`)) return;
    setRevoking(true);
    try {
      await api.deleteApiKey(apiKey.id);
      onRevoke(apiKey.id);
      addToast('API key revoked', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to revoke key', 'error');
    } finally {
      setRevoking(false);
    }
  }

  async function rotate() {
    if (!confirm(`Rotate "${apiKey.name}"? The old key will stop working immediately.`)) return;
    setRotating(true);
    try {
      const result = await api.rotateApiKey(apiKey.id);
      onRotate(result);
      addToast('Key rotated — save your new key!', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to rotate key', 'error');
    } finally {
      setRotating(false);
    }
  }

  const created = new Date(apiKey.created_at).toLocaleDateString();
  const lastUsed = apiKey.last_used_at
    ? new Date(apiKey.last_used_at).toLocaleDateString()
    : 'Never';

  return (
    <tr className="hover:bg-white/5 transition-colors" style={{ borderBottom: '1px solid var(--border)' }}>
      <td className="px-4 py-3">
        <p className="text-sm font-medium text-white">{apiKey.name}</p>
        <p className="text-xs font-mono mt-0.5" style={{ color: 'var(--text-muted)' }}>{apiKey.key_prefix}••••••••••••••••</p>
      </td>
      <td className="px-4 py-3 text-sm text-white/60">{created}</td>
      <td className="px-4 py-3 text-sm text-white/60">{lastUsed}</td>
      <td className="px-4 py-3">
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
          apiKey.is_active
            ? 'text-emerald-400'
            : 'text-white/40'
        }`} style={{
          background: apiKey.is_active ? 'rgba(16,185,129,0.12)' : 'rgba(255,255,255,0.06)',
          border: `1px solid ${apiKey.is_active ? 'rgba(16,185,129,0.25)' : 'rgba(255,255,255,0.08)'}`,
        }}>
          <span className={`w-1.5 h-1.5 rounded-full ${apiKey.is_active ? 'bg-emerald-400' : 'bg-white/30'}`} />
          {apiKey.is_active ? 'Active' : 'Revoked'}
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2 justify-end">
          <button onClick={rotate} disabled={rotating}
            title="Rotate key"
            className="p-1.5 text-white/30 hover:text-amber-400 hover:bg-amber-500/10 rounded-lg transition-colors disabled:opacity-50">
            {Ico.rotate}
          </button>
          <button onClick={revoke} disabled={revoking}
            title="Revoke key"
            className="p-1.5 text-white/30 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50">
            {Ico.trash}
          </button>
        </div>
      </td>
    </tr>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function ApiKeysPage() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newKey, setNewKey] = useState(null); // newly created key (full value shown once)
  const { addToast } = useToast();

  useEffect(() => {
    api.getApiKeys()
      .then(setKeys)
      .catch(() => setKeys([]))
      .finally(() => setLoading(false));
  }, []);

  function handleCreated(result) {
    setNewKey(result);
    setKeys((prev) => [result, ...prev]);
  }

  function handleRevoked(id) {
    setKeys((prev) => prev.filter((k) => k.id !== id));
  }

  function handleRotated(result) {
    setNewKey(result);
    setKeys((prev) => prev.map((k) => (k.id === result.id ? result : k)));
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">API Keys</h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
              Authenticate external apps and scripts against the MarketIntel API.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90 shadow-sm"
          >
            {Ico.plus} New Key
          </button>
        </div>

        {/* New key banner */}
        {newKey?.full_key && (
          <NewKeyBanner fullKey={newKey.full_key} onDismiss={() => setNewKey(null)} />
        )}

        {/* Security note */}
        <div className="flex items-start gap-3 rounded-xl p-4 mb-6" style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.18)' }}>
          <div className="text-amber-400 shrink-0 mt-0.5">{Ico.shield}</div>
          <div className="text-sm text-white/70">
            <strong className="text-white/90">Keep your API keys secret.</strong> Treat them like passwords — don't commit them to
            version control or share them publicly. Rotate immediately if a key is compromised.
            Pass keys in the <code className="px-1 rounded text-amber-400/80" style={{ background: 'rgba(245,158,11,0.1)' }}>Authorization: Bearer &lt;key&gt;</code> header.
          </div>
        </div>

        {/* Keys table */}
        <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          {loading ? (
            <div className="p-12 text-center flex items-center justify-center gap-3" style={{ color: 'var(--text-muted)' }}>
              <span className="w-5 h-5 border-2 border-white/10 border-t-amber-500 rounded-full animate-spin" />
              Loading…
            </div>
          ) : keys.length === 0 ? (
            <div className="p-12 text-center">
              <div className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3 text-white/30" style={{ background: 'var(--bg-elevated)' }}>
                {Ico.key}
              </div>
              <p className="font-medium text-white/60">No API keys yet</p>
              <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>Create a key to connect external tools and automations.</p>
              <button onClick={() => setShowCreate(true)}
                className="mt-4 px-4 py-2 gradient-brand text-white rounded-xl text-sm font-medium transition-opacity hover:opacity-90">
                Create your first key
              </button>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-elevated)' }}>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Name</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Created</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Last Used</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Status</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {keys.map((k) => (
                  <KeyRow key={k.id} apiKey={k} onRevoke={handleRevoked} onRotate={handleRotated} />
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Usage example */}
        <div className="mt-6 rounded-2xl p-5" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
          <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>Example Usage</p>
          <pre className="text-sm text-green-400 font-mono overflow-x-auto whitespace-pre">{
`curl https://api.marketintel.io/products/ \\
  -H "Authorization: Bearer mi_your_api_key_here"`
          }</pre>
        </div>
      </div>

      {showCreate && (
        <CreateKeyModal
          onClose={() => setShowCreate(false)}
          onCreate={handleCreated}
        />
      )}
    </Layout>
  );
}
