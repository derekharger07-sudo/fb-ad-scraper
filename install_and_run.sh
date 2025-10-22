#!/bin/bash

echo "=========================================="
echo "🚀 FACEBOOK AD SCRAPER - AUTO INSTALLER"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found!"
    echo "📥 Please install Python from: https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Install Python packages
echo "📦 Installing Python packages..."
pip3 install -r requirements.txt --quiet
if [ $? -eq 0 ]; then
    echo "✅ Python packages installed"
else
    echo "❌ Failed to install packages"
    exit 1
fi
echo ""

# Install Playwright
echo "🌐 Installing Chromium browser..."
python3 -m playwright install chromium --with-deps 2>&1 | grep -v "Downloading" || true
if [ $? -eq 0 ]; then
    echo "✅ Chromium installed"
else
    echo "❌ Failed to install Chromium"
    exit 1
fi
echo ""

# Setup API Key
echo "🔑 API KEY SETUP"
echo "----------------------------------------"
if [ -f .env ]; then
    echo "⚠️  .env file already exists"
    read -p "Do you want to update it? (y/n): " update_env
    if [ "$update_env" != "y" ]; then
        echo "Skipping API key setup..."
    else
        rm .env
    fi
fi

if [ ! -f .env ] || [ "$update_env" = "y" ]; then
    echo ""
    echo "You need a SpyFu API key to collect traffic data."
    echo "Get one here: https://www.spyfu.com/api"
    echo ""
    read -p "Enter your SpyFu API Key: " spyfu_key
    
    echo "SPYFU_API_KEY=$spyfu_key" > .env
    echo "✅ API key saved to .env file"
fi
echo ""

# Choose keyword file
echo "📋 KEYWORD SELECTION"
echo "----------------------------------------"
echo "Choose your keyword file:"
echo "1) keywords.txt (50 test keywords - ~30 min)"
echo "2) keywords_246_full.txt (246 keywords - ~2-4 hours)"
echo ""
read -p "Enter choice (1 or 2): " keyword_choice

if [ "$keyword_choice" = "2" ]; then
    keyword_file="keywords_246_full.txt"
    echo "✅ Selected: 246 keywords (comprehensive scan)"
else
    keyword_file="keywords.txt"
    echo "✅ Selected: 50 keywords (quick test)"
fi
echo ""

# Configure workers/threads
echo "⚙️  PERFORMANCE CONFIGURATION"
echo "----------------------------------------"
echo "Recommended settings based on your system:"
echo "1) Laptop/8GB RAM: 2 workers × 5 threads = 10 browsers"
echo "2) Desktop/16GB RAM: 3 workers × 10 threads = 30 browsers"
echo "3) Server/32GB+: 5 workers × 20 threads = 100 browsers"
echo "4) Custom configuration"
echo ""
read -p "Enter choice (1-4): " perf_choice

case $perf_choice in
    1)
        workers=2
        threads=5
        echo "✅ Laptop config: 2 workers × 5 threads"
        ;;
    2)
        workers=3
        threads=10
        echo "✅ Desktop config: 3 workers × 10 threads"
        ;;
    3)
        workers=5
        threads=20
        echo "✅ Server config: 5 workers × 20 threads"
        ;;
    4)
        read -p "Number of workers: " workers
        read -p "Threads per worker: " threads
        echo "✅ Custom config: $workers workers × $threads threads"
        ;;
    *)
        workers=2
        threads=5
        echo "✅ Default: 2 workers × 5 threads"
        ;;
esac
echo ""

# Update distributed_scraper.py
sed -i.bak "s/NUM_WORKERS = .*/NUM_WORKERS = $workers/" distributed_scraper.py
sed -i.bak "s/THREADS_PER_WORKER = .*/THREADS_PER_WORKER = $threads/" distributed_scraper.py

# Initialize database (CRITICAL STEP!)
echo "🔧 Initializing database..."
python3 init_database.py
if [ $? -ne 0 ]; then
    echo "❌ Database initialization failed"
    exit 1
fi
echo ""
sed -i.bak "s/KEYWORDS_FILE = .*/KEYWORDS_FILE = \"$keyword_file\"/" distributed_scraper.py
rm distributed_scraper.py.bak 2>/dev/null || true

# Start scraping
echo "=========================================="
echo "🎯 STARTING SCRAPER"
echo "=========================================="
echo "Configuration:"
echo "  Workers: $workers"
echo "  Threads per worker: $threads"
echo "  Total browsers: $((workers * threads))"
echo "  Keywords: $keyword_file"
echo ""
echo "Press Ctrl+C to stop at any time"
echo "Logs: scraper_main.log and logs/worker_*.log"
echo ""
sleep 2

python3 distributed_scraper.py

echo ""
echo "=========================================="
echo "✅ SCRAPING COMPLETE!"
echo "=========================================="
echo ""
echo "📊 View your data:"
echo "  python3 -c 'from app.db.repo import get_session; from app.db.models import AdCreative; print(f\"Total ads: {next(get_session()).query(AdCreative).count()}\")'"
echo ""
echo "🚀 Start API server:"
echo "  uvicorn app.api.main:app --host 0.0.0.0 --port 5000"
echo ""
