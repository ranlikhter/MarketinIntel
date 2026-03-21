# PostgreSQL Enterprise Cutover

This is the exact run order for moving the app from the current SQLite layout to the first enterprise-ready PostgreSQL release.

## Goal

Ship these changes safely:

1. move the live database to PostgreSQL
2. add workspace ownership to the current tables
3. backfill existing rows into workspaces
4. deploy the first workspace-aware backend code
5. enforce workspace constraints
6. add stable public UUIDs

## Preconditions

You should already have these files in the repo before starting:

1. [0008_add_workspace_scope_columns.py](C:/Users/ranli/Scrape/backend/alembic/versions/0008_add_workspace_scope_columns.py)
2. [0009_backfill_workspace_scope.py](C:/Users/ranli/Scrape/backend/alembic/versions/0009_backfill_workspace_scope.py)
3. [0010_enforce_workspace_scope_constraints.py](C:/Users/ranli/Scrape/backend/alembic/versions/0010_enforce_workspace_scope_constraints.py)
4. [0011_add_public_ids.py](C:/Users/ranli/Scrape/backend/alembic/versions/0011_add_public_ids.py)

## Preflight Checklist

Before touching production:

1. take a full backup of the SQLite file
2. take an application-level export of critical business data
3. provision the PostgreSQL database
4. confirm the app can connect to PostgreSQL with the future `DATABASE_URL`
5. schedule a maintenance window if you do not already have dual-write enabled

## Environment Setup

Set `DATABASE_URL` to the PostgreSQL database before running Alembic on the new target.

Example:

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://USER:PASSWORD@HOST:5432/marketintel"
```

## Exact Run Order

### Step 1: Build the empty PostgreSQL schema with the current app models

Run:

```powershell
cd C:\Users\ranli\Scrape\backend
python .\database\setup.py
```

What this does in plain language:
It creates the current public schema on PostgreSQL, including the workspace-aware columns that already exist in the repo models.

### Step 2: Stamp the already-created baseline and apply the enterprise schema wave

Run:

```powershell
cd C:\Users\ranli\Scrape\backend
python -m alembic stamp 0010
python -m alembic upgrade head
```

What this does:

1. tells Alembic the baseline public schema already exists
2. applies `0011`, `0012`, and `0013`
3. creates the new `state`, `analytics`, and `ops` schemas

### Step 3: Copy the current SQLite data into PostgreSQL

Run:

```powershell
cd C:\Users\ranli\Scrape\backend
$env:SQLITE_DATABASE_URL = "sqlite:///./marketintel.db"
python .\scripts\sqlite_to_postgres.py
```

If you are validating with the benchmark copy instead of the live file:

```powershell
$env:SQLITE_DATABASE_URL = "sqlite:///./benchmark_marketintel_copy.db"
python .\scripts\sqlite_to_postgres.py
```

What this does:

1. copies all overlapping tables from SQLite into PostgreSQL
2. normalizes SQLite booleans and JSON values so PostgreSQL accepts them
3. keeps PostgreSQL-only columns like `public_id` on their database defaults

Required validation after the copy:

1. user count matches
2. product count matches
3. competitor match count matches
4. price history count matches
5. alert count matches

Do not continue until those counts match.

### Step 4: Backfill workspace ownership for the copied rows

Run:

```powershell
cd C:\Users\ranli\Scrape\backend
python .\scripts\backfill_workspace_scope.py
```

What this does:

1. creates a personal workspace for users who do not already have one
2. links each user to that workspace
3. fills `workspace_id` on products, alerts, history, logs, keys, and integrations
4. sets `users.default_workspace_id`
5. stops if any core row is still missing workspace ownership

### Step 5: Rebuild the enterprise projection tables

Run:

```powershell
cd C:\Users\ranli\Scrape\backend
python .\scripts\backfill_enterprise_rollups.py
```

What this does:

1. rebuilds `state.product_state_current`
2. rebuilds `state.competitor_listing_state_current`
3. rebuilds `state.seller_state_current`
4. rebuilds `analytics.product_metrics_current`
5. rebuilds `analytics.portfolio_metrics_current`
6. rebuilds `analytics.seller_metrics_current`

### Step 6: Verify the backfill before deploying code

Run checks like these against PostgreSQL:

```sql
select count(*) from users where default_workspace_id is null;
select count(*) from products_monitored where workspace_id is null;
select count(*) from competitor_matches where workspace_id is null;
select count(*) from price_history where workspace_id is null;
select count(*) from price_alerts where workspace_id is null;
select count(*) from state.product_state_current;
select count(*) from analytics.product_metrics_current;
```

Expected result:

1. every `... is null` query above returns `0`
2. the `state` and `analytics` counts are non-zero when the source database has products

### Step 7: Deploy the workspace-aware backend code

Deploy the code that:

1. reads the active workspace from `X-Workspace-ID` or `users.default_workspace_id`
2. scopes product, alert, and insights reads by workspace
3. writes new products and alerts with both `user_id` and `workspace_id`
4. exposes `active_workspace_id` in auth responses

Relevant files:

1. [dependencies.py](C:/Users/ranli/Scrape/backend/api/dependencies.py)
2. [products.py](C:/Users/ranli/Scrape/backend/api/routes/products.py)
3. [alerts.py](C:/Users/ranli/Scrape/backend/api/routes/alerts.py)
4. [insights.py](C:/Users/ranli/Scrape/backend/api/routes/insights.py)
5. [workspaces.py](C:/Users/ranli/Scrape/backend/api/routes/workspaces.py)
6. [auth.py](C:/Users/ranli/Scrape/backend/api/routes/auth.py)

Important:
Do this after `0009`, not before. The new code expects the workspace columns to exist.

### Step 8: Smoke test the app

Test these flows on PostgreSQL:

1. login
2. `/api/auth/me`
3. `/api/workspaces`
4. `/api/products`
5. `/api/products/summary`
6. `/api/alerts`
7. `/api/insights/dashboard`
8. select a workspace with `/api/workspaces/{id}/select`

### Step 9: Switch live traffic

After smoke tests pass:

1. point the live app to PostgreSQL
2. restart backend workers and API instances
3. watch logs and error rates
4. keep the SQLite backup until the rollback window closes

## One-Line Upgrade Command

If PostgreSQL is ready and you want the exact proven local flow:

```powershell
cd C:\Users\ranli\Scrape\backend
python .\database\setup.py
python -m alembic stamp 0010
python -m alembic upgrade head
$env:SQLITE_DATABASE_URL = "sqlite:///./marketintel.db"
python .\scripts\sqlite_to_postgres.py
python .\scripts\backfill_workspace_scope.py
python .\scripts\backfill_enterprise_rollups.py
```

## Rollback Plan

If something fails before `0010`:

1. stop the rollout
2. point the app back to SQLite or the previous Postgres snapshot
3. restore from the last good backup if needed

If something fails after `0010`:

1. do not try to “half-revert” data manually
2. restore the PostgreSQL database from backup
3. redeploy the previous app version

## Things Not To Do

1. do not run the enterprise cutover on SQLite
2. do not skip `backfill_workspace_scope.py` after copying a populated SQLite database
3. do not switch live traffic before `backfill_enterprise_rollups.py` completes
4. do not drop the old user ownership columns in this release

## Success Criteria

The cutover is complete when:

1. the app is running on PostgreSQL
2. all hot business rows have `workspace_id`
3. auth responses include `active_workspace_id`
4. product, alert, and insights routes read the active workspace
5. `0013` is applied on PostgreSQL
6. `state` and `analytics` rows exist for populated workspaces
