import { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import { useToast } from '../../components/Toast';
import { useAuth } from '../../context/AuthContext';
import api from '../../lib/api';

// ─── Icons ────────────────────────────────────────────────────────────────────
const Ico = {
  users:  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>,
  plus:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  trash:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>,
  edit:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>,
  crown:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" /></svg>,
};

const ROLE_COLORS = {
  admin:  { background: 'rgba(139,92,246,0.15)', color: '#a78bfa' },
  editor: { background: 'rgba(59,130,246,0.15)', color: '#60a5fa' },
  viewer: { background: 'var(--bg-elevated)', color: 'var(--text-muted)' },
};

// ─── Invite Modal ─────────────────────────────────────────────────────────────
function InviteModal({ wsId, onClose, onInvited }) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('viewer');
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();

  async function submit(e) {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    try {
      const member = await api.inviteMember(wsId, email.trim(), role);
      onInvited(member);
      onClose();
      addToast(`${email} added to workspace`, 'success');
    } catch (err) {
      addToast(err.message || 'Invite failed', 'error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="rounded-2xl shadow-2xl w-full max-w-md p-6" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
        <h3 className="text-lg font-semibold text-white mb-4">Invite Team Member</h3>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1">Email Address</label>
            <input
              autoFocus type="email"
              value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="colleague@example.com"
              className="glass-input w-full rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
            />
            <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Must already have a MarketIntel account.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1">Role</label>
            <select value={role} onChange={(e) => setRole(e.target.value)}
              className="glass-input w-full rounded-lg px-3 py-2 text-sm text-white focus:outline-none">
              <option value="viewer">Viewer — read only</option>
              <option value="editor">Editor — can create &amp; update</option>
              <option value="admin">Admin — full access + manage members</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-medium text-white/70 hover:bg-white/5 transition-colors"
              style={{ border: '1px solid var(--border)' }}>
              Cancel
            </button>
            <button type="submit" disabled={loading || !email.trim()}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
              {loading ? 'Inviting…' : 'Send Invite'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Create Workspace Modal ───────────────────────────────────────────────────
function CreateWsModal({ onClose, onCreate }) {
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();

  async function submit(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    try {
      const ws = await api.createWorkspace(name.trim());
      onCreate(ws);
      onClose();
    } catch (err) {
      addToast(err.message || 'Failed to create workspace', 'error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="rounded-2xl shadow-2xl w-full max-w-md p-6" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
        <h3 className="text-lg font-semibold text-white mb-4">Create Workspace</h3>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1">Workspace Name</label>
            <input
              autoFocus
              value={name} onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Acme Commerce Team"
              className="glass-input w-full rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-medium text-white/70 hover:bg-white/5 transition-colors"
              style={{ border: '1px solid var(--border)' }}>
              Cancel
            </button>
            <button type="submit" disabled={loading || !name.trim()}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
              {loading ? 'Creating…' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Workspace Panel ──────────────────────────────────────────────────────────
function WorkspacePanel({ ws, isOwner, isActive, onDeleted, onSelected }) {
  const [members, setMembers] = useState(ws.members || []);
  const [showInvite, setShowInvite] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [switching, setSwitching] = useState(false);
  const { addToast } = useToast();

  async function removeMember(uid, memberName) {
    if (!confirm(`Remove ${memberName} from this workspace?`)) return;
    try {
      await api.removeMember(ws.id, uid);
      setMembers((prev) => prev.filter((m) => m.user_id !== uid));
      addToast('Member removed', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to remove member', 'error');
    }
  }

  async function changeRole(uid, newRole) {
    try {
      const updated = await api.updateMemberRole(ws.id, uid, newRole);
      setMembers((prev) => prev.map((m) => (m.user_id === uid ? { ...m, role: updated.role } : m)));
    } catch (err) {
      addToast(err.message || 'Failed to update role', 'error');
    }
  }

  async function deleteWorkspace() {
    if (!confirm(`Delete workspace "${ws.name}"? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await api.deleteWorkspace(ws.id);
      onDeleted(ws.id);
      addToast('Workspace deleted', 'success');
    } catch (err) {
      addToast(err.message || 'Failed to delete workspace', 'error');
      setDeleting(false);
    }
  }

  async function selectCurrentWorkspace() {
    if (isActive || switching) return;
    setSwitching(true);
    try {
      await onSelected(ws.id);
    } finally {
      setSwitching(false);
    }
  }

  return (
    <div className="rounded-2xl shadow-sm overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
      {/* Workspace header */}
      <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-elevated)' }}>
        <div>
          <h3 className="font-semibold text-white">{ws.name}</h3>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
            {members.length} member{members.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isActive ? (
            <span
              className="px-3 py-1 rounded-full text-xs font-semibold"
              style={{ background: 'rgba(59,130,246,0.16)', color: '#93C5FD' }}
            >
              Active Workspace
            </span>
          ) : (
            <button
              onClick={selectCurrentWorkspace}
              disabled={switching}
              className="px-3 py-1.5 rounded-lg text-sm font-medium text-white/80 hover:bg-white/5 transition-colors disabled:opacity-50"
              style={{ border: '1px solid var(--border)' }}
            >
              {switching ? 'Switching…' : 'Set Active'}
            </button>
          )}
          {isOwner && (
            <button
              onClick={() => setShowInvite(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              {Ico.plus} Invite
            </button>
          )}
          {isOwner && (
            <button onClick={deleteWorkspace} disabled={deleting}
              className="p-1.5 text-white/30 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50"
              title="Delete workspace">
              {Ico.trash}
            </button>
          )}
        </div>
      </div>

      {/* Members table */}
      <div>
        {members.length === 0 ? (
          <p className="text-sm text-center py-8" style={{ color: 'var(--text-muted)' }}>No members yet. Invite your team!</p>
        ) : (
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>Member</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>Role</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>Joined</th>
                {isOwner && <th className="px-4 py-3" style={{ background: 'var(--bg-elevated)' }} />}
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id} className="hover:bg-white/5 transition-colors" style={{ borderBottom: '1px solid var(--border)' }}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold" style={{ background: 'rgba(59,130,246,0.15)', color: '#60a5fa' }}>
                        {(m.full_name || m.email || '?')[0].toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">{m.full_name || m.email}</p>
                        {m.full_name && <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{m.email}</p>}
                      </div>
                      {m.user_id === ws.owner_id && (
                        <span className="text-amber-400" title="Workspace owner">{Ico.crown}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {isOwner && m.user_id !== ws.owner_id ? (
                      <select
                        value={m.role}
                        onChange={(e) => changeRole(m.user_id, e.target.value)}
                        className="glass-input text-xs rounded-lg px-2 py-1 text-white focus:outline-none"
                      >
                        <option value="viewer">Viewer</option>
                        <option value="editor">Editor</option>
                        <option value="admin">Admin</option>
                      </select>
                    ) : (
                      <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium" style={ROLE_COLORS[m.role] || ROLE_COLORS.viewer}>
                        {m.role}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-muted)' }}>
                    {m.joined_at ? new Date(m.joined_at).toLocaleDateString() : '—'}
                  </td>
                  {isOwner && (
                    <td className="px-4 py-3">
                      {m.user_id !== ws.owner_id && (
                        <button
                          onClick={() => removeMember(m.user_id, m.full_name || m.email)}
                          className="p-1.5 text-white/30 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                          title="Remove member">
                          {Ico.trash}
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showInvite && (
        <InviteModal
          wsId={ws.id}
          onClose={() => setShowInvite(false)}
          onInvited={(m) => setMembers((prev) => [...prev, m])}
        />
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function TeamPage() {
  const [showCreate, setShowCreate] = useState(false);
  const { addToast } = useToast();
  const {
    user,
    workspaces,
    workspacesLoading,
    refreshWorkspaces,
    selectWorkspace,
  } = useAuth();

  useEffect(() => {
    refreshWorkspaces().catch(() => addToast('Failed to load workspaces', 'error'));
  }, [refreshWorkspaces, addToast]);

  async function handleCreated() {
    await refreshWorkspaces();
  }

  async function handleDeleted() {
    await refreshWorkspaces();
  }

  async function handleSelectWorkspace(workspaceId) {
    const result = await selectWorkspace(workspaceId);
    if (!result.success) {
      addToast(result.error || 'Failed to switch workspace', 'error');
      return;
    }
    addToast('Active workspace updated', 'success');
    await refreshWorkspaces();
  }

  const allWorkspaces = [
    ...(workspaces?.owned || []).map((ws) => ({ ...ws, isOwner: true })),
    ...(workspaces?.member_of || []).map((ws) => ({ ...ws, isOwner: false })),
  ];

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Team &amp; Workspaces</h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
              Collaborate with your team. Share products, alerts, and saved views.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
          >
            {Ico.plus} New Workspace
          </button>
        </div>

        {workspacesLoading ? (
          <div className="text-center py-20" style={{ color: 'var(--text-muted)' }}>Loading…</div>
        ) : allWorkspaces.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>
              {Ico.users}
            </div>
            <h3 className="text-lg font-medium text-white/70 mb-2">No workspaces yet</h3>
            <p className="text-sm max-w-sm mx-auto mb-6" style={{ color: 'var(--text-muted)' }}>
              Create a workspace to invite your team and share your competitive intelligence data.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="px-5 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              Create your first workspace
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {allWorkspaces.map((ws) => (
              <WorkspacePanel
                key={ws.id}
                ws={ws}
                isOwner={ws.isOwner}
                isActive={ws.id === user?.active_workspace_id}
                onDeleted={handleDeleted}
                onSelected={handleSelectWorkspace}
              />
            ))}
          </div>
        )}
      </div>

      {showCreate && (
        <CreateWsModal
          onClose={() => setShowCreate(false)}
          onCreate={handleCreated}
        />
      )}
    </Layout>
  );
}
