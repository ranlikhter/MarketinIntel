# MarketIntel - E-commerce Competitive Intelligence SaaS

A powerful tool for monitoring competitor pricing across e-commerce platforms like Amazon, Walmart, and more.

## 🚀 Features

- **Product Monitoring**: Track your products across multiple retailers
- **Price Tracking**: Historical price data and trends
- **Competitor Analysis**: See how your prices compare to competitors
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

### Terminal 1 - Backend API

```bash
cd backend
uvicorn api.main:app --reload
```

The API will be available at: http://localhost:8000

API Documentation: http://localhost:8000/docs

### Terminal 2 - Frontend Dashboard

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

1. **Start both servers** (backend and frontend)
2. **Open your browser** to http://localhost:3000
3. **Add a product** using the "Add Product" form
4. **Enter a product name** (e.g., "Sony WH-1000XM5 Headphones")
5. **Click "Start Monitoring"**
6. **View results** - The system will scrape Amazon and show competitor prices

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

- `POST /products` - Add a new product to monitor
- `GET /products` - List all monitored products
- `GET /products/{id}` - Get product details
- `GET /products/{id}/matches` - Get competitor matches
- `GET /products/{id}/price-history` - Get price history
- `POST /scrape/{id}` - Manually trigger a scrape

Full API documentation: http://localhost:8000/docs

## 🚢 Deployment (Coming Soon)

- Backend: Railway.app or Render
- Frontend: Vercel
- Database: PostgreSQL (production)

## 📝 Development Roadmap

- [x] Basic project setup
- [x] Database models
- [ ] Amazon scraper
- [ ] Product matching algorithm
- [ ] REST API endpoints
- [ ] Dashboard UI
- [ ] Price history charts
- [ ] Automated scraping
- [ ] Multi-retailer support
- [ ] User authentication
- [ ] Email alerts

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
