import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import api from '../../lib/api';

export default function CompetitorsPage() {
  const [competitors, setCompetitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all'); // 'all', 'active', 'inactive'

  useEffect(() => {
    loadCompetitors();
  }, [filter]);

  const loadCompetitors = async () => {
    try {
      setLoading(true);
      const activeOnly = filter === 'active' ? true : (filter === 'inactive' ? false : undefined);
      const data = await api.getCompetitors(activeOnly);
      setCompetitors(data);
      setError(null);
    } catch (err) {
      setError('Failed to load competitors. Make sure the backend is running.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (id, currentStatus) => {
    try {
      await api.toggleCompetitorStatus(id);
      // Update local state
      setCompetitors(competitors.map(c =>
        c.id === id ? { ...c, is_active: !currentStatus } : c
      ));
    } catch (err) {
      alert('Failed to update competitor status');
      console.error(err);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this competitor? This will remove all associated data.')) {
      return;
    }

    try {
      await api.deleteCompetitor(id);
      setCompetitors(competitors.filter(c => c.id !== id));
    } catch (err) {
      alert('Failed to delete competitor');
      console.error(err);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading competitors...</p>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <p className="text-red-800">{error}</p>
          <p className="text-red-600 text-sm mt-2">
            Start the backend server: <code className="bg-red-100 px-2 py-1 rounded">start-backend.bat</code>
          </p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="sm:flex sm:items-center">
          <div className="sm:flex-auto">
            <h1 className="text-3xl font-bold text-gray-900">Competitor Websites</h1>
            <p className="mt-2 text-sm text-gray-700">
              Manage custom competitor websites and configure scraping selectors
            </p>
          </div>
          <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
            <Link
              href="/competitors/add"
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
            >
              Add Competitor
            </Link>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="mt-6 border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setFilter('all')}
              className={`${
                filter === 'all'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              All ({competitors.length})
            </button>
            <button
              onClick={() => setFilter('active')}
              className={`${
                filter === 'active'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              Active
            </button>
            <button
              onClick={() => setFilter('inactive')}
              className={`${
                filter === 'inactive'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              Inactive
            </button>
          </nav>
        </div>

        {/* Competitors Grid */}
        {competitors.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow mt-6">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
              />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No competitors</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by adding your first competitor website.
            </p>
            <div className="mt-6">
              <Link
                href="/competitors/add"
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
              >
                + Add Competitor
              </Link>
            </div>
          </div>
        ) : (
          <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {competitors.map((competitor) => (
              <div
                key={competitor.id}
                className="bg-white overflow-hidden shadow rounded-lg border border-gray-200 hover:shadow-lg transition-shadow"
              >
                <div className="p-6">
                  {/* Header */}
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900 truncate">
                      {competitor.name}
                    </h3>
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        competitor.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {competitor.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>

                  {/* Base URL */}
                  <a
                    href={competitor.base_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary-600 hover:text-primary-900 break-all block mb-4"
                  >
                    {competitor.base_url}
                  </a>

                  {/* Type */}
                  <div className="mb-4">
                    <span className="text-xs text-gray-500">Type: </span>
                    <span className="text-xs font-medium text-gray-700 capitalize">
                      {competitor.website_type || 'custom'}
                    </span>
                  </div>

                  {/* Selectors */}
                  <div className="space-y-2 mb-4">
                    <div className="text-xs">
                      <span className="text-gray-500">Price: </span>
                      <code className="bg-gray-100 px-2 py-0.5 rounded text-gray-700">
                        {competitor.price_selector || 'Not set'}
                      </code>
                    </div>
                    <div className="text-xs">
                      <span className="text-gray-500">Title: </span>
                      <code className="bg-gray-100 px-2 py-0.5 rounded text-gray-700">
                        {competitor.title_selector || 'Not set'}
                      </code>
                    </div>
                  </div>

                  {/* Notes */}
                  {competitor.notes && (
                    <p className="text-xs text-gray-600 mb-4 line-clamp-2">
                      {competitor.notes}
                    </p>
                  )}

                  {/* Date */}
                  <p className="text-xs text-gray-500 mb-4">
                    Added: {new Date(competitor.created_at).toLocaleDateString()}
                  </p>

                  {/* Actions */}
                  <div className="flex items-center justify-between pt-4 border-t border-gray-200">
                    <button
                      onClick={() => handleToggleActive(competitor.id, competitor.is_active)}
                      className={`text-sm font-medium ${
                        competitor.is_active
                          ? 'text-gray-600 hover:text-gray-900'
                          : 'text-green-600 hover:text-green-900'
                      }`}
                    >
                      {competitor.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <div className="space-x-3">
                      <Link
                        href={`/competitors/${competitor.id}/edit`}
                        className="text-sm font-medium text-primary-600 hover:text-primary-900"
                      >
                        Edit
                      </Link>
                      <button
                        onClick={() => handleDelete(competitor.id)}
                        className="text-sm font-medium text-red-600 hover:text-red-900"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
