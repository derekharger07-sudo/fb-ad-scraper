# ⚡ Quick Start - Run Locally in 2 Steps

**⚡ FAST MODE CONFIGURED:** 100 parallel browsers, 246 keywords, 10x speedup enabled!

## 🎯 Super Easy Setup

### **Step 1: Download the Project**
1. In Replit, click the **3-dot menu (⋮)** at the top
2. Select **"Download as ZIP"**
3. Extract the ZIP on your computer

### **Step 2: Run the Installer**

#### **Windows:**
Double-click: `install_and_run.bat`

#### **Mac/Linux:**
```bash
chmod +x install_and_run.sh
./install_and_run.sh
```

**That's it!** The installer will:
- ✅ Check Python
- ✅ Install all dependencies
- ✅ Install Chromium browser
- ✅ Ask for your SpyFu API key
- ✅ Let you choose keywords (50 or 246)
- ✅ Configure workers/threads for your system
- ✅ Start scraping automatically

---

## 🔑 Get Your SpyFu API Key

1. Go to: https://www.spyfu.com/api
2. Sign up for an account
3. Copy your API key
4. Paste it when the installer asks

---

## ⚙️ Configuration Options

### **Keywords:**
- **Current:** 246 keywords (keywords_246_full.txt)
- **Fast Mode:** URL-only extraction (10x faster than before)
- **Expected time:** 30-60 minutes with 100 browsers

### **Performance - Run Options:**

**Default Configuration (Recommended):**
```bash
python distributed_scraper.py
```
- Uses 10 workers × 10 threads = **100 browsers** ✅
- Optimized for most PCs (40GB RAM, i7 8-core)
- Can handle 50,000-100,000 ads in 30-60 minutes

**Custom Configurations:**
```bash
# Conservative (good for 8GB RAM systems)
python distributed_scraper.py --workers 5 --threads 10

# Balanced (16GB RAM)
python distributed_scraper.py --workers 8 --threads 10

# Aggressive (32GB+ RAM)
python distributed_scraper.py --workers 15 --threads 15

# Ultra Conservative (low-end PC)
python distributed_scraper.py --workers 3 --threads 5
```

**Get Help:**
```bash
python distributed_scraper.py --help
```

---

## 📊 After Scraping

### View your data:
```bash
python -c "from app.db.repo import get_session; from app.db.models import AdCreative; print(f'Total ads: {next(get_session()).query(AdCreative).count()}')"
```

### Start API server:
```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 5000
```

Then visit: http://localhost:5000/ads

---

## 🆘 Troubleshooting

### "Python not found"
- Download Python: https://www.python.org/downloads/
- Make sure to check "Add to PATH" during installation

### "pip not found"
```bash
python -m ensurepip --upgrade
```

### Scraper is slow
- Reduce workers/threads in the configuration menu
- Check your internet speed
- Try sequential mode: 1 worker × 1 thread

### Database errors
- The scraper uses SQLite by default (no setup needed)
- For PostgreSQL: Install locally and set DATABASE_URL in .env

---

## 💡 Pro Tips

1. **Run overnight** - Let it scrape while you sleep
2. **Start small** - Test with 50 keywords first
3. **Monitor logs** - Check `scraper_main.log` for progress
4. **Use good internet** - Faster connection = faster scraping

---

**Total setup time: 5 minutes** ⚡
