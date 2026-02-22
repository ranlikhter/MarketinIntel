# MarketIntel — E-commerce Competitive Intelligence SaaS

A full-stack SaaS platform for monitoring competitor pricing across e-commerce platforms. Built with FastAPI, Next.js, Tailwind CSS, and Stripe.

## Live Features

| Category | Status |
|---|---|
| JWT Authentication (signup / login / refresh / password reset) | ✅ |
| User profile update & password change | ✅ |
| Stripe billing (checkout, portal, webhooks) | ✅ |
| 4 subscription tiers with usage limit enforcement | ✅ |
| Product monitoring with pricing summary | ✅ |
| Competitor website management | ✅ |
| Amazon scraper + generic web scraper | ✅ |
| Auto site crawler | ✅ |
| WooCommerce / Shopify / XML import | ✅ |
| Price alerts (10 types, multi-channel) | ✅ |
| Advanced filtering & saved views | ✅ |
| Bulk repricing automation (5 strategies) | ✅ |
| Competitor intelligence profiles | ✅ |
| Historical analysis & price forecasting | ✅ |
| Auto competitor discovery | ✅ |
| Actionable insights dashboard | ✅ |
| Mobile-first UI (sidebar + topbar + bottom nav) | ✅ |
| Settings page (Profile / Billing / Notifications / API / Team) | ✅ |

---

## Prerequisites

- Python 3.11+
- Node.js 20+

---

## Installation

### 1. Backend

```bash
pip install -r backend/requirements.txt
playwright install chromium
```

### 2. Frontend

```bash
cd frontend
npm install
```

### 3. Environment

Copy `backend/.env.example` to `backend/.env` and fill in:

