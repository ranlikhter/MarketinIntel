# CLAUDE.md — MarketIntel Project Reference

## How to Use This File

1. **Read this file first** — before exploring any code.
2. **Trust the patterns here** — do NOT re-verify by reading files you aren't changing.
3. **Use Grep/Glob for targeted lookups**; use Read only for files you will edit.
4. **After completing work**, update the "Pending / Completed Work Log" section.
5. **Never rebuild context from scratch** — this file IS the context.

---

## 1. Project Snapshot

MarketIntel is a multi-tenant SaaS price-intelligence platform. Users add their own products,
the system scrapes competitor URLs and records price history, then surfaces alerts, repricing
suggestions, analytics, and AI-generated narratives. Tech stack: **FastAPI + SQLAlchemy +
PostgreSQL/SQLite + Celery/Redis** (backend), **Next.js 15 + TailwindCSS** (frontend),
**Playwright + BeautifulSoup + Apify** (scraping), **Claude API** (AI features), **Stripe** (billing).
Monorepo: `backend/` and `frontend/` at repo root.

---

## 2. Directory Map

| Path | Purpose |
|---|---|
| `backend/api/main.py` | FastAPI app entry point (v1.1.0) |
| `backend/api/routes/` | 33 route modules, one per feature |
| `backend/api/dependencies.py` | Auth deps: `get_current_user`, `get_current_workspace`, `ActiveWorkspace` |
| `backend/database/models.py` | All SQLAlchemy ORM models |
| `backend/database/connection.py` | `get_db` session dependency |
| `backend/services/` | Business logic layer (one service per domain) |
| `backend/tasks/scraping_tasks.py` | Celery tasks: scraping, cache invalidation |
| `backend/scrapers/scraper_manager.py` | Scraper dispatch: Shopify, generic, Apify fallback |
| `backend/celery_app.py` | Celery app + queue definitions |
| `frontend/pages/` | 43 Next.js pages |
| `frontend/lib/api.js` | **Central API client** — all fetch calls live here |
| `frontend/components/` | Shared UI: Layout, Modal, Toast, etc. |
| `frontend/next.config.js` | Next.js config (AVIF/WebP, removeConsole, etc.) |

**Key route files:**
`products.py`, `auth.py`, `alerts.py`, `analytics.py`, `ai.py`, `scrape.py`,
`competitors.py`, `repricing.py`, `billing.py`, `integrations.py`, `workspaces.py`,
`dashboards.py`, `seller_intel.py`, `forecasting.py`

---

## 3. Active Branch & Git Workflow

- **Feature branch:** `claude/improve-scraping-fireclaw-p23Mt`
- **Push command:** `git push -u origin claude/improve-scraping-fireclaw-p23Mt`
- **Never push to `main` directly**
- Commit prefixes: `feat:` `fix:` `perf:` `chore:` `docs:`
- Always stage specific files, never `git add .`

---

## 4. Start-Up Commands

```bash
# Backend (terminal 1)
cd backend && uvicorn api.main:app --reload            # → http://localhost:8000

# Frontend (terminal 2)
cd frontend && npm run dev                              # → http://localhost:3000

# Celery worker (terminal 3, optional)
cd backend && celery -A celery_app worker --loglevel=info \
  --queues=scraping,analytics,notifications,alerts,integrations,maintenance \
  --concurrency=4

# Celery beat scheduler (terminal 4, optional)
cd backend && celery -A celery_app beat --loglevel=info \
  --scheduler celery.beat.PersistentScheduler

# All-in-one (Unix)
./start-servers.sh
```

Docs: http://localhost:8000/docs  |  Health: http://localhost:8000/health

---

## 5. Established Code Patterns

### Backend

