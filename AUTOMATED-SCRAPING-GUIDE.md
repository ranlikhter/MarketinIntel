# 🤖 Automated Scraping with Celery + Redis Guide

## 🎉 What's New?

Your MarketIntel SaaS now has **FULLY AUTOMATED BACKGROUND SCRAPING**!

### Features Added:
- ✅ **Celery Task Queue** - Background job processing
- ✅ **Redis Backend** - Fast message broker and result storage
- ✅ **Automatic Scheduling** - Scrape products every 6 hours automatically
- ✅ **Priority Scraping** - Smart queue management
- ✅ **Analytics Updates** - Daily trend calculations
- ✅ **Price Alerts** - Automatic price change notifications
- ✅ **Task Monitoring UI** - Real-time task status dashboard
- ✅ **Manual Triggers** - On-demand task execution

---

## 📦 Installation Steps

### 1. Install Redis (Windows)

**Option A: Using Memurai (Redis for Windows)**
```bash
# Download from: https://www.memurai.com/get-memurai
# Install and start service
```

**Option B: Using Docker (Recommended)**
```bash
# Install Docker Desktop: https://www.docker.com/products/docker-desktop

# Run Redis container
docker run -d -p 6379:6379 --name redis redis:latest

# Verify Redis is running
docker ps
```

**Option C: Using WSL (Windows Subsystem for Linux)**
```bash
# Install WSL2 first
wsl --install

# Inside WSL, install Redis
sudo apt update
sudo apt install redis-server

# Start Redis
sudo service redis-server start

# Test connection
redis-cli ping  # Should return "PONG"
```

### 2. Install Python Dependencies

```bash
cd C:\Users\ranli\Scrape\backend

# Install Celery and Redis packages
pip install -r requirements.txt

# Verify installation
python -c "import celery; print(celery.__version__)"
python -c "import redis; print(redis.__version__)"
```

---

## 🚀 Running the System

### Terminal 1: Start FastAPI Backend
```bash
cd C:\Users\ranli\Scrape\backend
python api/main.py
```
**Runs on:** http://localhost:8000

### Terminal 2: Start Celery Worker
```bash
cd C:\Users\ranli\Scrape\backend

# Windows
celery -A celery_app worker --loglevel=info --pool=solo

# Linux/Mac
celery -A celery_app worker --loglevel=info
```
**Purpose:** Executes background tasks (scraping, analytics, alerts)

### Terminal 3: Start Celery Beat (Scheduler)
```bash
cd C:\Users\ranli\Scrape\backend

celery -A celery_app beat --loglevel=info
```
**Purpose:** Triggers scheduled tasks automatically

### Terminal 4: Start Flower (Optional - Monitoring UI)
```bash
cd C:\Users\ranli\Scrape\backend

celery -A celery_app flower
```
**Runs on:** http://localhost:5555
**Purpose:** Beautiful web UI to monitor tasks

### Terminal 5: Frontend (Next.js)
```bash
cd C:\Users\ranli\Scrape\frontend
npm run dev
```
**Runs on:** http://localhost:3000

---

## ⚙️ Automatic Schedules

Once Celery Beat is running, these tasks run automatically:

| Task | Schedule | Description |
|------|----------|-------------|
| **Scrape All Products** | Every 6 hours | Scrapes all monitored products |
| **Update Analytics** | Daily at 2:00 AM | Calculates trends and insights |
| **Daily Digest Email** | Daily at 8:00 AM | Sends summary email |
| **Data Cleanup** | Sunday 3:00 AM | Removes old price history (90+ days) |

### Customize Schedules

Edit `backend/celery_app.py`:

```python
beat_schedule={
    'scrape-all-products-6h': {
        'task': 'tasks.scraping_tasks.scrape_all_products',
        'schedule': crontab(minute=0, hour='*/6'),  # Change to */12 for 12 hours
        'options': {'queue': 'scraping'}
    },
}
```

