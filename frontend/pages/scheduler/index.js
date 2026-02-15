import { useState, useEffect } from 'react';
import Head from 'next/head';
import Layout from '../../components/Layout';
import { LoadingSpinner } from '../../components/LoadingStates';
import { useToast } from '../../components/Toast';
import api from '../../lib/api';

export default function SchedulerPage() {
  const [loading, setLoading] = useState(false);
  const [queueStats, setQueueStats] = useState(null);
  const [activeTasks, setActiveTasks] = useState([]);
  const [taskHistory, setTaskHistory] = useState([]);
  const { addToast } = useToast();

  useEffect(() => {
    loadQueueStats();
    loadActiveTasks();

    // Refresh every 5 seconds
    const interval = setInterval(() => {
      loadQueueStats();
      loadActiveTasks();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const loadQueueStats = async () => {
    try {
      const data = await api.request('/api/scheduler/queue/stats');
      setQueueStats(data);
    } catch (error) {
      console.error('Failed to load queue stats:', error);
    }
  };

  const loadActiveTasks = async () => {
    try {
      const data = await api.request('/api/scheduler/tasks/active');
      setActiveTasks(data.active_tasks || []);
    } catch (error) {
      console.error('Failed to load active tasks:', error);
    }
  };

  const triggerScrapeAll = async () => {
    setLoading(true);
    try {
      const result = await api.request('/api/scheduler/scrape/all', { method: 'POST' });
      addToast(`Bulk scraping started! Task ID: ${result.task_id}`, 'success');
      addTaskToHistory(result);
      setTimeout(() => loadQueueStats(), 1000);
    } catch (error) {
      addToast('Failed to start bulk scraping', 'error');
    } finally {
      setLoading(false);
    }
  };

  const triggerPriorityScrape = async () => {
    setLoading(true);
    try {
      const result = await api.request('/api/scheduler/scrape/all', {
        method: 'POST',
        body: JSON.stringify({ priority: true })
      });
      addToast('Priority scraping started!', 'success');
      addTaskToHistory(result);
    } catch (error) {
      addToast('Failed to start priority scraping', 'error');
    } finally {
      setLoading(false);
    }
  };

  const triggerAnalytics = async () => {
    setLoading(true);
    try {
      const result = await api.request('/api/scheduler/analytics/update', { method: 'POST' });
      addToast('Analytics update started!', 'success');
      addTaskToHistory(result);
    } catch (error) {
      addToast('Failed to start analytics update', 'error');
    } finally {
      setLoading(false);
    }
  };

  const triggerAlertCheck = async () => {
    setLoading(true);
    try {
      const result = await api.request('/api/scheduler/alerts/check', { method: 'POST' });
      addToast('Price alert check started!', 'success');
      addTaskToHistory(result);
    } catch (error) {
      addToast('Failed to check alerts', 'error');
    } finally {
      setLoading(false);
    }
  };

  const triggerCleanup = async () => {
    if (!confirm('Clean up old price history data (90+ days)? This cannot be undone.')) {
      return;
    }

    setLoading(true);
    try {
      const result = await api.request('/api/scheduler/maintenance/cleanup', { method: 'POST' });
      addToast('Data cleanup started!', 'success');
      addTaskToHistory(result);
    } catch (error) {
      addToast('Failed to start cleanup', 'error');
    } finally {
      setLoading(false);
    }
  };

  const addTaskToHistory = (task) => {
    setTaskHistory(prev => [
      {
        ...task,
        timestamp: new Date().toISOString()
      },
      ...prev.slice(0, 9) // Keep last 10
    ]);
  };

  return (
    <Layout>
      <Head>
        <title>Scheduler & Background Tasks - MarketIntel</title>
      </Head>

      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">⚙️ Scheduler & Background Tasks</h1>
            <p className="mt-2 text-gray-600">
              Manage automated scraping, analytics, and maintenance tasks
            </p>
          </div>
        </div>

        {/* Queue Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <StatCard
            label="Active Tasks"
            value={queueStats?.active_tasks || 0}
            icon="🔄"
            color="blue"
          />
          <StatCard
            label="Scheduled Tasks"
            value={queueStats?.scheduled_tasks || 0}
            icon="📅"
            color="purple"
          />
          <StatCard
            label="Active Workers"
            value={queueStats?.workers?.length || 0}
            icon="⚡"
            color="green"
          />
          <StatCard
            label="Task History"
            value={taskHistory.length}
            icon="📊"
            color="gray"
          />
        </div>

        {/* Manual Triggers */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">🚀 Manual Task Triggers</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Scraping Tasks */}
            <TaskTriggerCard
              title="Scrape All Products"
              description="Scrape all monitored products from competitors"
              icon="🔍"
              color="blue"
              onClick={triggerScrapeAll}
              loading={loading}
            />

            <TaskTriggerCard
              title="Priority Scrape"
              description="Scrape products not updated in 24h"
              icon="⚡"
              color="yellow"
              onClick={triggerPriorityScrape}
              loading={loading}
            />

            <TaskTriggerCard
              title="Update Analytics"
              description="Calculate trends and insights"
              icon="📊"
              color="purple"
              onClick={triggerAnalytics}
              loading={loading}
            />

            <TaskTriggerCard
              title="Check Price Alerts"
              description="Find significant price changes"
              icon="🔔"
              color="red"
              onClick={triggerAlertCheck}
              loading={loading}
            />

            <TaskTriggerCard
              title="Send Daily Digest"
              description="Generate and send daily report"
              icon="📧"
              color="green"
              onClick={async () => {
                setLoading(true);
                try {
                  const result = await api.request('/api/scheduler/notifications/digest', { method: 'POST' });
                  addToast('Digest generation started!', 'success');
                  addTaskToHistory(result);
                } catch (error) {
                  addToast('Failed to generate digest', 'error');
                } finally {
                  setLoading(false);
                }
              }}
              loading={loading}
            />

            <TaskTriggerCard
              title="Data Cleanup"
              description="Remove old price history (90+ days)"
              icon="🗑️"
              color="gray"
              onClick={triggerCleanup}
              loading={loading}
              dangerous
            />
          </div>
        </div>

        {/* Active Tasks */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">🔄 Currently Running Tasks</h2>

          {activeTasks.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>No tasks currently running</p>
            </div>
          ) : (
            <div className="space-y-3">
              {activeTasks.map((task) => (
                <div key={task.task_id} className="flex items-center justify-between p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex-1">
                    <div className="font-semibold text-gray-900">{task.name}</div>
                    <div className="text-sm text-gray-600">Task ID: {task.task_id}</div>
                    <div className="text-xs text-gray-500">Worker: {task.worker}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <LoadingSpinner size="sm" />
                    <span className="text-sm font-medium text-blue-600">Running...</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Task History */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">📜 Recent Task History</h2>

          {taskHistory.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>No tasks triggered yet in this session</p>
            </div>
          ) : (
            <div className="space-y-2">
              {taskHistory.map((task, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded border border-gray-200">
                  <div>
                    <div className="font-medium text-gray-900">{task.message}</div>
                    <div className="text-xs text-gray-500">
                      {new Date(task.timestamp).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 text-xs font-semibold rounded ${
                      task.status === 'queued' ? 'bg-blue-100 text-blue-700' :
                      task.status === 'running' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      {task.status}
                    </span>
                    <code className="text-xs text-gray-500">{task.task_id.slice(0, 8)}...</code>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Scheduled Tasks Info */}
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">📅 Automatic Schedule (Celery Beat)</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ScheduleInfo
              name="Scrape All Products"
              schedule="Every 6 hours"
              description="Automatically scrapes all monitored products"
            />
            <ScheduleInfo
              name="Update Analytics"
              schedule="Daily at 2:00 AM"
              description="Calculates trends and insights"
            />
            <ScheduleInfo
              name="Daily Digest Email"
              schedule="Daily at 8:00 AM"
              description="Sends summary email to users"
            />
            <ScheduleInfo
              name="Data Cleanup"
              schedule="Weekly on Sunday 3:00 AM"
              description="Removes old price history data"
            />
          </div>
        </div>
      </div>
    </Layout>
  );
}

function StatCard({ label, value, icon, color }) {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    purple: 'bg-purple-50 border-purple-200 text-purple-700',
    green: 'bg-green-50 border-green-200 text-green-700',
    gray: 'bg-gray-50 border-gray-200 text-gray-700'
  };

  return (
    <div className={`rounded-lg shadow p-6 border ${colorClasses[color]}`}>
      <div className="text-3xl mb-2">{icon}</div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm font-medium mt-1">{label}</div>
    </div>
  );
}

function TaskTriggerCard({ title, description, icon, color, onClick, loading, dangerous = false }) {
  const colorClasses = {
    blue: 'bg-blue-500 hover:bg-blue-600',
    yellow: 'bg-yellow-500 hover:bg-yellow-600',
    purple: 'bg-purple-500 hover:bg-purple-600',
    red: 'bg-red-500 hover:bg-red-600',
    green: 'bg-green-500 hover:bg-green-600',
    gray: 'bg-gray-500 hover:bg-gray-600'
  };

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 p-5 hover:shadow-lg transition-shadow">
      <div className="text-3xl mb-3">{icon}</div>
      <h3 className="font-bold text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-600 mb-4">{description}</p>
      <button
        onClick={onClick}
        disabled={loading}
        className={`w-full px-4 py-2 text-white text-sm font-medium rounded-md transition-colors ${
          dangerous ? 'bg-red-500 hover:bg-red-600' : colorClasses[color]
        } disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {loading ? 'Starting...' : 'Run Now'}
      </button>
    </div>
  );
}

function ScheduleInfo({ name, schedule, description }) {
  return (
    <div className="bg-white rounded-lg p-4 border border-gray-200">
      <div className="flex items-start gap-3">
        <div className="text-2xl">⏰</div>
        <div>
          <div className="font-bold text-gray-900">{name}</div>
          <div className="text-sm text-blue-600 font-semibold">{schedule}</div>
          <div className="text-xs text-gray-600 mt-1">{description}</div>
        </div>
      </div>
    </div>
  );
}
