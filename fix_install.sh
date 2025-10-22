#!/bin/bash
echo "=========================================="
echo "🔧 FIXING MISSING DEPENDENCIES"
echo "=========================================="
echo ""

echo "Installing missing packages..."
pip3 install python-dateutil==2.8.2
pip3 install opencv-python==4.8.1.78
pip3 install pytesseract==0.3.10
pip3 install openai==1.12.0
pip3 install requests==2.31.0

echo ""
echo "✅ Dependencies fixed!"
echo ""
echo "Now run the scraper again:"
echo "  python3 distributed_scraper.py"
echo ""