**Crontab Examples:**
- Every hour: `crontab(minute=0)`
- Every 30 minutes: `crontab(minute='*/30')`
- Every day at 3 AM: `crontab(minute=0, hour=3)`
- Every Monday at 9 AM: `crontab(minute=0, hour=9, day_of_week=1)`

---

## 🎯 Using the Scheduler UI

Navigate to: **http://localhost:3000/scheduler**

### Features:

#### 1. **Queue Stats** (Top Cards)
- Active Tasks: Currently running tasks
- Scheduled Tasks: Queued tasks waiting to run
- Active Workers: Number of Celery workers
- Task History: Recent task log

#### 2. **Manual Task Triggers**
Click any button to run tasks immediately:

- **🔍 Scrape All Products** - Scrape every monitored product now
- **⚡ Priority Scrape** - Scrape products not updated in 24h
- **📊 Update Analytics** - Recalculate all trends and insights
- **🔔 Check Price Alerts** - Find significant price changes (>5%)
- **📧 Send Daily Digest** - Generate and send daily report
- **🗑️ Data Cleanup** - Remove old price history (90+ days)

#### 3. **Currently Running Tasks**
Shows real-time status of active tasks:
- Task name and ID
- Which worker is processing it
- Live progress indicator

#### 4. **Recent Task History**
Log of tasks triggered in the current session:
- Task message and status
- Timestamp and task ID
- Color-coded status badges

---

## 📊 Monitoring with Flower

Flower provides advanced monitoring:

```bash
# Start Flower
celery -A celery_app flower
```

Visit: **http://localhost:5555**

### Features:
- 📈 Task execution timeline
- 📊 Success/failure rate charts
- ⏱️ Task duration statistics
- 👷 Worker health monitoring
- 🔄 Real-time task updates
- 📝 Task history and results

---

## 🔧 Task Queue Architecture

### Queue Types:
- **scraping** - Product scraping tasks (highest priority)
- **analytics** - Trend calculations
- **notifications** - Email alerts
- **maintenance** - Data cleanup

### Task Flow:
```
1. Task Triggered (Manual or Scheduled)
   ↓
2. Added to Redis Queue
   ↓
3. Celery Worker Picks Up Task
   ↓
4. Task Executes (Scraping, Analytics, etc.)
   ↓
5. Result Stored in Redis
   ↓
6. UI Updates with Result
```

---

## 🎯 Example: Automated Daily Workflow

**8:00 AM** - Celery Beat triggers daily scrape
```
→ scrape_all_products() queues 50 individual scraping tasks
→ Each product scraped in parallel by workers
→ New prices recorded in PriceHistory table
```

**9:00 AM** - Analytics update runs
```
→ update_all_analytics() calculates:
  - Average competitor prices
  - Price trends (increasing/decreasing/stable)
  - Volatility and stability scores
```

**10:00 AM** - Price alert check
```
→ check_price_alerts() finds:
  - Products with >5% price changes
  - Sends email alerts (TODO: implement SMTP)
```

**11:00 AM** - Daily digest sent
```
→ send_daily_digest() generates:
  - Total products scraped
  - Biggest price drops
  - Summary email sent to users
```

---

## 🔔 Price Alerts (Coming Soon)

### How Alerts Work:

1. **Alert Check Runs** (automatically or manually)
2. **Compares Recent Prices** (last 24 hours)
3. **Calculates Change %**
4. **If change > threshold** → Send notification

### Alert Types:
- 📉 **Price Drop** - Competitor lowered price
- 📈 **Price Increase** - Competitor raised price
- ⚠️ **Out of Stock** - Product unavailable
- 🎯 **Back in Stock** - Product available again

### Configuring Alerts:

```python
# In scheduler UI or via API
POST /api/scheduler/alerts/check?threshold_pct=10.0

# Alert if price changes by 10% or more
```

---

## 📧 Email Integration (TODO)

To send email alerts, add to `.env`:

```env
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Or use SendGrid
SENDGRID_API_KEY=your-sendgrid-key
```

Then update `tasks/notification_tasks.py` to send actual emails.

---

## 🐛 Troubleshooting

