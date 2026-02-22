# MarketIntel — Complete Feature Summary

**Status:** Production-ready SaaS platform ✅

---

## Authentication & Accounts

- JWT-based auth (HS256) — 24h access tokens, 30d refresh tokens
- Signup, login, email verification, password reset
- Profile update (`PUT /api/auth/me`) and password change (`POST /api/auth/change-password`)
- User-scoped data isolation (multi-tenant)
- Usage limits enforced at API level per subscription tier

## Subscription Billing (Stripe)

- 4 tiers: FREE / PRO ($49/mo) / BUSINESS ($149/mo) / ENTERPRISE
- Stripe Checkout and Customer Portal
- Webhook handler for subscription lifecycle events
- Automatic tier upgrade/downgrade with limit sync

## Product Monitoring

- Add, edit, delete products (title, brand, SKU, image, `my_price`)
- Pricing summary computed per product:
  - `lowest_price`, `avg_price`, `in_stock_count`
  - `price_position`: cheapest / mid / expensive
  - `price_change_pct`: 7-day trend
- Price history tracked automatically on each scrape

## Competitor Management

- Add custom competitor websites with CSS selectors
- Active/inactive toggle
- Scrape any website (Amazon specialist + generic)
- Auto site crawler — discovers full competitor catalogs

## Product Import

- XML / Google Shopping Feed upload
- WooCommerce REST API import
- Shopify Admin API import

## Price Alerts (10 types)

1. Price Drop
2. Price Increase
3. Any Change
4. Competitor Out of Stock (opportunity)
5. Price War (3+ competitors dropped in 24h)
6. New Competitor
7. You're Most Expensive
8. Competitor Raised Price (opportunity)
9. Back In Stock
10. Market Trend

**Delivery channels:** Email, SMS, Slack, Discord, Push
**Modes:** Instant, daily digest, weekly digest, quiet hours

## Advanced Filtering & Saved Views

- Filter by price position, competition level, activity, opportunity score
- Fuzzy full-text search
- Saved views with usage tracking and team sharing

## Bulk Repricing Automation

- Match Lowest — match cheapest competitor ± margin
- Undercut — price below all competitors by amount or %
- Margin-Based — cost + desired markup
- Dynamic — multi-factor (stock, competition, demand)
- MAP Protected — never below Minimum Advertised Price
- Rule engine with priority and approval workflows

## Competitor Intelligence

- Per-competitor pricing strategy detection
- Win-rate, volatility, stock availability stats
- Head-to-head product comparison
- Market positioning analysis

## Historical Analysis & Forecasting

- Linear-regression price forecasting with confidence intervals
- Seasonal pattern detection (day of week, monthly)
- Best time to buy recommendations
- Price statistics (min/max/avg/median/std dev)

## Auto Competitor Discovery

- Keyword-based multi-site search
- Confidence-scored match suggestions
- Batch discovery with approval/rejection workflow

## Actionable Insights Dashboard

- Today's priorities (most expensive, out-of-stock competitors, price wars)
- Opportunities (raise price, low competition, bundling)
- Threats (aggressive competitors, market drops)
- KPI cards + trending products widget

---

## Frontend

### Layout (all pages)
- Fixed sidebar — desktop (w-64), with navigation, Add Product CTA, user dropdown
- Fixed topbar — search bar, avatar dropdown
- Fixed bottom nav with centre FAB — mobile only (`lg:hidden`)

### Products Page
- Card grid (1 → 2 → 3 columns responsive)
- Inline `my_price` editor (click to edit, save on blur/Enter, cancel on Escape)
- Stock badge (In Stock / Low Stock / Out of Stock)
- Price position badge (Lowest Price / Mid Range / Expensive)
- Sparkline (7-point trend from `price_change_pct`)
- Filter tabs: All / Watchlist / Need Repricing / Low Stock
- Bulk select + floating action bar (Export, Reprice)
- Loading skeleton

### Settings Page (5 tabs)
- **Profile** — Edit name, change password with strength meter
- **Billing** — Plan card with tier badge, usage meters (amber at 70%, red at 90%), Stripe portal
- **Notifications** — Frequency, Email/Slack/Discord webhooks, quiet hours
- **API Access** — Generate/copy/revoke API key (Business+)
- **Team** — Invite members with role selector, permission table (Business+)

### Auth Pages
- Login, Signup, Forgot Password, Reset Password — consistent gradient design

### Other Pages
- Dashboard (Insights)
- Product detail with price chart
- Competitor management
- Alert management
- Integrations import wizard
- Pricing page (FREE / PRO / BUSINESS / ENTERPRISE)

---

## API Endpoints (100+)

See http://localhost:8000/docs for the full interactive reference.

Key route groups:
- `/api/auth/` — 10 endpoints
- `/api/billing/` — 4 endpoints
- `/products/` — 8 endpoints
- `/competitors/` — 6 endpoints
- `/api/alerts/` — 6 endpoints
- `/api/analytics/` — 2 endpoints
- `/api/insights/` — 7 endpoints
- `/api/filters/` — 6 endpoints
- `/api/repricing/` — 13 endpoints
- `/api/competitor-intel/` — 8 endpoints
- `/api/forecasting/` — 8 endpoints
- `/api/discovery/` — 9 endpoints
- `/api/integrations/` — 6 endpoints
- `/api/crawler/` — 3 endpoints

---

## Tech Stack

**Backend:** FastAPI, SQLAlchemy, SQLite/PostgreSQL, passlib/bcrypt, python-jose (JWT), Stripe, Celery, Redis, Playwright, BeautifulSoup4, sentence-transformers

**Frontend:** Next.js 14, React 18, Tailwind CSS 3, Chart.js

---

## How to Run

```bash
# Backend
cd backend && uvicorn api.main:app --reload

# Frontend
cd frontend && npm run dev
```

Open http://localhost:3000, create an account, and start monitoring.
