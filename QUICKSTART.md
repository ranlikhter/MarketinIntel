# MarketIntel - Quick Start Guide

Get up and running in 5 minutes!

## 🎉 Your MarketIntel SaaS is Ready!

Everything is built and ready to test. Here's what you have:

### ✅ What's Working

1. **Backend API** (Python FastAPI)
   - 15+ REST API endpoints
   - SQLite database with 4 tables
   - Amazon scraper with anti-bot detection
   - Generic web scraper (works with ANY website)
   - Custom competitor websites feature

2. **Frontend Dashboard** (Next.js + React + Tailwind CSS)
   - Home page with stats
   - Products list and management
   - Product detail page with competitor matches
   - Price history charts
   - Competitor management interface

3. **Database**
   - Tables: products_monitored, competitor_matches, price_history, competitor_websites
   - Located at `data/products.db`

## 🚀 How to Run

### Step 1: Install Dependencies (First Time Only)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
playwright install chromium
python database/setup.py
cd ..
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### Step 2: Start Both Servers

Open **TWO** terminal windows:

**Terminal 1 - Backend:**
```bash
start-backend.bat
```
Backend will start at: http://localhost:8000

**Terminal 2 - Frontend:**
```bash
start-frontend.bat
```
Frontend will start at: http://localhost:3000

## 📖 Testing Your App

### 1. Open the Dashboard
Navigate to: http://localhost:3000

You should see:
- Hero section: "Monitor Competitor Prices Across E-commerce Platforms"
- Stats: 0 products, 0 matches, 0 competitors
- Navigation: Dashboard | Products | Competitors

### 2. Add Your First Product
- Click **"Add Product"** (top right)
- Fill in:
  - Title: "Sony WH-1000XM5 Headphones"
  - Brand: "Sony"
  - SKU: "WH1000XM5" (optional)
- Click **"Create Product"**

### 3. Scrape Amazon
- You'll be on the product detail page
- Click **"Scrape Amazon"** button
- Wait 5-10 seconds
- **Competitor matches will appear!**
  - You should see 3-5 Amazon products
  - Prices, images, stock status
  - Links to view on Amazon

### 4. Add a Custom Competitor
- Click **"Competitors"** in navigation
- Click **"Add Competitor"**
- Fill in:
  - Name: "Test Competitor"
  - Base URL: "https://www.amazon.com"
  - Price Selector: `.a-price-whole`
  - Title Selector: `#productTitle`
- Click **"Create Competitor"**

### 5. Test the API
Visit: http://localhost:8000/docs

Interactive Swagger UI with all 15+ endpoints!

Try:
- POST /products - Create product
- GET /products - List products
- POST /products/{id}/scrape - Scrape Amazon
- GET /competitors - List competitors

## 📂 Project Structure

```
C:\Users\ranli\Scrape/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app
│   │   └── routes/
│   │       ├── products.py      # Product endpoints
│   │       └── competitors.py   # Competitor endpoints
│   ├── database/
│   │   ├── models.py            # 4 database tables
│   │   ├── connection.py        # Database setup
│   │   └── setup.py             # Database creation
│   ├── scrapers/
│   │   ├── amazon_scraper.py    # Amazon-specific scraper
│   │   ├── generic_scraper.py   # Universal scraper
│   │   └── scraper_manager.py   # Intelligent selection
│   └── requirements.txt
├── frontend/
│   ├── pages/
│   │   ├── index.js             # Home page
│   │   ├── products/
│   │   │   ├── index.js         # Products list
│   │   │   ├── add.js           # Add product form
│   │   │   └── [id].js          # Product detail
│   │   └── competitors/
│   │       ├── index.js         # Competitors list
│   │       └── add.js           # Add competitor form
│   ├── components/
│   │   ├── Layout.js            # Page layout
│   │   └── PriceChart.js        # Price chart
│   ├── lib/
│   │   └── api.js               # API client
│   └── package.json
├── data/
│   └── products.db              # SQLite database
└── README.md                    # Full documentation
```

## 🆘 Troubleshooting

### Backend Won't Start
**Error: "python: command not found"**
- Fix: Make sure Python is installed
- Verify: `python --version`

**Error: "No module named 'fastapi'"**
- Fix: Install dependencies
- Run: `pip install -r backend/requirements.txt`

**Error: "Playwright browser not found"**
- Fix: `playwright install chromium`

### Frontend Won't Start
**Error: "npm: command not found"**
- Fix: Make sure Node.js is installed
- Verify: `node --version` and `npm --version`

**Error: "Cannot find module 'next'"**
- Fix: Install dependencies
- Run: `cd frontend && npm install`

### Scraping Fails
**Error: "CAPTCHA detected"**
- Fix: Amazon detected automation
- Wait a few minutes and try again

**Error: "Failed after 3 attempts"**
- Check internet connection
- Try a different product

### Port Already in Use
**Backend (port 8000):**
- Kill process: `netstat -ano | findstr :8000`
- Or change port in `backend/.env`

**Frontend (port 3000):**
- Next.js will suggest port 3001 automatically

## 🎯 What You Can Do Now

✅ **Monitor Products**:
- Add products you want to track
- Search Amazon for competitor matches
- View price history over time

✅ **Custom Competitors**:
- Add ANY competitor website
- Configure CSS selectors
- Scrape specific product URLs

✅ **API Access**:
- Full REST API at http://localhost:8000/docs
- Use for automation or integrations

## 🛠️ Next Steps

Once you've tested locally:

1. **Add More Features**:
   - Product matching algorithm (AI-based)
   - Automated scraping (Celery + Redis)
   - Email alerts for price drops
   - Walmart/eBay scrapers

2. **Deploy to Production**:
   - Backend: Railway.app or Render
   - Frontend: Vercel
   - Database: Migrate to PostgreSQL

3. **Add Business Features**:
   - User authentication
   - Multi-tenancy (SaaS mode)
   - Pricing tiers
   - Admin dashboard

## 📚 Resources

- **Full README**: `README.md`
- **API Docs**: http://localhost:8000/docs
- **Test Results**: `TEST_RESULTS.md`

---

**Everything is working!** Start by adding a product and scraping Amazon. 🚀
