import { createContext, useContext, useEffect, useState } from 'react';

const PwaContext = createContext({ canInstall: false, install: () => {}, isOnline: true });

export function usePwa() {
  return useContext(PwaContext);
}

export function PwaProvider({ children }) {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [canInstall, setCanInstall] = useState(false);
  const [isOnline, setIsOnline]     = useState(true);

  useEffect(() => {
    // ── Service worker registration ────────────────────────────────────────
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/sw.js', { scope: '/' })
        .then((reg) => {
          reg.addEventListener('updatefound', () => {
            const worker = reg.installing;
            worker?.addEventListener('statechange', () => {
              if (worker.state === 'installed' && navigator.serviceWorker.controller) {
                console.log('[SW] new version available');
              }
            });
          });
        })
        .catch((err) => console.warn('[SW] registration failed:', err));
    }

    // ── Install prompt ─────────────────────────────────────────────────────
    const onPrompt = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setCanInstall(true);
    };
    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', () => {
      setCanInstall(false);
      setDeferredPrompt(null);
    });

    // ── Online / Offline ───────────────────────────────────────────────────
    setIsOnline(navigator.onLine);
    const goOnline  = () => { setIsOnline(true);  localStorage.setItem('mi_last_sync', new Date().toISOString()); };
    const goOffline = () => setIsOnline(false);
    window.addEventListener('online',  goOnline);
    window.addEventListener('offline', goOffline);
    if (navigator.onLine) localStorage.setItem('mi_last_sync', new Date().toISOString());

    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('online',  goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, []);

  async function install() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      setCanInstall(false);
      setDeferredPrompt(null);
    }
  }

  return (
    <PwaContext.Provider value={{ canInstall, install, isOnline }}>
      {children}
    </PwaContext.Provider>
  );
}
