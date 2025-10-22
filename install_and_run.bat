@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo 🚀 FACEBOOK AD SCRAPER - AUTO INSTALLER
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found!
    echo 📥 Please install Python from: https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo.

REM Install Python packages
echo 📦 Installing Python packages...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ❌ Failed to install packages
    pause
    exit /b 1
)
echo ✅ Python packages installed
echo.

REM Install Playwright
echo 🌐 Installing Chromium browser...
python -m playwright install chromium
if %errorlevel% neq 0 (
    echo ❌ Failed to install Chromium
    pause
    exit /b 1
)
echo ✅ Chromium installed
echo.

REM Setup API Key
echo 🔑 API KEY SETUP
echo ----------------------------------------
if exist .env (
    echo ⚠️  .env file already exists
    set /p update_env="Do you want to update it? (y/n): "
    if /i "!update_env!" neq "y" (
        echo Skipping API key setup...
        goto :keyword_select
    )
    del .env
)

echo.
echo You need a SpyFu API key to collect traffic data.
echo Get one here: https://www.spyfu.com/api
echo.
set /p spyfu_key="Enter your SpyFu API Key: "
echo SPYFU_API_KEY=!spyfu_key!> .env
echo ✅ API key saved to .env file
echo.

:keyword_select
REM Choose keyword file
echo 📋 KEYWORD SELECTION
echo ----------------------------------------
echo Choose your keyword file:
echo 1) keywords.txt (50 test keywords - ~30 min)
echo 2) keywords_246_full.txt (246 keywords - ~2-4 hours)
echo 3) keywords_leggings_only.txt (1 keyword - quick test for advertiser scraping)
echo.
set /p keyword_choice="Enter choice (1, 2, or 3): "

if "!keyword_choice!"=="2" (
    set keyword_file=keywords_246_full.txt
    echo ✅ Selected: 246 keywords (comprehensive scan)
) else if "!keyword_choice!"=="3" (
    set keyword_file=keywords_leggings_only.txt
    echo ✅ Selected: 1 keyword "leggings" (test advertiser scraping)
) else (
    set keyword_file=keywords.txt
    echo ✅ Selected: 50 keywords (quick test)
)
echo.

REM Configure workers/threads
echo ⚙️  PERFORMANCE CONFIGURATION
echo ----------------------------------------
echo Recommended settings based on your system:
echo 1) Laptop/8GB RAM: 2 workers × 5 threads = 10 browsers
echo 2) Desktop/16GB RAM: 3 workers × 10 threads = 30 browsers
echo 3) High-End PC/40GB RAM: 4 workers × 20 threads = 80 browsers
echo 4) Server/64GB+: 5 workers × 20 threads = 100 browsers
echo 5) Custom configuration
echo.
set /p perf_choice="Enter choice (1-5): "

if "!perf_choice!"=="1" (
    set workers=2
    set threads=5
    echo ✅ Laptop config: 2 workers × 5 threads
) else if "!perf_choice!"=="2" (
    set workers=3
    set threads=10
    echo ✅ Desktop config: 3 workers × 10 threads
) else if "!perf_choice!"=="3" (
    set workers=4
    set threads=20
    echo ✅ High-End PC config: 4 workers × 20 threads
) else if "!perf_choice!"=="4" (
    set workers=5
    set threads=20
    echo ✅ Server config: 5 workers × 20 threads
) else if "!perf_choice!"=="5" (
    set /p workers="Number of workers: "
    set /p threads="Threads per worker: "
    echo ✅ Custom config: !workers! workers × !threads! threads
) else (
    set workers=2
    set threads=5
    echo ✅ Default: 2 workers × 5 threads
)
echo.

REM Update distributed_scraper.py
echo 🔧 Configuring scraper settings...
powershell -Command "(Get-Content distributed_scraper.py) -replace 'NUM_WORKERS = \d+', 'NUM_WORKERS = !workers!' | Set-Content distributed_scraper_temp.py"
powershell -Command "(Get-Content distributed_scraper_temp.py) -replace 'THREADS_PER_WORKER = \d+', 'THREADS_PER_WORKER = !threads!' | Set-Content distributed_scraper_temp2.py"
powershell -Command "(Get-Content distributed_scraper_temp2.py) -replace 'KEYWORDS_FILE = \".*?\"', 'KEYWORDS_FILE = \"!keyword_file!\"' | Set-Content distributed_scraper.py"
del distributed_scraper_temp.py distributed_scraper_temp2.py

REM Verify the settings were applied
echo.
echo ✅ Scraper configured with:
echo   Keyword file: !keyword_file!
powershell -Command "gc distributed_scraper.py | Select-String 'KEYWORDS_FILE ='"
echo.

REM Initialize database (CRITICAL STEP!)
echo 🔧 Initializing database...
python init_database.py
if %errorlevel% neq 0 (
    echo ❌ Database initialization failed
    pause
    exit /b 1
)
echo.

REM Start scraping
echo ==========================================
echo 🎯 STARTING SCRAPER
echo ==========================================
echo Configuration:
echo   Workers: !workers!
echo   Threads per worker: !threads!
set /a total_browsers=!workers! * !threads!
echo   Total browsers: !total_browsers!
echo   Keyword file: !keyword_file!
echo.

REM Show keyword count to verify
echo 📋 Keyword file loaded: !keyword_file!
for /f %%C in ('find /c /v "" ^< !keyword_file!') do set keyword_count=%%C
echo ✅ Total keywords: !keyword_count!
echo.
echo Press Ctrl+C to stop at any time
echo Logs: scraper_main.log and logs\worker_*.log
echo.
echo Starting in 3 seconds...
timeout /t 3 /nobreak >nul

python distributed_scraper.py

echo.
echo ==========================================
echo ✅ SCRAPING COMPLETE!
echo ==========================================
echo.
echo 📊 View your data:
echo   python -c "from app.db.repo import get_session; from app.db.models import AdCreative; print(f'Total ads: {next(get_session()).query(AdCreative).count()}')"
echo.
echo 🚀 Start API server:
echo   uvicorn app.api.main:app --host 0.0.0.0 --port 5000
echo.
pause
