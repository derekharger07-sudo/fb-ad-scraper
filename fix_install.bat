@echo off
echo ==========================================
echo 🔧 FIXING MISSING DEPENDENCIES
echo ==========================================
echo.

echo Installing missing packages...
pip install python-dateutil==2.8.2
pip install opencv-python==4.8.1.78
pip install pytesseract==0.3.10
pip install openai==1.12.0
pip install requests==2.31.0

echo.
echo ✅ Dependencies fixed!
echo.
echo Now run the scraper again:
echo   python distributed_scraper.py
echo.
pause
