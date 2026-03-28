import { useState, useEffect, useRef, useCallback } from 'react';
import Layout from '../components/Layout';
import api from '../lib/api';

// ── helpers ────────────────────────────────────────────────────────────────

function cls(...parts) { return parts.filter(Boolean).join(' '); }

function syntaxHighlight(json) {
  if (typeof json !== 'string') json = JSON.stringify(json, null, 2);
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      let cls = 'json-num';
      if (/^"/.test(match)) cls = /:$/.test(match) ? 'json-key' : 'json-str';
      else if (/true|false/.test(match)) cls = 'json-bool';
      else if (/null/.test(match)) cls = 'json-null';
      return `<span class="${cls}">${match}</span>`;
    }
  );
}

// ── Tab definitions ────────────────────────────────────────────────────────

const TABS = [
  {
    id: 'scrape',
    label: 'Scrape',
    desc: 'Extract data from a single URL',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
      </svg>
    ),
  },
  {
    id: 'crawl',
    label: 'Crawl',
    desc: 'Async full-site crawl with live progress',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20" />
      </svg>
    ),
  },
  {
    id: 'map',
    label: 'Map',
    desc: 'Discover all URLs without scraping',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21" />
        <line x1="9" y1="3" x2="9" y2="18" /><line x1="15" y1="6" x2="15" y2="21" />
      </svg>
    ),
  },
  {
    id: 'agent',
    label: 'Agent',
    desc: 'AI-powered natural language extraction',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
      </svg>
    ),
  },
];

// ── Sub-components ─────────────────────────────────────────────────────────

function UrlInput({ value, onChange, placeholder = 'https://example.com/product/123' }) {
  return (
    <div style={{ position: 'relative' }}>
      <span style={{
        position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
        color: 'var(--text-dim)', pointerEvents: 'none',
      }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
          <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
        </svg>
      </span>
      <input
        type="url"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="glass-input"
        style={{
          width: '100%', padding: '9px 12px 9px 34px',
          borderRadius: 8, fontSize: 13, fontFamily: "'IBM Plex Mono', monospace",
        }}
      />
    </div>
  );
}

function RunButton({ loading, onClick, label = 'Run', color = '#2563EB' }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      style={{
        display: 'flex', alignItems: 'center', gap: 7, padding: '9px 20px',
        background: loading ? '#93C5FD' : color,
        color: '#fff', border: 'none', borderRadius: 8, fontSize: 13,
        fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
        transition: 'all 0.15s', boxShadow: loading ? 'none' : '0 2px 8px rgba(37,99,235,0.25)',
      }}
    >
      {loading ? (
        <span style={{
          width: 14, height: 14, border: '2px solid rgba(255,255,255,0.4)',
          borderTopColor: '#fff', borderRadius: '50%',
          display: 'inline-block', animation: 'spin 0.7s linear infinite',
        }} />
      ) : (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
          <polygon points="5 3 19 12 5 21 5 3" />
        </svg>
      )}
      {loading ? 'Running…' : label}
    </button>
  );
}

function Label({ children }) {
  return (
    <label style={{
      display: 'block', fontSize: 11, fontWeight: 600, letterSpacing: '0.06em',
      textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6,
    }}>
      {children}
    </label>
  );
}

function Toggle({ label, checked, onChange }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', userSelect: 'none' }}>
      <div
        onClick={() => onChange(!checked)}
        style={{
          width: 36, height: 20, borderRadius: 10, position: 'relative', flexShrink: 0,
          background: checked ? '#2563EB' : '#D1D5DB',
          transition: 'background 0.2s',
        }}
      >
        <div style={{
          position: 'absolute', top: 3, left: checked ? 19 : 3,
          width: 14, height: 14, borderRadius: '50%', background: '#fff',
          transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
        }} />
      </div>
      <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{label}</span>
    </label>
  );
}