| Pattern | Rule |
|---|---|
| ORM → Pydantic | Always `ProductResponse.model_validate(db_obj)` — never construct field-by-field |
| Safe field update | Gate every `setattr` on `_PRODUCT_WRITABLE_FIELDS` whitelist in `products.py` |
| Workspace isolation | `build_scope_predicate(workspace_id)` on every query |
| Cache keys | `"{feature}:{user_id}:{entity_id}:{param}"` — `user_id` MUST be included |
| Cache invalidation | `"feature:*:{entity_id}:*"` — wildcard **before** entity_id |
| N+1 fix | batch `.in_(ids)` query → `defaultdict` group → pure-Python aggregation |
| Pydantic v2 | `.model_dump(exclude_unset=True)` — never `.dict()` |
| ORM loading | `selectinload` for one-to-many; never `joinedload` (avoids cartesian products) |
| DB aggregation | `func.min`, `func.avg` in SQL — never Python `min()`/`sum()` over large tables |
| Pydantic ORM mode | `model_config = ConfigDict(from_attributes=True)` on all response schemas |

### Frontend

| Pattern | Rule |
|---|---|
| API calls | All via `frontend/lib/api.js` — never raw `fetch()` in pages |
| Numeric form fields | Use `NUMERIC_FIELDS` list + `parseFloat` coercion on submit |
| Boolean form fields | Use `BOOL_FIELDS` list + explicit `Boolean()` coercion |
| XSS in innerHTML | `escapeHtml()` BEFORE any regex substitution; never skip this |
| Pagination | `api.getProducts(limit, offset)` — `PAGE_SIZE = 50`, append on page > 0 |
| Form arrays | tags / bundle_skus: comma-split → array; variant_attributes: JSON.parse with try/catch |

---

## 6. Key Environment Variables

```
# Required in production
JWT_SECRET_KEY        generate: python -c "import secrets; print(secrets.token_hex(32))"
ENCRYPTION_KEY        generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
DATABASE_URL          sqlite:///./marketintel.db  (dev)  |  postgresql://...  (prod)
REDIS_HOST / REDIS_PORT

# Optional integrations
ANTHROPIC_API_KEY     AI features (alerts, repricing recommendations)
STRIPE_SECRET_KEY     Billing
SHOPIFY_APP_CLIENT_ID / SECRET
GOOGLE_CLIENT_ID      OAuth SSO
SENTRY_DSN            Error tracking
```

