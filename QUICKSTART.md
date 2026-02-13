# MarketIntel - Quick Start Guide

## 🎉 Congratulations! Your Project is Set Up!

Everything is installed and ready to go. Here's what you have so far:

### ✅ What's Working

1. **Backend API** (Python FastAPI)
   - REST API for managing products
   - SQLite database with 3 tables
   - API documentation at `/docs`

2. **Frontend** (Next.js + React)
   - Configured with Tailwind CSS
   - Ready to build dashboard pages

3. **Database**
   - SQLite database created at `data/products.db`
   - Tables: products_monitored, competitor_matches, price_history

### 🚀 How to Run Your App

#### Option 1: Using the Startup Scripts (EASIEST)

**Terminal 1 - Start Backend:**
```
Double-click: start-backend.bat
```
The API will start at http://localhost:8000

**Terminal 2 - Start Frontend:**
```
Double-click: start-frontend.bat
```
The dashboard will start at http://localhost:3000

#### Option 2: Manual Commands

**Terminal 1 - Backend:**
```bash
cd backend
python -m uvicorn api.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 📖 Testing the API

Once the backend is running, visit:
- **API Root**: http://localhost:8000/
- **API Docs**: http://localhost:8000/docs (Interactive Swagger UI!)
- **Health Check**: http://localhost:8000/health

Try creating a product in the Swagger UI:
1. Go to http://localhost:8000/docs
2. Click on **POST /products**
3. Click "Try it out"
4. Enter this JSON:
```json
{
  "title": "Sony WH-1000XM5 Headphones",
  "brand": "Sony"
}
```
5. Click "Execute"
6. You should see a success response!

### 📂 Project Structure

```
C:\Users\ranli\Scrape/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app entry point
│   │   └── routes/
│   │       └── products.py      # Product API endpoints
│   ├── database/
│   │   ├── models.py            # Database tables
│   │   ├── connection.py        # Database connection
│   │   └── setup.py             # Database initialization
│   ├── requirements.txt         # Python dependencies
│   └── .env                     # Configuration
├── frontend/
│   ├── pages/                   # Next.js pages (TODO)
│   ├── components/              # React components (TODO)
│   ├── package.json             # Node dependencies
│   └── tailwind.config.js       # Styling config
├── data/
│   └── products.db              # SQLite database file
├── start-backend.bat            # Easy backend start
├── start-frontend.bat           # Easy frontend start
└── README.md                    # Full documentation
```

### 🛠️ What's Next?

We still need to build:
1. **Amazon Scraper** - Actually scrape Amazon for prices
2. **Product Matcher** - Match products across retailers
3. **Frontend Pages**:
   - Home page with "Add Product" form
   - Products list page
   - Product detail page with price charts
4. **Integration** - Connect frontend to backend

### 🆘 Common Issues

**"Module not found" error:**
```bash
# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install
```

**"Port already in use":**
- Backend uses port 8000
- Frontend uses port 3000
- Close other programs using these ports or change the port in the config

**Database errors:**
```bash
# Recreate the database
rm data/products.db
python backend/database/setup.py
```

### 📝 Git Commands

Your work is already saved in Git! To see your progress:
```bash
git log        # See commit history
git status     # See what's changed
git add .      # Stage all changes
git commit -m "Your message"  # Commit changes
```

---

**Ready to continue?** Just ask and I'll help you build the next component! 🚀
