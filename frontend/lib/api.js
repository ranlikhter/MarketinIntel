/**
 * MarketIntel API Client
 * Centralised fetch wrapper with auth header injection.
 */

const BASE = 'http://localhost:8000';

function getToken() {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('accessToken');
}

function buildHeaders(extra = {}) {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { ...buildHeaders(), ...(options.headers || {}) },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }

  // 204 No Content
  if (res.status === 204) return null;
  return res.json();
}

const api = {
  // ─── Products ────────────────────────────────────────────────────────────────
  getProducts: () => request('/products/'),
  getProduct: (id) => request(`/products/${id}`),
  createProduct: (data) =>
    request('/products/', { method: 'POST', body: JSON.stringify(data) }),
  updateProduct: (id, data) =>
    request(`/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProduct: (id) => request(`/products/${id}`, { method: 'DELETE' }),

  getProductMatches: (id) => request(`/products/${id}/matches`),
  getProductPriceHistory: (id) => request(`/products/${id}/price-history`),

  // CSV export — returns a Blob for download
  exportProductCSV: async (id) => {
    const token = getToken();
    const res = await fetch(`${BASE}/products/${id}/export.csv`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    return res.blob();
  },

  scrapeProduct: (id, website = 'amazon.com', maxResults = 5) =>
    request(
      `/products/${id}/scrape?website=${encodeURIComponent(website)}&max_results=${maxResults}`,
      { method: 'POST' }
    ),

  // ─── Competitors ─────────────────────────────────────────────────────────────
  getCompetitors: (activeOnly = false) =>
    request(`/competitors/?active_only=${activeOnly}`),
  getCompetitor: (id) => request(`/competitors/${id}`),
  createCompetitor: (data) =>
    request('/competitors/', { method: 'POST', body: JSON.stringify(data) }),
  updateCompetitor: (id, data) =>
    request(`/competitors/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteCompetitor: (id) => request(`/competitors/${id}`, { method: 'DELETE' }),
  toggleCompetitorStatus: (id) =>
    request(`/competitors/${id}/toggle`, { method: 'POST' }),

  // ─── Analytics ───────────────────────────────────────────────────────────────
  getProductTrendline: (id, days = 30) =>
    request(`/api/analytics/products/${id}/trendline?days=${days}`),
  getProductTrendlineCustom: (id, startDate, endDate) =>
    request(
      `/api/analytics/products/${id}/trendline?start_date=${startDate}&end_date=${endDate}`
    ),
  getDateRangeComparison: (id, s1, e1, s2, e2) =>
    request(
      `/api/analytics/products/${id}/date-range?start_date_1=${s1}&end_date_1=${e1}&start_date_2=${s2}&end_date_2=${e2}`
    ),

  // ─── Alerts ──────────────────────────────────────────────────────────────────
  getAlerts: (productId = null) =>
    request(`/api/alerts/${productId ? `?product_id=${productId}` : ''}`),
  createAlert: (data) =>
    request('/api/alerts/', { method: 'POST', body: JSON.stringify(data) }),
  updateAlert: (id, data) =>
    request(`/api/alerts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteAlert: (id) => request(`/api/alerts/${id}`, { method: 'DELETE' }),
  toggleAlert: (id) =>
    request(`/api/alerts/${id}/toggle`, { method: 'POST' }),

  // ─── Integrations ────────────────────────────────────────────────────────────
  importFromWooCommerce: (storeUrl, consumerKey, consumerSecret, importLimit = 100) =>
    request('/api/integrations/import/woocommerce', {
      method: 'POST',
      body: JSON.stringify({
        store_url: storeUrl,
        consumer_key: consumerKey,
        consumer_secret: consumerSecret,
        import_limit: importLimit,
      }),
    }),

  importFromShopify: (shopUrl, accessToken, importLimit = 100) =>
    request('/api/integrations/import/shopify', {
      method: 'POST',
      body: JSON.stringify({
        shop_url: shopUrl,
        access_token: accessToken,
        import_limit: importLimit,
      }),
    }),

  importFromXML: async (xmlFile, formatType) => {
    const formData = new FormData();
    formData.append('file', xmlFile);
    formData.append('format_type', formatType);
    const token = getToken();
    const res = await fetch(`${BASE}/api/integrations/import/xml`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Import failed');
    }
    return res.json();
  },

  // ─── Price Push ──────────────────────────────────────────────────────────────
  pushPriceToWooCommerce: (storeUrl, consumerKey, consumerSecret, sku, title, newPrice) =>
    request('/api/integrations/push-price/woocommerce', {
      method: 'POST',
      body: JSON.stringify({
        store_url: storeUrl,
        consumer_key: consumerKey,
        consumer_secret: consumerSecret,
        sku: sku || '',
        title: title || '',
        new_price: newPrice,
      }),
    }),

  pushPriceToShopify: (shopUrl, accessToken, sku, title, newPrice) =>
    request('/api/integrations/push-price/shopify', {
      method: 'POST',
      body: JSON.stringify({
        shop_url: shopUrl,
        access_token: accessToken,
        sku: sku || '',
        title: title || '',
        new_price: newPrice,
      }),
    }),

  // ─── Crawler ─────────────────────────────────────────────────────────────────
  startSiteCrawl: (url, maxProducts = 50, maxDepth = 3, autoImport = false, name = '') =>
    request('/api/crawler/site', {
      method: 'POST',
      body: JSON.stringify({
        url,
        max_products: maxProducts,
        max_depth: maxDepth,
        auto_import: autoImport,
        name,
      }),
    }),

  // ─── Generic passthrough ─────────────────────────────────────────────────────
  request: (path, options = {}) => request(path, options),
};

export default api;
