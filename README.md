# MarketIntel - E-commerce Competitive Intelligence SaaS

A powerful tool for monitoring competitor pricing across e-commerce platforms like Amazon, Walmart, and more.

## 🚀 Features

- **Product Monitoring**: Track your products across multiple retailers
- **Price Tracking**: Historical price data and trends
- **Competitor Analysis**: See how your prices compare to competitors
- **Custom Competitor Websites**: Add ANY website (not just Amazon/eBay) with custom CSS selectors
- **Amazon Scraper**: Specialized scraper with anti-bot detection for Amazon
- **Smart Matching**: AI-powered product matching across different retailers
- **Real-time Dashboard**: Beautiful visualizations of pricing data

## 📋 Prerequisites

Make sure you have these installed:

- Python 3.11+ ([Download](https://www.python.org/downloads/))
- Node.js 20+ ([Download](https://nodejs.org/))
- Git ([Download](https://git-scm.com/))

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd Scrape
```

### 2. Set up the Backend (Python)

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Install Playwright browsers (needed for web scraping)
playwright install chromium

# Create the database
python backend/database/setup.py
```

### 3. Set up the Frontend (Next.js)

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Go back to root directory
cd ..
```

## 🏃 Running the Application

You need to run both the backend and frontend servers.

### Option 1: Using Startup Scripts (Windows - Easiest!)

**Terminal 1 - Start Backend:**
```bash
start-backend.bat
```

**Terminal 2 - Start Frontend:**
```bash
start-frontend.bat
```

### Option 2: Manual Commands

**Terminal 1 - Backend API:**
```bash
cd backend
uvicorn api.main:app --reload
```

The API will be available at: http://localhost:8000

API Documentation: http://localhost:8000/docs

**Terminal 2 - Frontend Dashboard:**
```bash
cd frontend
npm run dev
```

The dashboard will be available at: http://localhost:3000

## 📁 Project Structure

```
Scrape/
├── backend/               # Python backend
│   ├── api/              # FastAPI REST API
│   ├── database/         # Database models & setup
│   ├── scrapers/         # Web scraping logic
│   ├── matchers/         # Product matching algorithms
│   └── requirements.txt  # Python dependencies
├── frontend/             # Next.js frontend
│   ├── pages/           # React pages
│   ├── components/      # Reusable UI components
│   ├── lib/             # Utility functions
│   └── package.json     # Node.js dependencies
├── data/                # SQLite database files
└── README.md           # This file
```

## 🎯 How to Use

### Adding Your First Product

1. **Start both servers** (run `start-backend.bat` and `start-frontend.bat`)
2. **Open your browser** to http://localhost:3000
3. **Click "Add Product"** in the top navigation
4. **Fill in product details**:
   - Title: "Sony WH-1000XM5 Headphones"
   - Brand: "Sony"
   - SKU: "WH1000XM5-BLK" (optional)
5. **Click "Create Product"**
6. **On the product detail page**, click "Scrape Amazon"
7. **View competitor matches** and price history

### Adding Custom Competitor Websites

1. **Navigate to "Competitors"** in the top navigation
2. **Click "Add Competitor"**
3. **Enter competitor details**:
   - Name: "CompetitorStore"
   - Base URL: "https://www.competitor.com"
   - CSS Selectors for price, title, stock, image
4. **Click "Create Competitor"**
5. **Go to a product detail page**
6. **Use "Scrape URL"** to scrape a specific competitor product page

### Finding CSS Selectors

To extract data from custom competitor websites:

1. Open the competitor's product page in Chrome
2. Right-click the price → "Inspect"
3. In DevTools, right-click the highlighted HTML
4. Select "Copy" → "Copy selector"
5. Paste into the competitor form

## 🔧 Configuration

Edit `backend/.env` to customize settings:

```env
# Database
DATABASE_URL=sqlite:///./data/products.db

# API Settings
API_PORT=8000

# Scraping Settings
SCRAPE_DELAY_MIN=2
SCRAPE_DELAY_MAX=5
```

## 🐛 Troubleshooting

### "Module not found" errors
```bash
# Make sure you're in the right directory and dependencies are installed
pip install -r backend/requirements.txt
cd frontend && npm install
```

### Database errors
```bash
# Recreate the database
rm data/products.db
python backend/database/setup.py
```

### Port already in use
```bash
# Backend (port 8000)
# Change API_PORT in backend/.env

# Frontend (port 3000)
# Next.js will automatically suggest port 3001
```

### Playwright browser not found
```bash
playwright install chromium
```

## 📚 API Endpoints

### Products
- `POST /products` - Add a new product to monitor
- `GET /products` - List all monitored products
- `GET /products/{id}` - Get product details
- `GET /products/{id}/matches` - Get competitor matches
- `GET /products/{id}/price-history` - Get price history
- `POST /products/{id}/scrape` - Search for product on website (e.g., Amazon)
- `POST /products/{id}/scrape-url` - Scrape specific competitor URL
- `DELETE /products/{id}` - Delete a product

### Competitors
- `GET /competitors` - List all competitor websites
- `POST /competitors` - Add a new competitor website
- `GET /competitors/{id}` - Get competitor details
- `PUT /competitors/{id}` - Update competitor
- `POST /competitors/{id}/toggle` - Activate/deactivate competitor
- `DELETE /competitors/{id}` - Delete competitor

Full API documentation: http://localhost:8000/docs

## 🚢 Deployment (Coming Soon)

- Backend: Railway.app or Render
- Frontend: Vercel
- Database: PostgreSQL (production)

## 📝 Development Roadmap

### MVP (Completed ✅)
- [x] Basic project setup
- [x] Database models (4 tables)
- [x] Amazon scraper with anti-bot detection
- [x] Generic web scraper (works with ANY website)
- [x] Custom competitor websites feature
- [x] REST API endpoints (15+ endpoints)
- [x] Dashboard UI (Next.js + Tailwind CSS)
- [x] Price history charts
- [x] Products management
- [x] Competitors management

### Next Steps
- [ ] Product matching algorithm (AI-based)
- [ ] Automated scraping (Celery + Redis)
- [ ] Email alerts for price drops
- [ ] Walmart scraper
- [ ] eBay scraper
- [ ] User authentication
- [ ] Multi-tenancy (SaaS mode)
- [ ] Deploy to production (Railway + Vercel)

## 🤝 Contributing

This is a learning project! Feel free to:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - Feel free to use this project for learning and commercial purposes.

## 🙏 Acknowledgments

- Inspired by Intelligence Node
- Built with FastAPI, Next.js, and Playwright
- Following best practices from the MarketIntel architecture docs

---

**Questions?** Open an issue or reach out!

**Happy coding!** 🎉