Frontend: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`)

---

## 7. Known Gotchas — Never Repeat These Bugs

| Bug | Root cause | Fix |
|---|---|---|
| `NameError: blocklist` on every auth request | Missing import in `dependencies.py` | `from services.token_blocklist import blocklist` |
| `NameError: uuid` in auth_service | Missing import | `import uuid` at top of `auth_service.py` |
| `Dashboard.widgets` AttributeError | Missing ORM back-ref | `widgets = relationship("DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan")` in `models.py` |
| XSS via `dangerouslySetInnerHTML` in `scrape-api.js` | Raw JSON wrapped in `<span>` | `escapeHtml()` pre-pass; regex must match `&quot;` delimiters |
| Hardcoded JWT secret in prod | `SECRET_KEY = "..."` fallback | Raise `ValueError` if env var missing when `ENVIRONMENT == "production"` |
| Cross-user cache collisions in analytics | Cache key missing user identifier | Include `user_id` in every analytics cache key |
| Cache invalidation missing stale keys | Old glob `"feature:{id}:*"` missed keys with user_id prefix | Use `"feature:*:{id}:*"` (wildcard before entity_id) |
| Scraper merge conflict | `main` missing ShopifyScraper | Resolve by checking out feature branch: `git checkout <branch> -- backend/scrapers/scraper_manager.py` |

---

## 8. Model Quick Reference

Key SQLAlchemy models in `backend/database/models.py`:

| Model | Key fields |
|---|---|
| `User` | `id`, `email`, `role` (UserRole enum), `subscription_tier`, `workspace_id` |
| `Workspace` | `id`, `name`, `owner_id` |
| `ProductMonitored` | `id`, `user_id`, `workspace_id`, `title`, `sku`, `brand`, `my_price`, `image_url`, `asin`, `upc_ean`, `mpn`, `category`, `status`, `scrape_frequency`, `scrape_priority`, `match_threshold`, `source` |
| `CompetitorMatch` | `id`, `monitored_product_id`, `competitor_url`, `latest_price`, `in_stock`, `last_scraped` |
| `PriceHistory` | `id`, `match_id`, `price`, `timestamp` |
| `CompetitorWebsite` | `id`, `user_id`, `domain`, `scraper_type` |
| `Alert` | `id`, `user_id`, `product_id`, `alert_type`, `threshold`, `triggered_at` |
| `Dashboard` / `DashboardWidget` | `dashboard_id`, `widget_type`, `position`, `config` |

---

## 9. Pending / Completed Work Log

> Format: `[DONE]` / `[PENDING]` / `[IN PROGRESS]`

### Session: QA + optimize + CLAUDE.md (2026-04-13)

**Backend fixes (QA pass)**
- [DONE] `products.py` — `update_product` returns `ProductResponse.model_validate(product)`
- [DONE] `products.py` — setattr guarded by `_PRODUCT_WRITABLE_FIELDS`
- [DONE] `products.py` — `.model_dump(exclude_unset=True)` (was `.dict()`)
- [DONE] `dependencies.py` — `blocklist` import fix (critical NameError)
- [DONE] `auth_service.py` — `import uuid`, prod-safe JWT secret handling
- [DONE] `models.py` — `Dashboard.widgets` relationship added

**Frontend fixes (QA pass)**
- [DONE] `add.js` — full rewrite: 7 accordion sections, all extended fields
- [DONE] `scrape-api.js` — XSS fix in `syntaxHighlight()` via `escapeHtml()` pre-pass

**Speed optimizations (batch 1)**
- [DONE] `ai.py` — N+1 fix in `_build_user_context` (3 batch queries + defaultdict)
- [DONE] `ai.py` — N+1 fix in `generate_narrative` (same batch pattern)
- [DONE] `analytics.py` — `user_id` added to all 3 Redis cache keys
- [DONE] `scraping_tasks.py` — cache invalidation glob wildcards fixed; `.order_by` on pagination
- [DONE] `product_catalog_service.py` — SQL aggregates (`func.min` / `func.avg`)
- [DONE] `seller_intel_service.py` — `selectinload` on CompetitorMatch query
- [DONE] `next.config.js` — AVIF/WebP image formats, `removeConsole` in prod, `optimizePackageImports`
- [DONE] `api.js` — `getProducts(limit, offset)` pagination params

**Speed optimizations (batch 2 — committed separately)**
- [DONE] `products/index.js` — Load More pagination (PAGE_SIZE=50, append, hasMore state)

**"Fall in love" features**
- [DONE] `OnboardingWizard.js` + `_app.js` — full-screen overlay, step animations, animated icons, colored alert cards, marketplace chips, wired via OnboardingGate
- [DONE] `[id].js` + `ai.py` + `api.js` — AI price suggestion card on product detail (POST /ai/recommend/:id, Apply button)
- [DONE] `settings/index.js` + `notifications.py` + `api.js` — branded channel cards with test-send + connection status for Slack/Discord/Push/Email
- [DONE] `repricing/index.js` + `repricing.py` + `api.js` — Rule preview panel: "affects N products, avg $X → $Y, ±Z%"
- [PENDING] Feature #5: Insights → actions linking ("Fix this" creates repricing rule)

**Scraping speed**
- [DONE] `scraping_tasks.py` — S1: honor scrape_frequency (skip recently-scraped); S2: task priority via _PRIORITY_MAP; S3: per-worker persistent BrowserPool singleton
- [DONE] `celery_app.py` — task_queue_max_priority=10, task_default_priority=5

**System speed / DB**
- [DONE] `repricing.py` — MAP violations O(N³) → 2 batch queries + Python join
- [DONE] `products.py` — price-history endpoint: days/limit params (default 90d/500)
- [DONE] `models.py` — idx_ph_match_time_price covering index; idx_pa_job_filter
- [DONE] `smart_alert_service.py` — alert job SQL pre-filter (snoozed/cooldown)

**Stickiness**
- [DONE] `analytics.py` + `dashboard/index.js` — Quick Wins panel: overpriced/alert/no-data insights with CTA links
- [DONE] `notifications.py` + `settings/index.js` — Digest preview: shows stats + top movements inline before sending

**Housekeeping**
- [DONE] `CLAUDE.md` — created (this file)
