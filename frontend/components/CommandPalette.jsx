'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/router';
import api from '../lib/api';

const SUGGESTIONS = [
  'Which products am I most overpriced on?',
  'Show me my recent competitor price changes',
  'Refresh my price data now',
  'Take me to repricing rules',
  'How competitive am I overall?',
  'Which competitors dropped prices this week?',
];

const SKIP_PATHS = ['/auth/', '/pricing', '/offline'];

function Dots() {
  return (
    <span className="inline-flex gap-1 items-center px-1">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-current opacity-60"
          style={{ animation: `bounce 1s ease-in-out ${i * 0.15}s infinite` }}
        />
      ))}
      <style>{`@keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}`}</style>
    </span>
  );
}

function ActionCard({ action, onNavigate }) {
  const router = useRouter();

  if (!action) return null;

  const handleClick = async () => {
    if (action.type === 'navigate') {
      router.push(action.path);
      onNavigate?.();
    } else if (action.type === 'scrape_queued') {
      // already executed on backend, just close
      onNavigate?.();
    } else if (action.type === 'create_rule') {
      // navigate to repricing with the rule payload pre-filled (query param)
      const encoded = encodeURIComponent(JSON.stringify(action.payload));
      router.push(`/repricing?newRule=${encoded}`);
      onNavigate?.();
    }
  };

  const iconMap = {
    navigate: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
      </svg>
    ),
    scrape_queued: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
    ),
    create_rule: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
      </svg>
    ),
  };

  return (
    <div
      className="mt-2 flex items-center gap-3 px-4 py-3 rounded-xl"
      style={{
        background: 'rgba(245,158,11,0.1)',
        border: '1px solid rgba(245,158,11,0.3)',
      }}
    >
      <span style={{ color: '#f59e0b' }}>{iconMap[action.type] || iconMap.navigate}</span>
      <button
        onClick={handleClick}
        className="flex-1 text-left text-sm font-medium transition-colors"
        style={{ color: '#f59e0b' }}
      >
        {action.label}
      </button>
      {action.type === 'create_rule' && action.payload?.description && (
        <span className="text-xs" style={{ color: 'rgba(245,158,11,0.7)' }}>
          {action.payload.description}
        </span>
      )}
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      {!isUser && (
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mr-2 mt-0.5"
          style={{ background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', fontSize: 12 }}
        >
          ✦
        </div>
      )}
      <div style={{ maxWidth: '80%' }}>
        <div
          className="px-4 py-2.5 rounded-2xl text-sm leading-relaxed"
          style={
            isUser
              ? {
                  background: 'linear-gradient(135deg,#2563eb,#4f46e5)',
                  color: '#fff',
                  borderBottomRightRadius: 4,
                }
              : {
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: 'rgba(255,255,255,0.9)',
                  borderBottomLeftRadius: 4,
                }
          }
        >
          {msg.loading ? <Dots /> : msg.content}
        </div>
        {msg.action && !msg.loading && (
          <ActionCard action={msg.action} onNavigate={msg.onClose} />
        )}
      </div>
    </div>
  );
}

export default function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const bottomRef = useRef(null);

  // Keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen(v => !v);
      }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Auto-focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 60);
    }
  }, [open]);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const close = useCallback(() => setOpen(false), []);

  const sendMessage = useCallback(async (text) => {
    const msg = text.trim();
    if (!msg || loading) return;

    const history = messages
      .filter(m => !m.loading && m.role)
      .map(m => ({ role: m.role, content: m.content }));

    setMessages(prev => [
      ...prev,
      { role: 'user', content: msg },
      { role: 'assistant', content: '', loading: true },
    ]);
    setInput('');
    setLoading(true);

    try {
      const res = await api.aiCommand(msg, history);
      setMessages(prev => {
        const next = [...prev];
        const loadingIdx = next.findLastIndex(m => m.loading);
        if (loadingIdx !== -1) {
          next[loadingIdx] = {
            role: 'assistant',
            content: res.reply,
            action: res.action,
            onClose: close,
            loading: false,
          };
        }
        return next;
      });
    } catch (err) {
      setMessages(prev => {
        const next = [...prev];
        const loadingIdx = next.findLastIndex(m => m.loading);
        if (loadingIdx !== -1) {
          next[loadingIdx] = {
            role: 'assistant',
            content: err?.message?.includes('ANTHROPIC_API_KEY')
              ? 'AI features require an API key to be configured.'
              : 'Something went wrong. Please try again.',
            loading: false,
          };
        }
        return next;
      });
    } finally {
      setLoading(false);
    }
  }, [messages, loading, close]);

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  if (SKIP_PATHS.some(p => router.pathname.startsWith(p))) return null;

  return (
    <>
      {/* Floating trigger button */}
      <button
        onClick={() => setOpen(v => !v)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-2.5 rounded-full shadow-lg transition-all hover:scale-105 active:scale-95 text-sm font-medium"
        style={{
          background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
          color: '#fff',
          boxShadow: '0 4px 24px rgba(99,102,241,0.4)',
        }}
        title="Open AI assistant (⌘K)"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        <span>Ask AI</span>
        <kbd
          className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-xs"
          style={{ background: 'rgba(255,255,255,0.2)', fontSize: 10 }}
        >
          ⌘K
        </kbd>
      </button>

      {/* Modal overlay */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:p-4 p-0"
          style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}
          onClick={(e) => { if (e.target === e.currentTarget) close(); }}
        >
          <div
            className="w-full sm:max-w-xl flex flex-col rounded-t-2xl sm:rounded-2xl overflow-hidden"
            style={{
              background: 'rgba(17,17,34,0.98)',
              border: '1px solid rgba(255,255,255,0.1)',
              boxShadow: '0 25px 80px rgba(0,0,0,0.6)',
              maxHeight: '80vh',
            }}
          >
            {/* Header */}
            <div
              className="flex items-center gap-3 px-4 py-3 flex-shrink-0"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}
            >
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-white"
                style={{ background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', fontSize: 13 }}
              >
                ✦
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white">Ask MarketIntel</p>
                <p className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
                  Questions, actions, navigation — just type
                </p>
              </div>
              <button
                onClick={close}
                className="p-1.5 rounded-lg transition-colors"
                style={{ color: 'rgba(255,255,255,0.4)' }}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Messages / suggestions */}
            <div className="flex-1 overflow-y-auto p-4" style={{ minHeight: 120 }}>
              {messages.length === 0 ? (
                <div>
                  <p className="text-xs font-medium mb-3" style={{ color: 'rgba(255,255,255,0.35)' }}>
                    Try asking…
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {SUGGESTIONS.map(s => (
                      <button
                        key={s}
                        onClick={() => sendMessage(s)}
                        className="px-3 py-1.5 rounded-full text-xs transition-all hover:scale-105"
                        style={{
                          background: 'rgba(99,102,241,0.12)',
                          border: '1px solid rgba(99,102,241,0.3)',
                          color: 'rgba(255,255,255,0.7)',
                        }}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg, i) => <Message key={i} msg={msg} />)
              )}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <form
              onSubmit={handleSubmit}
              className="flex items-center gap-3 p-3 flex-shrink-0"
              style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}
            >
              <input
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask anything about your prices…"
                disabled={loading}
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-white/30 text-white"
                style={{ caretColor: '#6366f1' }}
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="p-2 rounded-lg transition-all disabled:opacity-30 hover:scale-105 active:scale-95"
                style={{
                  background: input.trim() && !loading ? 'linear-gradient(135deg,#6366f1,#8b5cf6)' : 'rgba(255,255,255,0.08)',
                  color: '#fff',
                }}
              >
                {loading ? (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                )}
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