```env
DATABASE_URL=sqlite:///./marketintel.db
JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
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

## Running

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn api.main:app --reload
```
API: http://localhost:8000 · Docs: http://localhost:8000/docs

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```
App: http://localhost:3000

**Terminal 3 — Celery worker (optional, for alerts & background tasks):**
```bash
cd backend
celery -A tasks.celery_app worker --loglevel=info
```

---

## Project Structure

```
marketintel/
├── backend/
│   ├── api/
│   │   ├── main.py                  # FastAPI app, router registration
│   │   ├── dependencies.py          # Auth middleware, usage limit helpers
│   │   └── routes/
│   │       ├── auth.py              # Signup, login, refresh, me, password
│   │       ├── billing.py           # Stripe checkout, portal, webhooks
│   │       ├── products.py          # CRUD + pricing summary
│   │       ├── competitors.py       # Competitor websites
│   │       ├── alerts.py            # Price alerts (10 types)
│   │       ├── analytics.py         # Trendline, date-range comparison
│   │       ├── insights.py          # Actionable insights dashboard
│   │       ├── filters.py           # Advanced filtering & saved views
│   │       ├── repricing.py         # Bulk repricing rules
│   │       ├── competitor_intel.py  # Competitor profiles
│   │       ├── forecasting.py       # Price forecasting
│   │       ├── discovery.py         # Auto competitor discovery
│   │       ├── integrations.py      # XML / WooCommerce / Shopify import
│   │       └── crawler.py           # Auto site crawler
│   ├── database/
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── connection.py            # DB session factory
│   │   └── setup.py                 # Table creation
│   ├── scrapers/                    # Amazon, generic, site crawler
│   ├── integrations/                # XML, WooCommerce, Shopify parsers
│   ├── services/                    # Business logic services
│   └── requirements.txt
├── frontend/
│   ├── pages/
│   │   ├── auth/                    # login, signup, forgot/reset password
│   │   ├── dashboard/               # Insights + comparison dashboard
│   │   ├── products/                # Card grid, add, detail [id]
│   │   ├── competitors/             # List, add, detail [id]
│   │   ├── alerts/                  # Alert management
│   │   ├── integrations/            # Import wizard
│   │   ├── pricing.js               # Pricing tiers page
│   │   └── settings/                # 5-tab settings page
│   ├── components/
│   │   ├── Layout.js                # Sidebar + Topbar + BottomNav
│   │   ├── Toast.js                 # Toast notification system
│   │   └── ...
│   ├── context/
│   │   └── AuthContext.js           # JWT auth state + helpers
│   ├── lib/
│   │   └── api.js                   # Centralised fetch client
│   └── styles/
│       └── globals.css              # Tailwind base + utilities
└── data/                            # SQLite database
```

---

## API Reference

### Authentication (`/api/auth/`)
| Method | Path | Description |
|---|---|---|
| POST | `/signup` | Create account, returns JWT pair |
| POST | `/login` | Login, returns JWT pair |
| POST | `/refresh` | Refresh access token |
| GET | `/me` | Get current user |
| PUT | `/me` | Update profile (full_name) |
| POST | `/change-password` | Change password |
| POST | `/forgot-password` | Request password reset email |
| POST | `/reset-password` | Reset password with token |
| GET | `/verify-email/{token}` | Verify email address |
| POST | `/logout` | Logout |

### Billing (`/api/billing/`)
| Method | Path | Description |
|---|---|---|
| POST | `/create-checkout-session` | Start Stripe Checkout |
| POST | `/create-portal-session` | Open Stripe billing portal |
| GET | `/subscription` | Get subscription info |
| POST | `/webhook` | Stripe webhook handler |

### Products (`/products/`)
| Method | Path | Description |
|---|---|---|
| GET | `/` | List products with pricing summary |
| POST | `/` | Create product |
| GET | `/{id}` | Get product details |
| PUT | `/{id}` | Update product (title, sku, brand, image_url, my_price) |
| DELETE | `/{id}` | Delete product |
| GET | `/{id}/matches` | Get competitor matches |
| GET | `/{id}/price-history` | Get price history |
| POST | `/{id}/scrape` | Trigger Amazon scrape |

Pricing summary fields returned on list: `lowest_price`, `avg_price`, `in_stock_count`, `price_position` (cheapest/mid/expensive), `price_change_pct`.

### Full API docs: http://localhost:8000/docs

---

## Subscription Tiers

| Tier | Price | Products | Matches | Alerts |
|---|---|---|---|---|
| FREE | $0 | 5 | 10 | 1 |
| PRO | $49/mo | 50 | 100 | 10 |
| BUSINESS | $149/mo | 200 | 500 | 50 |
| ENTERPRISE | Custom | Unlimited | Unlimited | Unlimited |

---

## UI Design

The frontend uses a **mobile-first design** with:

- **Sidebar** (desktop): Fixed left, `w-64`, logo + navigation + user avatar dropdown
- **Topbar**: Fixed top, search bar (desktop), avatar (mobile)
- **Bottom navigation**: Fixed bottom with centre FAB, hidden on desktop
- **Product cards**: 80×80px image, SKU, stock badge, price-position badge, inline `my_price` editor, sparkline, competitor count
- **Filter tabs**: All / Watchlist / Need Repricing / Low Stock
- **Bulk actions**: Floating bar with Export and Reprice buttons

---

## Troubleshooting

**Backend won't start**
```bash
pip install -r backend/requirements.txt
python -c "from api import main"   # check imports
```

**Frontend won't start**
```bash
cd frontend && npm install
rm -rf .next && npm run dev
```

**Database errors**
```bash
cd backend && python database/setup.py
```

**Playwright not found**
```bash
playwright install chromium
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Uvicorn |
| ORM | SQLAlchemy |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Auth | JWT (HS256), passlib/bcrypt |
| Payments | Stripe |
| Background jobs | Celery + Redis |
| Web scraping | Playwright + BeautifulSoup4 |
| AI matching | sentence-transformers |
| Frontend | Next.js 14 + React 18 |
| Styling | Tailwind CSS 3 |
| Charts | Chart.js |

---

## Deployment

- **Backend**: Railway, Render, or any Docker host
- **Frontend**: Vercel (recommended for Next.js)
- **Database**: Migrate to PostgreSQL for production
- **Environment**: Set all `.env` variables on your host

---

## License

MIT — free for personal and commercial use.