function ResultPanel({ result, type = 'json' }) {
  const [copied, setCopied] = useState(false);

  const copyText = useCallback(() => {
    const text = typeof result === 'string' ? result : JSON.stringify(result, null, 2);
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  }, [result]);

  if (!result) return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', color: 'var(--text-dim)', fontSize: 13, gap: 12,
    }}>
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" opacity={0.4}>
        <rect x="2" y="3" width="20" height="14" rx="2" />
        <line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
      </svg>
      <span>Results will appear here</span>
    </div>
  );

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 14px', borderBottom: '1px solid var(--border)',
        background: 'var(--bg-hover)', flexShrink: 0,
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
          {type === 'markdown' ? 'Markdown' : type === 'urls' ? 'URLs' : 'JSON'}
        </span>
        <button
          onClick={copyText}
          style={{
            display: 'flex', alignItems: 'center', gap: 5, padding: '4px 10px',
            background: 'transparent', border: '1px solid var(--border-md)', borderRadius: 6,
            fontSize: 11, color: 'var(--text-muted)', cursor: 'pointer', fontWeight: 500,
          }}
        >
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <div style={{
        flex: 1, overflow: 'auto', background: '#0F172A', padding: '16px 18px',
        fontFamily: "'IBM Plex Mono', monospace", fontSize: 12.5, lineHeight: 1.7,
        color: '#CBD5E1',
      }}>
        {type === 'json' && (
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
            dangerouslySetInnerHTML={{ __html: syntaxHighlight(result) }}
          />
        )}
        {type === 'markdown' && (
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#E2E8F0' }}>
            {typeof result === 'string' ? result : result.markdown || ''}
          </pre>
        )}
        {type === 'urls' && Array.isArray(result) && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {result.map((url, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ color: '#475569', minWidth: 32, textAlign: 'right', fontSize: 11 }}>{i + 1}</span>
                <a href={url} target="_blank" rel="noreferrer" style={{ color: '#60A5FA', textDecoration: 'none', wordBreak: 'break-all' }}>
                  {url}
                </a>
              </div>
            ))}
          </div>
        )}
        {type === 'screenshot' && result?.screenshot && (
          <img
            src={`data:image/png;base64,${result.screenshot}`}
            alt="Screenshot"
            style={{ maxWidth: '100%', borderRadius: 6, border: '1px solid #1E293B' }}
          />
        )}
      </div>
    </div>
  );
}

function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div style={{
      padding: '10px 14px', background: '#FEF2F2', border: '1px solid #FECACA',
      borderRadius: 8, fontSize: 13, color: '#DC2626', fontFamily: "'IBM Plex Mono', monospace",
    }}>
      {message}
    </div>
  );
}

// ── Tab panels ─────────────────────────────────────────────────────────────

