# MarketIntel — System Status

**Last Updated:** 2026-02-22
**Status:** ✅ All systems operational

---

## Services

### Backend API
- **URL:** http://localhost:8000
- **Framework:** FastAPI + Uvicorn
- **Docs:** http://localhost:8000/docs

### Frontend Web App
- **URL:** http://localhost:3000
- **Framework:** Next.js 14

---

## Feature Completion

| # | Feature | Status | Endpoints |
|---|---|---|---|
| 1 | Authentication (JWT, signup, login, refresh, password reset) | ✅ Complete | 10 |
| 2 | User profile update & password change | ✅ Complete | 2 |
| 3 | Stripe billing (checkout, portal, webhooks, 4 tiers) | ✅ Complete | 4 |
| 4 | Product CRUD + pricing summary + my_price | ✅ Complete | 8 |
| 5 | Competitor website management | ✅ Complete | 6 |
| 6 | Amazon + generic scraper + site crawler | ✅ Complete | 5 |
| 7 | WooCommerce / Shopify / XML import | ✅ Complete | 6 |
| 8 | Price alerts (10 types, multi-channel) | ✅ Complete | 6 |
| 9 | Advanced filtering & saved views | ✅ Complete | 6 |
| 10 | Bulk repricing automation (5 strategies) | ✅ Complete | 13 |
| 11 | Competitor intelligence profiles | ✅ Complete | 8 |
| 12 | Historical analysis & price forecasting | ✅ Complete | 8 |
| 13 | Auto competitor discovery | ✅ Complete | 9 |
| 14 | Actionable insights dashboard | ✅ Complete | 7 |
| 15 | Mobile-first UI redesign (sidebar + topbar + bottom nav) | ✅ Complete | — |
| 16 | Product card grid with inline price editor & sparklines | ✅ Complete | — |
| 17 | Settings page (5 tabs) | ✅ Complete | — |
| **Total** | | **17 / 17** | **98+** |

---

## Frontend Pages

| Page | Path | Status |
|---|---|---|
| Login | `/auth/login` | ✅ |
| Signup | `/auth/signup` | ✅ |
| Forgot password | `/auth/forgot-password` | ✅ |
| Reset password | `/auth/reset-password` | ✅ |
| Dashboard (Insights) | `/dashboard` | ✅ |
| Products (card grid) | `/products` | ✅ |
| Add product | `/products/add` | ✅ |
| Product detail | `/products/[id]` | ✅ |
| Competitors | `/competitors` | ✅ |
| Add competitor | `/competitors/add` | ✅ |
| Alerts | `/alerts` | ✅ |
| Integrations | `/integrations` | ✅ |
| Pricing | `/pricing` | ✅ |
| Settings | `/settings` | ✅ |

---

## API Endpoints

### Authentication — `/api/auth/`
```
POST   /signup             Create account
POST   /login              Login
POST   /refresh            Refresh access token
GET    /me                 Get current user
PUT    /me                 Update profile (full_name)
POST   /change-password    Change password
POST   /forgot-password    Request password reset
POST   /reset-password     Reset password with token
GET    /verify-email/{t}   Verify email
POST   /logout             Logout
```

### Billing — `/api/billing/`
```
POST   /create-checkout-session   Start Stripe Checkout
POST   /create-portal-session     Open billing portal
GET    /subscription              Get subscription info
POST   /webhook                   Stripe webhook handler
```

### Products — `/products/`
```
GET    /                   List (with pricing summary)
POST   /                   Create
GET    /{id}               Get
PUT    /{id}               Update (title/sku/brand/image_url/my_price)
DELETE /{id}               Delete
GET    /{id}/matches        Competitor matches
GET    /{id}/price-history  Price history
POST   /{id}/scrape         Trigger scrape
```

### Analytics — `/api/analytics/`
```
GET    /products/{id}/trendline    Price trendline (days or date range)
GET    /products/{id}/date-range   Compare two date ranges
```

### Alerts — `/api/alerts/`
```
GET    /          List alerts
POST   /          Create alert
GET    /{id}       Get alert
PUT    /{id}       Update alert
DELETE /{id}       Delete alert
POST   /{id}/toggle  Enable/disable
```

### Competitors — `/competitors/`
```
GET    /           List
POST   /           Create
GET    /{id}        Get
PUT    /{id}        Update
DELETE /{id}        Delete
POST   /{id}/toggle Enable/disable
```

### Integrations — `/api/integrations/`
```
POST   /import/xml           Import XML feed
POST   /import/woocommerce   Import from WooCommerce
POST   /import/shopify       Import from Shopify
POST   /test/woocommerce     Test WooCommerce connection
POST   /test/shopify         Test Shopify connection
GET    /sample/xml           Get sample XML format
```

### Crawler — `/api/crawler/`
```
POST   /site                  Start site crawl
POST   /discover-categories   Discover categories
GET    /status/{crawl_id}     Crawl status
```

### Insights — `/api/insights/`
```
GET    /priorities            Today's action items
GET    /opportunities         Revenue opportunities
GET    /threats               Competitive risks
GET    /metrics               KPI summary
GET    /trending              Trending products
GET    /summary               Executive summary
GET    /products/{id}/opportunity-score
```

### Repricing — `/api/repricing/`
```
POST   /bulk/match-lowest     Match lowest price
POST   /bulk/undercut         Undercut competitors
POST   /bulk/margin-based     Margin-based pricing
POST   /bulk/dynamic          Dynamic pricing
POST   /bulk/check-map        MAP compliance check
POST   /rules                 Create rule
GET    /rules                 List rules
GET    /rules/{id}             Get rule
PUT    /rules/{id}             Update rule
DELETE /rules/{id}             Delete rule
POST   /rules/{id}/apply       Apply rule
POST   /rules/{id}/toggle      Enable/disable rule
```

### Forecasting — `/api/forecasting/`
### Competitor Intel — `/api/competitor-intel/`
### Discovery — `/api/discovery/`
### Filters — `/api/filters/`

_(See Swagger UI at http://localhost:8000/docs for full docs)_

---

## Subscription Tiers

| Tier | Products | Matches | Alerts |
|---|---|---|---|
| FREE | 5 | 10 | 1 |
| PRO | 50 | 100 | 10 |
| BUSINESS | 200 | 500 | 50 |
| ENTERPRISE | ∞ | ∞ | ∞ |

---

## Dependencies

### Backend
- fastapi, uvicorn, pydantic, sqlalchemy
- passlib[bcrypt], python-jose[cryptography]
- stripe, celery, redis
- playwright, beautifulsoup4, lxml
- sentence-transformers, torch
- requests, email-validator

### Frontend
- next 14, react 18, tailwindcss 3
- chart.js, axios

---

## Environment Variables (backend/.env)

```bash
DATABASE_URL=sqlite:///./marketintel.db
JWT_SECRET_KEY=<32-byte hex secret>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
CORS_ORIGINS=http://localhost:3000
REDIS_URL=redis://localhost:6379
```

---

## Health Checks

```bash
# Backend
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# Database
cd backend && python -c "from database.connection import SessionLocal; db = SessionLocal(); print('DB OK')"
```

---

## Production Checklist

- [ ] Use PostgreSQL instead of SQLite
- [ ] Set strong `JWT_SECRET_KEY`
- [ ] Configure real Stripe keys
- [ ] Set up Redis for Celery
- [ ] Configure SSL / HTTPS
- [ ] Set `CORS_ORIGINS` to production domain
- [ ] Enable database backups
- [ ] Set up monitoring (Sentry / Datadog)
- [ ] Deploy backend to Railway/Render
- [ ] Deploy frontend to Vercel
