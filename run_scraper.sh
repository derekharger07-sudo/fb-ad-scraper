#!/bin/bash
# Run distributed scraper in background with proper logging

echo "🚀 Starting Distributed Facebook Ad Scraper..."
echo "📊 Processing 246 keywords with 5 workers × 10 threads"
echo ""

# Run scraper and redirect all output to a log file
cd product-research-tool-starter 2>/dev/null || true
nohup python3 distributed_scraper.py > scraper_main.log 2>&1 &

SCRAPER_PID=$!
echo "✅ Scraper started with PID: $SCRAPER_PID"
echo "📁 Main log: scraper_main.log"
echo "📁 Worker logs: logs/worker_*.log"
echo ""
echo "Monitor progress with:"
echo "  tail -f scraper_main.log"
echo "  tail -f logs/worker_1.log"
echo ""
echo "Stop scraper with: kill $SCRAPER_PID"
