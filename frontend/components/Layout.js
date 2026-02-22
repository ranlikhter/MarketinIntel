import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../context/AuthContext';

const TIER_COLORS = {
  free:       { bg: 'bg-gray-100',   text: 'text-gray-700',   label: 'Free'       },
  pro:        { bg: 'bg-blue-100',   text: 'text-blue-700',   label: 'Pro'        },
  business:   { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Business'   },
  enterprise: { bg: 'bg-amber-100',  text: 'text-amber-700',  label: 'Enterprise' },
};

function UserMenu({ user, logout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const router = useRouter();

  // Close on outside click
  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() ?? '?';

  const tier = user?.subscription_tier ?? 'free';
  const tierStyle = TIER_COLORS[tier] ?? TIER_COLORS.free;

  const handleLogout = () => {
    setOpen(false);
    logout();
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 rounded-full focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
      >
        {/* Avatar circle */}
        <div className="w-9 h-9 rounded-full bg-primary-600 flex items-center justify-center text-white font-semibold text-sm select-none ring-2 ring-white">
          {initials}
        </div>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
            <p className="font-semibold text-gray-900 truncate">
              {user?.full_name || 'Your Account'}
            </p>
            <p className="text-sm text-gray-500 truncate">{user?.email}</p>
            <span className={`inline-flex items-center mt-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${tierStyle.bg} ${tierStyle.text}`}>
              {tierStyle.label} Plan
            </span>
          </div>

          {/* Links */}
          <div className="py-1">
            <Link
              href="/settings"
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Account Settings
            </Link>
            <Link
              href="/pricing"
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Upgrade Plan
            </Link>
          </div>

          <div className="border-t border-gray-100 py-1">
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Layout({ children }) {
  const router = useRouter();
  const { user, logout } = useAuth();

  const isActive = (path) => router.pathname === path;
  const startsWith = (path) => router.pathname.startsWith(path);

  const navLink = (href, label, match) => (
    <Link
      href={href}
      className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors ${
        match
          ? 'border-primary-500 text-gray-900'
          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
      }`}
    >
      {label}
    </Link>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              {/* Logo */}
              <Link href="/" className="flex items-center">
                <span className="text-2xl font-bold text-primary-600">MarketIntel</span>
              </Link>

              {/* Navigation Links */}
              <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
                {navLink('/', 'Home', isActive('/'))}
                {navLink('/dashboard', 'Comparison', startsWith('/dashboard'))}
                {navLink('/products', 'Products', startsWith('/products'))}
                {navLink('/competitors', 'Competitors', startsWith('/competitors'))}
                {navLink('/integrations', 'Integrations', startsWith('/integrations'))}
                {navLink('/scheduler', 'Scheduler', startsWith('/scheduler'))}
              </div>
            </div>

            {/* Right side */}
            <div className="flex items-center gap-3">
              <Link
                href="/products/add"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-all hover:scale-105"
              >
                + Add Product
              </Link>

              {user ? (
                <UserMenu user={user} logout={logout} />
              ) : (
                <Link
                  href="/auth/login"
                  className="text-sm font-medium text-gray-500 hover:text-gray-700"
                >
                  Sign In
                </Link>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <p className="text-center text-gray-500 text-sm">
            MarketIntel - Competitive Intelligence Platform | Built with Next.js &amp; FastAPI
          </p>
        </div>
      </footer>
    </div>
  );
}