function ScrapePanel() {
  const [url, setUrl] = useState('');
  const [format, setFormat] = useState('json');
  const [screenshot, setScreenshot] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const [selectors, setSelectors] = useState({ price: '', title: '', stock: '', image: '' });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const run = async () => {
    if (!url) return;
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await api.scrapeUrl({
        url,
        output_format: format,
        capture_screenshot: screenshot,
        ...(selectors.price && { price_selector: selectors.price }),
        ...(selectors.title && { title_selector: selectors.title }),
        ...(selectors.stock && { stock_selector: selectors.stock }),
        ...(selectors.image && { image_selector: selectors.image }),
      });
      setResult(data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const resultType = screenshot && result?.screenshot ? 'screenshot' : format === 'markdown' ? 'markdown' : 'json';

  return (
    <PanelLayout
      controls={
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <Label>URL</Label>
            <UrlInput value={url} onChange={setUrl} />
          </div>

          <div>
            <Label>Output Format</Label>
            <div style={{ display: 'flex', gap: 6 }}>
              {['json', 'markdown'].map((f) => (
                <button
                  key={f}
                  onClick={() => setFormat(f)}
                  style={{
                    padding: '6px 16px', borderRadius: 6, fontSize: 12, fontWeight: 600,
                    cursor: 'pointer', border: format === f ? '1.5px solid #2563EB' : '1px solid var(--border-md)',
                    background: format === f ? '#EFF6FF' : 'transparent',
                    color: format === f ? '#2563EB' : 'var(--text-muted)',
                    textTransform: 'uppercase', letterSpacing: '0.05em',
                  }}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <Toggle label="Capture screenshot (PNG)" checked={screenshot} onChange={setScreenshot} />

          <div>
            <button
              onClick={() => setAdvanced(!advanced)}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 12, color: 'var(--text-muted)', fontWeight: 600,
              }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
                style={{ transform: advanced ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }}>
                <polyline points="9 18 15 12 9 6" />
              </svg>
              CSS Selectors (optional)
            </button>
            {advanced && (
              <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
                {['price', 'title', 'stock', 'image'].map((k) => (
                  <div key={k}>
                    <Label>{k} selector</Label>
                    <input
                      type="text"
                      value={selectors[k]}
                      onChange={(e) => setSelectors({ ...selectors, [k]: e.target.value })}
                      placeholder={`.product-${k}`}
                      className="glass-input"
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 7, fontSize: 12, fontFamily: "'IBM Plex Mono', monospace" }}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          <ErrorBanner message={error} />
          <RunButton loading={loading} onClick={run} label="Run Scrape" />
        </div>
      }
      output={<ResultPanel result={result} type={resultType} />}
    />
  );
}

function CrawlPanel() {
  const [url, setUrl] = useState('');
  const [maxPages, setMaxPages] = useState(50);
  const [maxDepth, setMaxDepth] = useState(3);
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState(null);
  const [error, setError] = useState('');
  const pollRef = useRef(null);

  const stopPolling = () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };

  const pollJob = useCallback(async (jobId) => {
    try {
      const status = await api.getCrawlJob(jobId);
      setJob(status);
      if (status.status === 'completed' || status.status === 'failed') stopPolling();
    } catch (e) { setError(e.message); stopPolling(); }
  }, []);

  const start = async () => {
    if (!url) return;
    stopPolling();
    setLoading(true); setError(''); setJob(null);
    try {
      const data = await api.startCrawl({ url, max_pages: maxPages, max_depth: maxDepth });
      setJob({ job_id: data.job_id, status: 'running', progress_pct: 0, pages_visited: 0, products_found: 0 });
      pollRef.current = setInterval(() => pollJob(data.job_id), 2000);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => () => stopPolling(), []);

  const statusColor = { running: '#2563EB', completed: '#10B981', failed: '#EF4444' };

  return (
    <PanelLayout
      controls={
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <Label>Start URL</Label>
            <UrlInput value={url} onChange={setUrl} placeholder="https://shop.example.com" />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <Label>Max Pages</Label>
              <input type="number" value={maxPages} min={1} max={500}
                onChange={(e) => setMaxPages(Number(e.target.value))}
                className="glass-input"
                style={{ width: '100%', padding: '8px 10px', borderRadius: 8, fontSize: 13 }}
              />
            </div>
            <div>
              <Label>Max Depth</Label>
              <select value={maxDepth} onChange={(e) => setMaxDepth(Number(e.target.value))}
                className="glass-input"
                style={{ width: '100%', padding: '8px 10px', borderRadius: 8, fontSize: 13 }}>
                {[1, 2, 3, 4, 5].map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
          </div>
          <ErrorBanner message={error} />
          <RunButton loading={loading} onClick={start} label="Start Crawl" />

          {job && (
            <div style={{
              marginTop: 4, padding: '14px 16px', borderRadius: 10,
              border: `1.5px solid ${statusColor[job.status] || '#E5E7EB'}20`,
              background: `${statusColor[job.status] || '#6B7280'}08`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: statusColor[job.status], textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {job.status}
                  {job.status === 'running' && (
                    <span style={{
                      display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
                      background: '#2563EB', marginLeft: 8,
                      animation: 'pulse-dot 1.5s ease-in-out infinite',
                    }} />
                  )}
                </span>
                <span style={{ fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", color: 'var(--text-muted)' }}>
                  {job.job_id?.slice(0, 8)}…
                </span>
              </div>
              <div style={{ height: 6, background: '#E5E7EB', borderRadius: 4, overflow: 'hidden', marginBottom: 10 }}>
                <div style={{
                  height: '100%', borderRadius: 4,
                  background: statusColor[job.status] || '#6B7280',
                  width: `${job.progress_pct || (job.status === 'running' ? 15 : 0)}%`,
                  transition: 'width 0.5s ease',
                  backgroundImage: job.status === 'running'
                    ? 'linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.3) 50%, transparent 75%)'
                    : 'none',
                  backgroundSize: '200% 100%',
                  animation: job.status === 'running' ? 'shimmer 1.5s infinite' : 'none',
                }} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                {[
                  { label: 'Pages', value: job.pages_visited || 0 },
                  { label: 'Products', value: job.products_found || 0 },
                  { label: 'Categories', value: job.categories_found || 0 },
                ].map(({ label, value }) => (
                  <div key={label} style={{
                    textAlign: 'center', padding: '8px 4px',
                    background: 'var(--bg-surface)', borderRadius: 8,
                    border: '1px solid var(--border)',
                  }}>
                    <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "'Syne', sans-serif", color: 'var(--text)' }}>{value}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-dim)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
                  </div>
                ))}
              </div>
              {job.error && <div style={{ marginTop: 10, fontSize: 12, color: '#DC2626', fontFamily: "'IBM Plex Mono', monospace" }}>{job.error}</div>}
            </div>
          )}
        </div>
      }
      output={
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 14, color: 'var(--text-dim)' }}>
          {!job ? (
            <>
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" opacity={0.35}>
                <circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" />
                <path d="M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20" />
              </svg>
              <span style={{ fontSize: 13 }}>Start a crawl to see live progress</span>
            </>
          ) : job.status === 'completed' ? (
            <div style={{ padding: 24, textAlign: 'center' }}>
              <div style={{ fontSize: 40, marginBottom: 8 }}>✓</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#10B981' }}>Crawl Complete</div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6 }}>
                {job.products_found} products found · {job.products_imported || 0} imported
              </div>
            </div>
          ) : job.status === 'running' ? (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 13, color: '#2563EB', fontWeight: 600, marginBottom: 6 }}>Crawling…</div>
              <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>Polling every 2 seconds</div>
            </div>
          ) : (
            <div style={{ fontSize: 13, color: '#EF4444' }}>Crawl failed: {job.error}</div>
          )}
        </div>
      }
    />
  );
}

function MapPanel() {
  const [url, setUrl] = useState('');
  const [maxUrls, setMaxUrls] = useState(500);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [filter, setFilter] = useState('');
  const [error, setError] = useState('');

  const run = async () => {
    if (!url) return;
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await api.mapSite({ url, max_urls: maxUrls });
      setResult(data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const filteredUrls = result?.urls?.filter((u) => !filter || u.toLowerCase().includes(filter.toLowerCase())) || [];

  return (
    <PanelLayout
      controls={
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <Label>Website URL</Label>
            <UrlInput value={url} onChange={setUrl} placeholder="https://shop.example.com" />
          </div>
          <div>
            <Label>Max URLs</Label>
            <input type="number" value={maxUrls} min={10} max={2000}
              onChange={(e) => setMaxUrls(Number(e.target.value))}
              className="glass-input"
              style={{ width: '100%', padding: '8px 10px', borderRadius: 8, fontSize: 13 }}
            />
          </div>
          <ErrorBanner message={error} />
          <RunButton loading={loading} onClick={run} label="Map Site" color="#059669" />

          {result && (
            <div style={{ padding: '12px 14px', background: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: 10 }}>
              <div style={{ fontSize: 22, fontWeight: 800, fontFamily: "'Syne', sans-serif", color: '#065F46' }}>{result.url_count}</div>
              <div style={{ fontSize: 12, color: '#047857', fontWeight: 600 }}>URLs discovered</div>
            </div>
          )}
        </div>
      }
      output={
        result ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{
              padding: '8px 14px', borderBottom: '1px solid var(--border)',
              background: 'var(--bg-hover)', display: 'flex', gap: 10, alignItems: 'center', flexShrink: 0,
            }}>
              <input
                type="text"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter URLs…"
                className="glass-input"
                style={{ flex: 1, padding: '5px 10px', borderRadius: 6, fontSize: 12, fontFamily: "'IBM Plex Mono', monospace" }}
              />
              <span style={{ fontSize: 11, color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>{filteredUrls.length} shown</span>
            </div>
            <div style={{ flex: 1, overflow: 'auto', background: '#0F172A', padding: '14px 16px' }}>
              {filteredUrls.map((u, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 3, alignItems: 'flex-start' }}>
                  <span style={{ color: '#475569', fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", minWidth: 28, paddingTop: 1 }}>{i + 1}</span>
                  <a href={u} target="_blank" rel="noreferrer"
                    style={{ color: '#60A5FA', fontSize: 12.5, fontFamily: "'IBM Plex Mono', monospace", wordBreak: 'break-all', textDecoration: 'none', lineHeight: 1.5 }}>
                    {u}
                  </a>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <ResultPanel result={null} />
        )
      }
    />
  );
}

function AgentPanel() {
  const [url, setUrl] = useState('');
  const [prompt, setPrompt] = useState('');
  const [schemaOn, setSchemaOn] = useState(false);
  const [schema, setSchema] = useState('{\n  "name": "string",\n  "price": "number",\n  "in_stock": "boolean"\n}');
  const [includeMarkdown, setIncludeMarkdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const run = async () => {
    if (!url || !prompt) return;
    setLoading(true); setError(''); setResult(null);
    try {
      let parsedSchema = null;
      if (schemaOn && schema.trim()) {
        try { parsedSchema = JSON.parse(schema); } catch { setError('Invalid JSON schema'); setLoading(false); return; }
      }
      const data = await api.agentExtract({ url, prompt, schema: parsedSchema, include_markdown: includeMarkdown });
      setResult(data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <PanelLayout
      controls={
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <Label>URL</Label>
            <UrlInput value={url} onChange={setUrl} />
          </div>
          <div>
            <Label>Extraction Prompt</Label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={'Extract the product name, current price, was-price, and whether it\'s in stock.'}
              className="glass-input"
              style={{
                width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13, resize: 'vertical',
                minHeight: 90, fontFamily: 'inherit', lineHeight: 1.6,
              }}
            />
          </div>
          <Toggle label="Include JSON schema" checked={schemaOn} onChange={setSchemaOn} />
          {schemaOn && (
            <div>
              <Label>JSON Schema</Label>
              <textarea
                value={schema}
                onChange={(e) => setSchema(e.target.value)}
                className="glass-input"
                style={{
                  width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 12,
                  fontFamily: "'IBM Plex Mono', monospace", resize: 'vertical', minHeight: 100,
                }}
              />
            </div>
          )}
          <Toggle label="Include page markdown in response" checked={includeMarkdown} onChange={setIncludeMarkdown} />
          <ErrorBanner message={error} />
          <RunButton loading={loading} onClick={run} label="Extract" color="#7C3AED" />
        </div>
      }
      output={<ResultPanel result={result?.extracted || result} type="json" />}
    />
  );
}

// ── Layout wrapper ─────────────────────────────────────────────────────────

function PanelLayout({ controls, output }) {
  return (
    <div style={{
      display: 'flex', gap: 0, flex: 1, overflow: 'hidden',
      borderRadius: 12, border: '1px solid var(--border)',
      background: 'var(--bg-surface)', boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
    }}>
      {/* Controls */}
      <div style={{
        width: 340, minWidth: 280, flexShrink: 0,
        padding: '20px 20px 24px',
        borderRight: '1px solid var(--border)',
        overflowY: 'auto',
      }}>
        {controls}
      </div>
      {/* Output */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
        {output}
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function ScrapeApiPage() {
  const [activeTab, setActiveTab] = useState('scrape');

  const panels = { scrape: ScrapePanel, crawl: CrawlPanel, map: MapPanel, agent: AgentPanel };
  const ActivePanel = panels[activeTab] || ScrapePanel;

  return (
    <Layout>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
        .json-key  { color: #7DD3FC; }
        .json-str  { color: #86EFAC; }
        .json-num  { color: #FCA5A5; }
        .json-bool { color: #FCD34D; }
        .json-null { color: #94A3B8; }
      `}</style>

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 20px', display: 'flex', flexDirection: 'column', gap: 20, height: 'calc(100vh - 56px - 44px)', minHeight: 500 }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexShrink: 0 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 800, fontFamily: "'Syne', sans-serif", color: 'var(--text)', margin: 0 }}>
              Scrape API
            </h1>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '4px 0 0' }}>
              Firecrawl-compatible web extraction · scrape, crawl, map, and AI-extract any site
            </p>
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '5px 12px', background: '#EFF6FF', border: '1px solid #BFDBFE',
            borderRadius: 20, fontSize: 11, fontWeight: 700, color: '#2563EB',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#2563EB', animation: 'pulse-dot 2s ease-in-out infinite' }} />
            Live API
          </div>
        </div>

        {/* Tab bar */}
        <div style={{
          display: 'flex', gap: 2, flexShrink: 0,
          background: 'var(--bg-surface)', border: '1px solid var(--border)',
          borderRadius: 10, padding: 4,
        }}>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
                gap: 7, padding: '8px 12px', borderRadius: 7, border: 'none', cursor: 'pointer',
                fontSize: 13, fontWeight: activeTab === tab.id ? 700 : 500,
                background: activeTab === tab.id ? '#EFF6FF' : 'transparent',
                color: activeTab === tab.id ? '#2563EB' : 'var(--text-muted)',
                transition: 'all 0.15s',
              }}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab description */}
        <div style={{
          fontSize: 12, color: 'var(--text-muted)', flexShrink: 0,
          fontStyle: 'italic',
        }}>
          {TABS.find((t) => t.id === activeTab)?.desc}
        </div>

        {/* Panel */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <ActivePanel />
        </div>
      </div>
    </Layout>
  );
}