### Redis Connection Error
```
celery.exceptions.OperationalError: Error connecting to Redis
```

**Solution:**
```bash
# Check if Redis is running
redis-cli ping

# If using Docker
docker ps | grep redis

# If not running, start Redis
docker start redis
```

### Celery Worker Not Starting
```
ImportError: No module named 'celery_app'
```

**Solution:**
```bash
# Make sure you're in the backend directory
cd C:\Users\ranli\Scrape\backend

# Verify celery_app.py exists
ls celery_app.py

# Try running with full path
celery -A celery_app worker --loglevel=info --pool=solo
```

### Tasks Not Running Automatically
```
No tasks running despite schedule configured
```

**Solution:**
```bash
# Make sure Celery Beat is running
celery -A celery_app beat --loglevel=info

# Check beat schedule
celery -A celery_app inspect scheduled
```

### Database Lock Error
```
sqlite3.OperationalError: database is locked
```

**Solution:**
- SQLite doesn't handle concurrent writes well
- For production, migrate to PostgreSQL:

```bash
# Install PostgreSQL
# Update .env
DATABASE_URL=postgresql://user:pass@localhost/marketintel

# Update database/connection.py to use PostgreSQL
```

---

## 🚀 Production Deployment

### Option 1: Railway.app (Recommended for Beginners)

**1. Add Procfile:**
```bash
# backend/Procfile
web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
worker: celery -A celery_app worker --loglevel=info
beat: celery -A celery_app beat --loglevel=info
```

**2. Deploy:**
```bash
# Push to GitHub
git add .
git commit -m "Add automated scraping"
git push

# In Railway dashboard:
- Connect GitHub repo
- Add Redis service
- Add 3 processes: web, worker, beat
- Set environment variables
```

### Option 2: Heroku

```bash
# Install Heroku CLI
# Login
heroku login

# Create app
heroku create marketintel-app

# Add Redis addon
heroku addons:create heroku-redis:mini

# Add worker + beat to Procfile
# Deploy
git push heroku main

# Scale workers
heroku ps:scale web=1 worker=1 beat=1
```

### Option 3: VPS (DigitalOcean, AWS, etc.)

```bash
# Install Redis
sudo apt install redis-server

# Install Python dependencies
pip install -r requirements.txt

# Use systemd for Celery
sudo nano /etc/systemd/system/celery.service
sudo systemd start celery
```

---

## 📈 Performance Tips

### 1. Increase Worker Concurrency
```bash
# Run more workers
celery -A celery_app worker --concurrency=4
```

### 2. Use Multiple Queues
```python
# Separate high-priority scraping
scrape_single_product.apply_async(args=[product_id], queue='high-priority')
```

### 3. Rate Limiting
```python
# Limit scraping to 10 products per minute
@celery_app.task(rate_limit='10/m')
def scrape_single_product(product_id):
    ...
```

### 4. Retry Failed Tasks
```python
@celery_app.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def scrape_single_product(product_id):
    ...
```

---

## 🎯 Next Steps

✅ **Implemented:**
- Celery + Redis setup
- Background task queue
- Automatic scheduling
- Task monitoring UI

🔜 **Coming Next:**
1. Email/SMS notifications (SendGrid integration)
2. User-specific alert preferences
3. Webhook integrations
4. Advanced analytics (ML-based trend predictions)
5. Multi-user support with task isolation

---

## 📚 Additional Resources

- **Celery Docs:** https://docs.celeryq.dev/
- **Redis Docs:** https://redis.io/docs/
- **Flower Docs:** https://flower.readthedocs.io/
- **Crontab Syntax:** https://crontab.guru/

---

**Your MarketIntel SaaS is now a FULLY AUTOMATED competitive intelligence platform!** 🚀

Run all 5 terminals and watch the magic happen:
1. FastAPI: http://localhost:8000
2. Celery Worker (processes tasks)
3. Celery Beat (schedules tasks)
4. Flower: http://localhost:5555 (optional)
5. Next.js: http://localhost:3000

Navigate to **http://localhost:3000/scheduler** to control everything! 🎉
