/**
 * MarketIntel API Client
 * Centralized fetch wrapper with secure cookie auth.
 */

const BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

function buildHeaders(options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  return headers;
}

async function tryRefreshSession() {
  const response = await fetch(`${BASE}/api/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  });
  return response.ok;
}

async function request(path, options = {}, canRetry = true) {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    ...options,
    headers: buildHeaders(options),
  });

  if (res.status === 401 && canRetry && path !== '/api/auth/refresh') {
    const refreshed = await tryRefreshSession();
    if (refreshed) {
      return request(path, options, false);
    }
  }

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
  getProducts: () => request('/api/products/'),
  getHomeCatalogSummary: () => request('/api/products/summary'),
  getProduct: (id) => request(`/api/products/${id}`),
  createProduct: (data) =>
    request('/api/products/', { method: 'POST', body: JSON.stringify(data) }),
  updateProduct: (id, data) =>
    request(`/api/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProduct: (id) => request(`/api/products/${id}`, { method: 'DELETE' }),

  getProductMatches: (id) => request(`/api/products/${id}/matches`),
  getProductPriceHistory: (id) => request(`/api/products/${id}/price-history`),

  // CSV export — returns a Blob for download
  exportProductCSV: async (id) => {
    const res = await fetch(`${BASE}/api/products/${id}/export.csv`, {
      credentials: 'include',
    });
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    return res.blob();
  },

  scrapeProduct: (id, website = 'amazon.com', maxResults = 5) =>
    request(
      `/api/products/${id}/scrape?website=${encodeURIComponent(website)}&max_results=${maxResults}`,
      { method: 'POST' }
    ),

  /**
   * Manually pin a specific competitor URL to a product.
   * The backend scrapes the page, extracts all price/stock/meta fields,
   * creates (or refreshes) a CompetitorMatch with match_score=100, and
   * returns the full match object so the UI can render it immediately.
   */
  scrapeProductUrl: (productId, competitorUrl, competitorName = null) =>
    request(`/api/products/${productId}/scrape-url`, {
      method: 'POST',
      body: JSON.stringify({
        competitor_url: competitorUrl,
        ...(competitorName ? { competitor_name: competitorName } : {}),
      }),
    }),

  // ─── Competitors ─────────────────────────────────────────────────────────────
  getCompetitors: (activeOnly = false) =>
    request(`/api/competitors/?active_only=${activeOnly}`),
  getCompetitor: (id) => request(`/api/competitors/${id}`),
  createCompetitor: (data) =>
    request('/api/competitors/', { method: 'POST', body: JSON.stringify(data) }),
  updateCompetitor: (id, data) =>
    request(`/api/competitors/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteCompetitor: (id) => request(`/api/competitors/${id}`, { method: 'DELETE' }),
  toggleCompetitorStatus: (id) =>
    request(`/api/competitors/${id}/toggle`, { method: 'POST' }),

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
    const res = await fetch(`${BASE}/api/integrations/import/xml`, {
      method: 'POST',
      credentials: 'include',
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

  // ─── My Price History ─────────────────────────────────────────────────────────
  getMyPriceHistory: (id) => request(`/api/products/${id}/my-price-history`),

  // ─── Competitor Intelligence ──────────────────────────────────────────────────
  getCompetitorComparison: (names = []) => {
    const qs = names.map((n) => `competitors=${encodeURIComponent(n)}`).join('&');
    return request(`/api/competitor-intel/compare${qs ? `?${qs}` : ''}`);
  },
  getCompetitorStrategies: () => request('/api/competitor-intel/strategies'),
  getCompetitorProfile: (name) =>
    request(`/api/competitor-intel/competitors/${encodeURIComponent(name)}`),

  // ─── Excel export ─────────────────────────────────────────────────────────────
  exportProductXLSX: async (id) => {
    const res = await fetch(`${BASE}/api/products/${id}/export.xlsx`, {
      credentials: 'include',
    });
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    return res.blob();
  },

  // ─── API Keys ─────────────────────────────────────────────────────────────────
  getApiKeys: () => request('/api/auth/api-keys'),
  createApiKey: (name) =>
    request('/api/auth/api-keys', { method: 'POST', body: JSON.stringify({ name }) }),
  deleteApiKey: (id) => request(`/api/auth/api-keys/${id}`, { method: 'DELETE' }),
  rotateApiKey: (id) => request(`/api/auth/api-keys/${id}/rotate`, { method: 'POST' }),

  // ─── Workspaces ───────────────────────────────────────────────────────────────
  getWorkspaces: () => request('/api/workspaces'),
  createWorkspace: (name) =>
    request('/api/workspaces', { method: 'POST', body: JSON.stringify({ name }) }),
  getWorkspace: (id) => request(`/api/workspaces/${id}`),
  updateWorkspace: (id, name) =>
    request(`/api/workspaces/${id}`, { method: 'PUT', body: JSON.stringify({ name }) }),
  deleteWorkspace: (id) => request(`/api/workspaces/${id}`, { method: 'DELETE' }),
  selectWorkspace: (id) => request(`/api/workspaces/${id}/select`, { method: 'POST' }),
  inviteMember: (wsId, email, role = 'viewer') =>
    request(`/api/workspaces/${wsId}/members`, {
      method: 'POST',
      body: JSON.stringify({ email, role }),
    }),
  updateMemberRole: (wsId, uid, role) =>
    request(`/api/workspaces/${wsId}/members/${uid}`, {
      method: 'PUT',
      body: JSON.stringify({ role }),
    }),
  removeMember: (wsId, uid) =>
    request(`/api/workspaces/${wsId}/members/${uid}`, { method: 'DELETE' }),

  // ─── Saved Views ──────────────────────────────────────────────────────────────
  getSavedViews: () => request('/api/filters/views'),
  createSavedView: (data) =>
    request('/api/filters/views', { method: 'POST', body: JSON.stringify(data) }),
  deleteSavedView: (id) => request(`/api/filters/views/${id}`, { method: 'DELETE' }),
  duplicateSavedView: (id) =>
    request(`/api/filters/views/${id}/duplicate`, { method: 'POST' }),

  // ─── Store Connections ────────────────────────────────────────────────────────
  getStoreConnections: () => request('/api/integrations/store-connections'),
  saveStoreConnection: (data) =>
    request('/api/integrations/store-connections', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  deleteStoreConnection: (id) =>
    request(`/api/integrations/store-connections/${id}`, { method: 'DELETE' }),
  syncStoreInventory: (id) =>
    request(`/api/integrations/store-connections/${id}/sync`, { method: 'POST' }),

  // ─── Activity Log ─────────────────────────────────────────────────────────────
  getActivity: ({ page = 1, limit = 50, category, action, entityId, days } = {}) => {
    const params = new URLSearchParams({ page, limit });
    if (category) params.set('category', category);
    if (action)   params.set('action', action);
    if (entityId) params.set('entity_id', entityId);
    if (days)     params.set('days', days);
    return request(`/api/activity?${params}`);
  },

  // ─── Forecasting ──────────────────────────────────────────────────────────────
  getForecastHistory:   (productId, days = 90) =>
    request(`/api/forecasting/products/${productId}/history?days=${days}`),
  getForecast:          (productId, daysAhead = 30) =>
    request(`/api/forecasting/products/${productId}/forecast?days_ahead=${daysAhead}`),
  getSeasonalPatterns:  (productId, months = 12) =>
    request(`/api/forecasting/products/${productId}/seasonal?months=${months}`),
  getCompetitorPerf:    (competitorName, days = 90) =>
    request(`/api/forecasting/competitors/${encodeURIComponent(competitorName)}/performance?days=${days}`),
  getPriceDrops:        (days = 30, minDropPct = 10) =>
    request(`/api/forecasting/price-drops?days=${days}&min_drop_pct=${minDropPct}`),
  getForecastSummary:   () =>
    request('/api/forecasting/trends/summary'),

  // ─── Push Notifications ───────────────────────────────────────────────────────
  getPushVapidKey: () =>
    request('/api/notifications/push/vapid-public-key'),
  subscribePush: (endpoint, p256dh, auth, userAgent) =>
    request('/api/notifications/push/subscribe', {
      method: 'POST',
      body: JSON.stringify({ endpoint, p256dh, auth, user_agent: userAgent }),
    }),
  unsubscribePush: (endpoint) =>
    request('/api/notifications/push/unsubscribe', {
      method: 'DELETE',
      body: JSON.stringify({ endpoint }),
    }),
  sendTestPush: () =>
    request('/api/notifications/push/test', { method: 'POST' }),

  // ─── Promotions ───────────────────────────────────────────────────────────────
  getPromotions: ({ days = 30, promoType, competitor, activeOnly = true } = {}) => {
    const params = new URLSearchParams({ days, active_only: activeOnly });
    if (promoType) params.set('promo_type', promoType);
    if (competitor) params.set('competitor', competitor);
    return request(`/api/promotions?${params}`);
  },
  getPromotionStats: (days = 30) =>
    request(`/api/promotions/stats?days=${days}`),

  // ─── Competitor Strategy DNA ──────────────────────────────────────────────────
  getDnaProfiles: () =>
    request('/api/competitor-dna/profiles'),
  getDnaProfile: (competitorName) =>
    request(`/api/competitor-dna/profiles/${encodeURIComponent(competitorName)}`),
  getDnaStrikePredictions: () =>
    request('/api/competitor-dna/strike-predictions'),
  classifyPriceChange: (competitorName, productId, oldPrice, newPrice) =>
    request('/api/competitor-dna/classify', {
      method: 'POST',
      body: JSON.stringify({
        competitor_name: competitorName,
        product_id: productId,
        old_price: oldPrice,
        new_price: newPrice,
      }),
    }),
  simulateReprice: (productId, proposedPrice) =>
    request('/api/competitor-dna/simulate', {
      method: 'POST',
      body: JSON.stringify({ product_id: productId, proposed_price: proposedPrice }),
    }),

  // ─── Product Health & Review Velocity ─────────────────────────────────────────
  getPortfolioHealth: () =>
    request('/api/product-health/portfolio'),
  getProductHealth: (productId) =>
    request(`/api/product-health/products/${productId}`),
  getReviewVelocityTrend: (matchId, days = 30) =>
    request(`/api/product-health/velocity/${matchId}?days=${days}`),

  // ─── Seller Intelligence ──────────────────────────────────────────────────────
  getSellerOverview: () =>
    request('/api/seller-intel/overview'),
  getAmazonThreats: () =>
    request('/api/seller-intel/amazon-threats'),
  getSellerProfile: (sellerName) =>
    request(`/api/seller-intel/sellers/${encodeURIComponent(sellerName)}`),
  getBuyboxVolatility: (productId) =>
    request(`/api/seller-intel/buybox-volatility/${productId}`),

  // ─── Listing Quality ─────────────────────────────────────────────────────────
  getPortfolioListingGaps: () =>
    request('/api/listing-quality/portfolio'),
  getListingComparison: (productId) =>
    request(`/api/listing-quality/products/${productId}`),
  getListingTrends: (matchId, days = 60) =>
    request(`/api/listing-quality/trends/${matchId}?days=${days}`),

  // ─── Keyword Ranks ────────────────────────────────────────────────────────────
  getPortfolioKeywords: () =>
    request('/api/keyword-ranks/summary'),
  getRankMovements: (days = 7) =>
    request(`/api/keyword-ranks/movements?days=${days}`),
  getProductKeywords: (productId) =>
    request(`/api/keyword-ranks/products/${productId}`),
  getKeywordTrend: (productId, keyword, days = 30) =>
    request(`/api/keyword-ranks/trends/${productId}?keyword=${encodeURIComponent(keyword)}&days=${days}`),
  addKeyword: (productId, keyword) =>
    request(`/api/keyword-ranks/products/${productId}/keywords`, {
      method: 'POST',
      body: JSON.stringify({ keyword }),
    }),

  // ─── Custom Dashboards ────────────────────────────────────────────────────────
  getDashboards: () =>
    request('/api/dashboards'),
  createDashboard: (data) =>
    request('/api/dashboards', { method: 'POST', body: JSON.stringify(data) }),
  getDashboard: (id) =>
    request(`/api/dashboards/${id}`),
  updateDashboard: (id, data) =>
    request(`/api/dashboards/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteDashboard: (id) =>
    request(`/api/dashboards/${id}`, { method: 'DELETE' }),

  addWidget: (dashboardId, data) =>
    request(`/api/dashboards/${dashboardId}/widgets`, { method: 'POST', body: JSON.stringify(data) }),
  updateWidget: (dashboardId, widgetId, data) =>
    request(`/api/dashboards/${dashboardId}/widgets/${widgetId}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteWidget: (dashboardId, widgetId) =>
    request(`/api/dashboards/${dashboardId}/widgets/${widgetId}`, { method: 'DELETE' }),
  saveDashboardLayout: (dashboardId, layout) =>
    request(`/api/dashboards/${dashboardId}/layout`, { method: 'PUT', body: JSON.stringify(layout) }),

  getWidgetData: (widgetType, params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null))
    ).toString();
    return request(`/api/dashboards/widget-data/${widgetType}${qs ? '?' + qs : ''}`);
  },

  // ─── Scrape API (Firecrawl-compatible) ───────────────────────────────────────
  scrapeUrl: (data) =>
    request('/api/scrape', { method: 'POST', body: JSON.stringify(data) }),
  startCrawl: (data) =>
    request('/api/scrape/crawl', { method: 'POST', body: JSON.stringify(data) }),
  getCrawlJob: (jobId) => request(`/api/scrape/jobs/${jobId}`),
  mapSite: (data) =>
    request('/api/scrape/map', { method: 'POST', body: JSON.stringify(data) }),
  agentExtract: (data) =>
    request('/api/scrape/agent', { method: 'POST', body: JSON.stringify(data) }),

  // ─── Generic passthrough ─────────────────────────────────────────────────────
  request: (path, options = {}) => request(path, options),
};

export default api;
