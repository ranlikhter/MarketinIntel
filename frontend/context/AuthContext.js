import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/router';

const AuthContext = createContext();
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';
const MICROSOFT_CLIENT_ID = process.env.NEXT_PUBLIC_MICROSOFT_CLIENT_ID || '';

const jsonHeaders = {
  'Content-Type': 'application/json',
};

async function fetchJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : jsonHeaders),
      ...(options.headers || {}),
    },
  });

  const data = await response.json().catch(() => ({}));
  return { response, data };
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const router = useRouter();

  const loadCurrentUser = async () => {
    const { response, data } = await fetchJson('/api/auth/me', {
      method: 'GET',
    });

    if (!response.ok) {
      setUser(null);
      return { success: false, error: data.detail || 'Not authenticated' };
    }

    setUser(data);
    return { success: true, user: data };
  };

  useEffect(() => {
    const checkAuth = async () => {
      try {
        await loadCurrentUser();
      } catch (err) {
        console.error('Auth check failed:', err);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const signup = async (email, password, fullName) => {
    try {
      setError(null);
      const { response, data } = await fetchJson('/api/auth/signup', {
        method: 'POST',
        body: JSON.stringify({
          email,
          password,
          full_name: fullName,
        }),
      });

      if (!response.ok) {
        throw new Error(data.detail || 'Signup failed');
      }

      setUser(data.user);
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  const login = async (email, password) => {
    try {
      setError(null);
      const { response, data } = await fetchJson('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          email,
          password,
        }),
      });

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      setUser(data.user);
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  const loginWithGoogle = async (credential) => {
    try {
      setError(null);
      const { response, data } = await fetchJson('/api/auth/sso/google', {
        method: 'POST',
        body: JSON.stringify({ credential }),
      });

      if (!response.ok) {
        throw new Error(data.detail || 'Google sign-in failed');
      }

      setUser(data.user);
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  const completeSSOLogin = async () => {
    try {
      setError(null);
      const result = await loadCurrentUser();
      if (!result.success) {
        throw new Error(result.error || 'SSO login failed');
      }

      return { success: true };
    } catch (err) {
      setUser(null);
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  const getMicrosoftLoginUrl = (returnTo = '/dashboard') =>
    `${API_BASE}/api/auth/sso/microsoft/start?return_to=${encodeURIComponent(returnTo)}`;

  const logout = async () => {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setUser(null);
      router.push('/auth/login');
    }
  };

  const refreshAccessToken = async () => {
    try {
      const { response } = await fetchJson('/api/auth/refresh', {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      return true;
    } catch (err) {
      console.error('Token refresh failed:', err);
      await logout();
      return false;
    }
  };

  const forgotPassword = async (email) => {
    try {
      setError(null);
      const { response, data } = await fetchJson('/api/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        throw new Error(data.detail || 'Password reset request failed');
      }

      return { success: true, message: data.message };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  const resetPassword = async (token, newPassword) => {
    try {
      setError(null);
      const { response, data } = await fetchJson('/api/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({
          token,
          new_password: newPassword,
        }),
      });

      if (!response.ok) {
        throw new Error(data.detail || 'Password reset failed');
      }

      return { success: true, message: data.message };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  const updateUser = (userData) => {
    setUser((prev) => ({ ...(prev || {}), ...userData }));
  };

  const verifyEmail = async (token) => {
    try {
      setError(null);
      const { response, data } = await fetchJson('/api/auth/verify-email', {
        method: 'POST',
        body: JSON.stringify({ token }),
      });

      if (!response.ok) {
        throw new Error(data.detail || 'Email verification failed');
      }

      if (user) {
        setUser({ ...user, is_verified: true });
      }

      return { success: true, message: data.message };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  const value = {
    user,
    loading,
    error,
    signup,
    login,
    loginWithGoogle,
    completeSSOLogin,
    getMicrosoftLoginUrl,
    logout,
    refreshAccessToken,
    forgotPassword,
    resetPassword,
    verifyEmail,
    updateUser,
    isAuthenticated: !!user,
    googleClientId: GOOGLE_CLIENT_ID,
    microsoftClientId: MICROSOFT_CLIENT_ID,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const withAuth = (Component) => {
  return (props) => {
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!loading && !user) {
        router.push('/auth/login');
      }
    }, [user, loading, router]);

    if (loading) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      );
    }

    if (!user) {
      return null;
    }

    return <Component {...props} />;
  };
};
