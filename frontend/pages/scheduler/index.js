import { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import api from '../../lib/api';

const Ico = {
  tasks:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  calendar:<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>,
  bolt:    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  history: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  search:  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>,
  chart:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  bell:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>,
  mail:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>,
  trash:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>,
  clock:   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  spin:    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>,
};

function StatCard({ label, value, color, icon }) {
  const bg = {
    blue:   'bg-blue-900/40 text-blue-400',
    violet: 'bg-violet-900/40 text-violet-400',
    emerald:'bg-emerald-900/40 text-emerald-400',
    gray:   'bg-white/10 text-white/40',
  }[color];
  return (
    <div className="rounded-2xl p-5 flex items-center gap-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${bg}`}>{icon}</div>
      <div>
        <p className="text-2xl font-bold text-white leading-none">{value ?? 0}</p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
      </div>
    </div>
  );
}

const TRIGGERS = [
  {
    key: 'scrapeAll',
    title: 'Scrape All Products',
    desc: 'Scrape all monitored products from competitors',
    icon: Ico.search,
    color: 'blue',
    endpoint: '/api/scheduler/scrape/all',
    body: null,
  },
  {
    key: 'priorityScrape',
    title: 'Priority Scrape',
    desc: 'Scrape products not updated in the last 24h',
    icon: Ico.bolt,
    color: 'amber',
    endpoint: '/api/scheduler/scrape/all',
    body: { priority: true },
  },
  {
    key: 'analytics',
    title: 'Update Analytics',
    desc: 'Recalculate trends, insights and forecasts',
    icon: Ico.chart,
    color: 'violet',
    endpoint: '/api/scheduler/analytics/update',
    body: null,
  },
  {
    key: 'alertCheck',
    title: 'Check Price Alerts',
    desc: 'Find significant price changes and fire alerts',
    icon: Ico.bell,
    color: 'red',
    endpoint: '/api/scheduler/alerts/check',
    body: null,
  },
  {
    key: 'digest',
    title: 'Send Daily Digest',
    desc: 'Generate and send the daily summary email',
    icon: Ico.mail,
    color: 'emerald',
    endpoint: '/api/scheduler/notifications/digest',
    body: null,
  },
  {
    key: 'cleanup',
    title: 'Data Cleanup',
    desc: 'Remove price history older than 90 days',
    icon: Ico.trash,
    color: 'gray',
    endpoint: '/api/scheduler/maintenance/cleanup',
    body: null,
    dangerous: true,
  },
];

const SCHEDULE = [
  { name: 'Scrape All Products', schedule: 'Every 6 hours',           desc: 'Automatically scrapes all monitored products' },
  { name: 'Update Analytics',    schedule: 'Daily at 2:00 AM',        desc: 'Calculates trends and insights' },
  { name: 'Daily Digest Email',  schedule: 'Daily at 8:00 AM',        desc: 'Sends summary email to users' },
  { name: 'Data Cleanup',        schedule: 'Weekly, Sunday at 3:00 AM', desc: 'Removes old price history data' },
];

const BTN_COLOR = {
  blue:   'bg-blue-600 hover:bg-blue-700',
  amber:  'bg-amber-500 hover:bg-amber-600',
  violet: 'bg-violet-600 hover:bg-violet-700',
  red:    'bg-red-600 hover:bg-red-700',
  emerald:'bg-emerald-600 hover:bg-emerald-700',
  gray:   'bg-white/20 hover:bg-white/30',
};

export default function SchedulerPage() {
  const [queueStats, setQueueStats] = useState(null);
  const [activeTasks, setActiveTasks] = useState([]);
  const [taskHistory, setTaskHistory] = useState([]);
  const [running, setRunning] = useState({});
  const [toast, setToast] = useState(null);

  useEffect(() => {
    loadStats();
    const iv = setInterval(loadStats, 5000);
    return () => clearInterval(iv);
  }, []);

  const loadStats = async () => {
    try {
      const [stats, tasks] = await Promise.all([
        api.request('/api/scheduler/queue/stats'),
        api.request('/api/scheduler/tasks/active'),
      ]);
      setQueueStats(stats);
      setActiveTasks(tasks.active_tasks || []);
    } catch { /* silent refresh */ }
  };

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const trigger = async (t) => {
    if (t.dangerous && !confirm(`${t.title}: This cannot be undone. Proceed?`)) return;
    setRunning(r => ({ ...r, [t.key]: true }));
    try {
      const opts = { method: 'POST' };
      if (t.body) opts.body = JSON.stringify(t.body);
      const result = await api.request(t.endpoint, opts);
      showToast(`${t.title} started!`);
      setTaskHistory(prev => [{ ...result, label: t.title, timestamp: new Date().toISOString() }, ...prev.slice(0, 9)]);
      setTimeout(loadStats, 1200);
    } catch (e) {
      showToast(e.message || `Failed to run ${t.title}`, 'error');
    } finally {
      setRunning(r => ({ ...r, [t.key]: false }));
    }
  };

  return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">

        {/* Toast */}
        {toast && (
          <div className={`fixed top-20 right-4 z-50 px-4 py-3 rounded-xl shadow-lg text-sm font-medium text-white transition-all ${toast.type === 'error' ? 'bg-red-600' : 'bg-gray-900'}`}>
            {toast.msg}
          </div>
        )}

        {/* Header */}
        <div>
          <h1 className="text-xl font-bold text-white">Scheduler</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>Manage automated scraping, analytics and maintenance tasks</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Active Tasks"     value={queueStats?.active_tasks || 0}        color="blue"   icon={Ico.tasks} />
          <StatCard label="Scheduled Tasks"  value={queueStats?.scheduled_tasks || 0}     color="violet" icon={Ico.calendar} />
          <StatCard label="Active Workers"   value={queueStats?.workers?.length || 0}     color="emerald" icon={Ico.bolt} />
          <StatCard label="Session History"  value={taskHistory.length}                   color="gray"   icon={Ico.history} />
        </div>

        {/* Manual Triggers */}
        <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <h2 className="text-sm font-semibold text-white">Manual Task Triggers</h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Run tasks on demand without waiting for the schedule</p>
          </div>
          <div className="p-5 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {TRIGGERS.map(t => {
              const isRunning = !!running[t.key];
              const iconBg = {
                blue:    'bg-blue-900/40 text-blue-400',
                amber:   'bg-amber-900/40 text-amber-400',
                violet:  'bg-violet-900/40 text-violet-400',
                red:     'bg-red-900/40 text-red-400',
                emerald: 'bg-emerald-900/40 text-emerald-400',
                gray:    'bg-white/10 text-white/40',
              }[t.color];
              return (
                <div key={t.key} className="rounded-xl p-4 flex flex-col gap-3 transition-colors" style={{ border: '1px solid var(--border)', background: 'var(--bg-elevated)' }}>
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${iconBg}`}>{t.icon}</div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-white truncate">{t.title}</p>
                      <p className="text-xs line-clamp-2" style={{ color: 'var(--text-muted)' }}>{t.desc}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => trigger(t)}
                    disabled={isRunning}
                    className={`w-full py-2 text-white text-xs font-semibold rounded-lg transition-colors disabled:opacity-50 ${t.dangerous ? 'bg-red-600 hover:bg-red-700' : BTN_COLOR[t.color]}`}
                  >
                    {isRunning ? (
                      <span className="inline-flex items-center gap-1.5 justify-center">{Ico.spin} Starting…</span>
                    ) : 'Run Now'}
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Running Tasks */}
        <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <h2 className="text-sm font-semibold text-white">Currently Running</h2>
          </div>
          {activeTasks.length === 0 ? (
            <div className="p-8 text-center text-xs" style={{ color: 'var(--text-muted)' }}>No tasks currently running</div>
          ) : (
            <div className="divide-y" style={{ '--tw-divide-opacity': 1 }}>
              {activeTasks.map(task => (
                <div key={task.task_id} className="px-5 py-3 flex items-center justify-between gap-3" style={{ borderBottom: '1px solid var(--border)' }}>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate">{task.name}</p>
                    <p className="text-xs mt-0.5 font-mono" style={{ color: 'var(--text-muted)' }}>{task.task_id.slice(0, 12)}… · {task.worker}</p>
                  </div>
                  <span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-400">
                    {Ico.spin} Running
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Task History */}
        <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <h2 className="text-sm font-semibold text-white">Session History</h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Tasks triggered during this browser session</p>
          </div>
          {taskHistory.length === 0 ? (
            <div className="p-8 text-center text-xs" style={{ color: 'var(--text-muted)' }}>No tasks triggered yet</div>
          ) : (
            <div>
              {taskHistory.map((task, i) => (
                <div key={i} className="px-5 py-3 flex items-center justify-between gap-3" style={{ borderBottom: '1px solid var(--border)' }}>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate">{task.label || task.message}</p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{new Date(task.timestamp).toLocaleString()}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      task.status === 'queued'  ? 'bg-blue-900/40 text-blue-400' :
                      task.status === 'running' ? 'bg-amber-900/40 text-amber-400' :
                                                  'bg-emerald-900/40 text-emerald-400'
                    }`}>
                      {task.status || 'queued'}
                    </span>
                    {task.task_id && (
                      <code className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{task.task_id.slice(0, 8)}…</code>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Auto Schedule */}
        <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <h2 className="text-sm font-semibold text-white">Automatic Schedule</h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Managed by Celery Beat — runs automatically</p>
          </div>
          <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {SCHEDULE.map((s, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-xl" style={{ background: 'var(--bg-elevated)' }}>
                <div className="w-8 h-8 bg-amber-900/40 rounded-lg flex items-center justify-center text-amber-400 shrink-0 mt-0.5">
                  {Ico.clock}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white">{s.name}</p>
                  <p className="text-xs text-amber-400 font-medium mt-0.5">{s.schedule}</p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </Layout>
  );
}
