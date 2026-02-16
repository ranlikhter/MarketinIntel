# 🚀 MarketIntel - Quick Start Guide

## ⚡ Quick Start (Windows)

Simply double-click: **`start-servers.bat`**

This will:
1. Start the Backend API (port 8000)
2. Start the Frontend Web App (port 3000)
3. Automatically open your browser

## 🖥️ Manual Start (All Platforms)

### Start Backend
```bash
cd backend/api
python main.py
```

### Start Frontend (New Terminal)
```bash
cd frontend
npm run dev
```

## 🌐 Access the Platform

Once started, you can access:

- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## 🔐 First Steps

1. **Sign Up:** Go to http://localhost:3000/auth/signup
2. **Create Account:** Enter your email and password
3. **Login:** Go to http://localhost:3000/auth/login
4. **Start Monitoring:** Add products and competitor websites!

## 📊 Features Available

All 7 major features are ready to use:

1. ✅ **Insights Dashboard** - See actionable intelligence
2. ✅ **Smart Alerts** - Get notified of price changes
3. ✅ **Advanced Filtering** - Find products quickly
4. ✅ **Bulk Repricing** - Automate pricing strategies
5. ✅ **Competitor Intel** - Analyze competitor behavior
6. ✅ **Forecasting** - Predict future prices
7. ✅ **Auto Discovery** - Find competitors automatically

## 🛑 Stop the Servers

### Windows
Close the terminal windows or press `Ctrl+C` in each terminal

### Mac/Linux
Press `Ctrl+C` in the terminal running the script

## 🐛 Troubleshooting

### Port Already in Use

**Backend (Port 8000):**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:8000 | xargs kill -9
```

**Frontend (Port 3000):**
```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:3000 | xargs kill -9
```

### Backend Won't Start

1. Make sure you're in the right directory
2. Check Python is installed: `python --version`
3. Install dependencies: `cd backend && pip install -r requirements.txt`

### Frontend Won't Start

1. Make sure you're in the right directory
2. Check Node is installed: `node --version`
3. Install dependencies: `cd frontend && npm install`

### Database Errors

Initialize the database:
```bash
cd backend
python database/setup.py
```

## 📖 Full Documentation

- **System Status:** See `SYSTEM-STATUS.md`
- **Feature Docs:** See `PR-SUMMARY.md`
- **API Endpoints:** http://localhost:8000/docs (when running)

## 🎯 Need Help?

1. Check `SYSTEM-STATUS.md` for detailed troubleshooting
2. Verify all services are running: http://localhost:8000/health
3. Check the terminal output for error messages

---

**Happy Monitoring!** 🎉
