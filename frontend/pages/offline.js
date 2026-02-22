import Head from 'next/head';
import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function OfflinePage() {
  const [lastSync, setLastSync] = useState(null);

  useEffect(() => {
    // Show when data was last cached
    const stored = localStorage.getItem('mi_last_sync');
    if (stored) setLastSync(new Date(stored).toLocaleString());

    // When we come back online, redirect to wherever the user was heading
    const handleOnline = () => {
      window.location.reload();
    };
    window.addEventListener('online', handleOnline);
    return () => window.removeEventListener('online', handleOnline);
  }, []);

  return (
    <>
      <Head>
        <title>Offline — MarketIntel</title>
      </Head>

      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
        {/* Icon */}
        <div className="w-20 h-20 rounded-full bg-blue-50 flex items-center justify-center mb-6">
          <svg className="w-10 h-10 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
          </svg>
        </div>

        {/* Heading */}
        <h1 className="text-2xl font-bold text-gray-900 mb-2 text-center">You're offline</h1>
        <p className="text-gray-500 text-center max-w-sm mb-1">
          MarketIntel can't reach the internet right now. Check your connection and we'll
          automatically reload when you're back.
        </p>
        {lastSync && (
          <p className="text-xs text-gray-400 mt-1">Last synced: {lastSync}</p>
        )}

        {/* Cached pages you can still visit */}
        <div className="mt-8 w-full max-w-xs space-y-2">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider text-center mb-3">
            Available offline
          </p>
          {[
            { href: '/products',  label: 'Products',   icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4' },
            { href: '/dashboard', label: 'Dashboard',  icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
            { href: '/alerts',    label: 'Alerts',     icon: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9' },
            { href: '/insights',  label: 'Insights',   icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
          ].map(({ href, label, icon }) => (
            <Link key={href} href={href}
              className="flex items-center gap-3 px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
              <svg className="w-4 h-4 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
              </svg>
              {label}
            </Link>
          ))}
        </div>

        {/* Retry button */}
        <button
          onClick={() => window.location.reload()}
          className="mt-8 px-6 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 transition-colors"
        >
          Try again
        </button>

        {/* Brand */}
        <div className="mt-12 flex items-center gap-2 text-gray-400">
          <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
          <span className="text-sm font-semibold">MarketIntel</span>
        </div>
      </div>
    </>
  );
}
