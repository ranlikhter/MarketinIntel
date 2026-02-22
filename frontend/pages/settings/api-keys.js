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
    <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 mb-6">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 text-emerald-600">{Ico.key}</div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-emerald-800 mb-1">
            Save your API key — it will only be shown once
          </p>
          <div className="flex items-center gap-2 mt-2">
            <code className="flex-1 bg-white border border-emerald-200 rounded-lg px-3 py-2 text-sm font-mono text-gray-800 truncate">
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
          <p className="text-xs text-emerald-700 mt-2">
            Use this key in the <code className="bg-emerald-100 px-1 rounded">Authorization: Bearer</code> header when calling the MarketIntel API.
          </p>
        </div>
        <button onClick={onDismiss} className="text-emerald-400 hover:text-emerald-600 text-lg leading-none">&times;</button>
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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Create API Key</h3>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Key Name</label>
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Zapier automation, Shopify app"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">A label to help you remember what this key is for.</p>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={loading || !name.trim()}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
              {loading ? 'Creating…' : 'Create Key'}
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
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
      <td className="px-4 py-3">
        <p className="text-sm font-medium text-gray-900">{apiKey.name}</p>
        <p className="text-xs text-gray-400 font-mono mt-0.5">{apiKey.key_prefix}••••••••••••••••</p>
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">{created}</td>
      <td className="px-4 py-3 text-sm text-gray-600">{lastUsed}</td>
      <td className="px-4 py-3">
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
          apiKey.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${apiKey.is_active ? 'bg-emerald-500' : 'bg-gray-400'}`} />
          {apiKey.is_active ? 'Active' : 'Revoked'}
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2 justify-end">
          <button onClick={rotate} disabled={rotating}
            title="Rotate key"
            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50">
            {Ico.rotate}
          </button>
          <button onClick={revoke} disabled={revoking}
            title="Revoke key"
            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50">
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
            <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
            <p className="text-sm text-gray-500 mt-1">
              Authenticate external apps and scripts against the MarketIntel API.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
          >
            {Ico.plus} New Key
          </button>
        </div>

        {/* New key banner */}
        {newKey?.full_key && (
          <NewKeyBanner fullKey={newKey.full_key} onDismiss={() => setNewKey(null)} />
        )}

        {/* Security note */}
        <div className="flex items-start gap-3 bg-blue-50 border border-blue-100 rounded-xl p-4 mb-6">
          <div className="text-blue-500 shrink-0 mt-0.5">{Ico.shield}</div>
          <div className="text-sm text-blue-800">
            <strong>Keep your API keys secret.</strong> Treat them like passwords — don't commit them to
            version control or share them publicly. Rotate immediately if a key is compromised.
            Pass keys in the <code className="bg-blue-100 px-1 rounded">Authorization: Bearer &lt;key&gt;</code> header.
          </div>
        </div>

        {/* Keys table */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-gray-400">Loading…</div>
          ) : keys.length === 0 ? (
            <div className="p-12 text-center">
              <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3 text-gray-400">
                {Ico.key}
              </div>
              <p className="text-gray-500 font-medium">No API keys yet</p>
              <p className="text-sm text-gray-400 mt-1">Create a key to connect external tools and automations.</p>
              <button onClick={() => setShowCreate(true)}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors">
                Create your first key
              </button>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Created</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Last Used</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
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
        <div className="mt-6 bg-gray-900 rounded-2xl p-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Example Usage</p>
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
