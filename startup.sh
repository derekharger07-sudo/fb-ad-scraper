#!/bin/bash
echo "🚀 Setting up fb-ad-scraper environment..."

# 1️⃣ System prep
apt-get update -y && apt-get install -y \
    tesseract-ocr \
    ffmpeg \
    libgl1 \
    git \
    wget

# 2️⃣ Workspace setup
cd /workspace
if [ ! -d "fb-ad-scraper" ]; then
    echo "📦 Cloning repo..."
    git clone https://github.com/derekharger07-sudo/fb-ad-scraper.git
else
    echo "🔄 Repo exists, pulling latest..."
    cd fb-ad-scraper && git pull
fi
cd fb-ad-scraper

# 3️⃣ Python environment
echo "🐍 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 4️⃣ Ensure spacy model + OCR
python -m spacy download en_core_web_sm
pip install pytesseract openai

# 5️⃣ Environment variables
export OPENAI_API_KEY="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"

# 6️⃣ Verify installs
echo "✅ Verifying key tools..."
tesseract --version
python -c "import cv2, pytesseract, openai, torch; print('✅ All key libs working!')"

# 7️⃣ Optional test run
if [ -f "test_video_fb.mp4" ]; then
    echo "🎬 Running test video analysis..."
    python hook_detector_test.py test_video_fb.mp4
else
    echo "⚠️ test_video_fb.mp4 not found. Skipping test run."
fi

echo "🎯 Setup complete."
