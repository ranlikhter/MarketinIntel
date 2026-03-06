// MarketIntel Service Worker — v1
// Strategy:
//   /_next/static/**  → cache-first  (immutable hashed assets)
//   /icons/**         → cache-first
//   /api/**           → network-first, fallback to cache (read-only GET)
//   navigation pages  → network-first, fallback to cache then /offline
//   non-GET           → always network (mutations must go through)

const SW_VERSION = 'v1';
const STATIC_CACHE  = `mi-static-${SW_VERSION}`;
const PAGES_CACHE   = `mi-pages-${SW_VERSION}`;
const API_CACHE     = `mi-api-${SW_VERSION}`;

// Pages to pre-cache so the app shell is always available
const PRECACHE_PAGES = [
  '/',
  '/offline',
  '/products',
  '/dashboard',
  '/insights',
  '/alerts',
  '/manifest.json',
  '/favicon.svg',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

// ─── Install ─────────────────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(PAGES_CACHE).then((cache) =>
      // addAll fails silently per-URL if the page isn't reachable during install
      Promise.allSettled(PRECACHE_PAGES.map((url) => cache.add(url)))
    )
  );
  // Don't wait for old SW to finish — take control immediately
  self.skipWaiting();
});

// ─── Activate ────────────────────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  const VALID = new Set([STATIC_CACHE, PAGES_CACHE, API_CACHE]);
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => !VALID.has(k)).map((k) => caches.delete(k)))
    )
  );
  // Claim all open clients so the new SW takes effect without a reload
  self.clients.claim();
});

// ─── Fetch ────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin GET requests
  if (request.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;

  // /_next/static/ — hashed, immutable → cache-first forever
  if (url.pathname.startsWith('/_next/static/') || url.pathname.startsWith('/icons/')) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // /api/* or backend proxy — network-first, cache for offline reads
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request, API_CACHE, 5000));
    return;
  }

  // Navigation requests (HTML pages) — network-first with offline fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      networkFirst(request, PAGES_CACHE, 4000).catch(() =>
        caches.match('/offline').then((r) => r ?? new Response('Offline', { status: 503 }))
      )
    );
    return;
  }

  // Everything else (fonts, images, etc.) — stale-while-revalidate
  event.respondWith(staleWhileRevalidate(request, PAGES_CACHE));
});

// ─── Strategies ───────────────────────────────────────────────────────────────

/** Serve from cache immediately; on miss fetch & cache. */
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(cacheName);
    cache.put(request, response.clone());
  }
  return response;
}

/** Try network first (with timeout); on failure return cached version. */
async function networkFirst(request, cacheName, timeoutMs = 5000) {
  const cache = await caches.open(cacheName);

  try {
    const networkResponse = await Promise.race([
      fetch(request),
      new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), timeoutMs)),
    ]);

    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone()); // background update
    }
    return networkResponse;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw new Error('Network and cache both failed');
  }
}

/** Return cache immediately AND revalidate in background. */
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  const networkFetch = fetch(request).then((response) => {
    if (response.ok) cache.put(request, response.clone());
    return response;
  });

  return cached ?? networkFetch;
}

// ─── Background Sync ──────────────────────────────────────────────────────────
// Queue failed write operations (alerts, price updates) and replay when online
self.addEventListener('sync', (event) => {
  if (event.tag === 'mi-sync-queue') {
    event.waitUntil(replaySyncQueue());
  }
});

const SYNC_STORE = 'mi-sync-queue';

async function replaySyncQueue() {
  const db = await openSyncDB();
  const items = await dbGetAll(db);
  for (const item of items) {
    try {
      const response = await fetch(item.url, {
        method: item.method,
        headers: item.headers,
        body: item.body,
      });
      if (response.ok) await dbDelete(db, item.id);
    } catch {
      // Leave in queue — will retry on next sync
    }
  }
}

// Minimal IndexedDB wrapper for the sync queue
function openSyncDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('mi-sync', 1);
    req.onupgradeneeded = () => req.result.createObjectStore(SYNC_STORE, { keyPath: 'id', autoIncrement: true });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
function dbGetAll(db) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(SYNC_STORE, 'readonly');
    const req = tx.objectStore(SYNC_STORE).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
function dbDelete(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(SYNC_STORE, 'readwrite');
    const req = tx.objectStore(SYNC_STORE).delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

// ─── Push Notifications ───────────────────────────────────────────────────────
self.addEventListener('push', (event) => {
  if (!event.data) return;

  let data;
  try {
    data = event.data.json();
  } catch {
    data = { title: 'MarketIntel Alert', body: event.data.text() };
  }

  const options = {
    body: data.body ?? '',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    tag: data.tag ?? 'mi-alert',
    data: { url: data.url ?? '/' },
    requireInteraction: data.urgent ?? false,
    actions: data.actions ?? [],
  };

  event.waitUntil(self.registration.showNotification(data.title ?? 'MarketIntel', options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url ?? '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      const existing = clients.find((c) => c.url === targetUrl && 'focus' in c);
      if (existing) return existing.focus();
      return self.clients.openWindow(targetUrl);
    })
  );
});
