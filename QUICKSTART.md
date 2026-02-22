# MarketIntel — Quick Start Guide

Get up and running in under 5 minutes.

---

## Step 1: Install Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
playwright install chromium
python database/setup.py
```

**Frontend:**
```bash
cd frontend
npm install
```

---

## Step 2: Configure Environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set at minimum:
```env
JWT_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
```

Stripe keys are optional for local testing (billing features will be disabled).

---

## Step 3: Start Both Servers

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn api.main:app --reload
```
→ API running at http://localhost:8000

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```
→ App running at http://localhost:3000

---

## Step 4: Create Your Account

1. Open http://localhost:3000
2. Click **Sign Up** on the login page
3. Enter your email, password, and name
4. You're in — landing on the **Dashboard**

---

## Step 5: Add Your First Product

1. Click **Products** in the sidebar (or bottom nav on mobile)
2. Click the **+** FAB button (centre of bottom nav) or **Add Product** in the sidebar
3. Fill in the product title, brand, SKU, and optionally your price
4. Click **Create Product**

---

## Step 6: Find Competitor Prices

1. Open the product detail page
2. Click **Scrape Amazon** to search for matching products
3. Competitor matches appear with prices, stock status, and links
4. Price history is tracked automatically from that point on

---

## Step 7: Explore the Products Card Grid

Back on the Products page you'll see cards with:
- **MY PRICE** — click to edit inline
- **Stock badge** — In Stock / Low Stock / Out of Stock
- **Price position badge** — Lowest Price / Mid Range / Expensive
- **Sparkline** — 7-day price trend direction
- **Filter tabs** — All / Watchlist / Need Repricing / Low Stock
- **Bulk select** — checkbox per card, floating action bar appears

---

## Step 8: Configure Settings

Go to **Settings** (gear icon in sidebar / bottom nav):

| Tab | What you can do |
|---|---|
| Profile | Update name, change password |
| Billing | View current plan, upgrade, manage Stripe subscription |
| Notifications | Email / Slack / Discord alerts, digest frequency |
| API Access | Generate API key (Business+ tier) |
| Team | Invite team members (Business+ tier) |

---

## Project Layout

```
marketintel/
├── backend/
│   ├── api/main.py               # FastAPI entry point
│   ├── api/routes/               # All API routes
│   ├── database/                 # Models + connection
│   ├── scrapers/                 # Amazon + generic + crawler
│   ├── integrations/             # XML / WooCommerce / Shopify
│   └── services/                 # Business logic
├── frontend/
│   ├── pages/                    # Next.js pages
│   ├── components/Layout.js      # Sidebar + Topbar + BottomNav
│   ├── context/AuthContext.js    # JWT auth state
│   └── lib/api.js                # API client
└── data/marketintel.db           # SQLite database
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `No module named 'fastapi'` | `pip install -r backend/requirements.txt` |
| `Playwright browser not found` | `playwright install chromium` |
| `Cannot find module 'next'` | `cd frontend && npm install` |
| `No such table: users` | `cd backend && python database/setup.py` |
| Port 8000 in use | Change `API_PORT` in `backend/.env` |
| Port 3000 in use | Next.js auto-suggests 3001 |

---

## What's Available

- **Dashboard** — Actionable insights, opportunities, threats, KPIs
- **Products** — Card grid with inline price editing, filter tabs, bulk select
- **Competitors** — Manage competitor websites with custom CSS selectors
- **Alerts** — 10 alert types, email/Slack/Discord delivery
- **Integrations** — Import from XML, WooCommerce, Shopify, or auto-crawl
- **Pricing** — 4 subscription tiers (FREE → PRO → BUSINESS → ENTERPRISE)
- **Settings** — Profile, Billing, Notifications, API Access, Team

API docs: http://localhost:8000/docs
