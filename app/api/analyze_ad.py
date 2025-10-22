import os
import cv2
import pytesseract
import tempfile
import requests
from openai import OpenAI
from PIL import Image
from io import BytesIO
import base64

def get_openai_client():
    """Lazy initialization of OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)

def extract_video_frames(video_url, frame_interval=2):
    """
    Smart-sampling: capture 1 frame every 2 seconds across the full video.
    Returns a list of PIL images.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.write(requests.get(video_url).content)
    tmp.flush()

    vid = cv2.VideoCapture(tmp.name)
    fps = vid.get(cv2.CAP_PROP_FPS)
    total_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    frames = []
    sec = 0
    while sec < duration:
        vid.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
        success, frame = vid.read()
        if not success:
            break
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        frames.append(img)
        sec += frame_interval

    vid.release()
    tmp.close()
    return frames

def ocr_frames(frames):
    """Extracts all visible text from frames."""
    text_blocks = []
    for frame in frames:
        text = pytesseract.image_to_string(frame)
        if text.strip():
            text_blocks.append(text.strip())
    return " ".join(text_blocks)

def analyze_video(video_url, ad_text=""):
    # Validate video URL
    if not video_url or video_url.strip() == "":
        raise ValueError("Video URL is required for analysis")
    
    print(f"🎬 Starting video analysis for: {video_url[:80]}...")
    
    # Extract frames
    try:
        frames = extract_video_frames(video_url, frame_interval=2)
        print(f"✅ Extracted {len(frames)} frames")
        
        if len(frames) == 0:
            raise ValueError("No frames could be extracted from video - video may be corrupted or inaccessible")
    except Exception as e:
        print(f"❌ Frame extraction failed: {str(e)}")
        raise ValueError(f"Failed to extract video frames: {str(e)}")
    
    # Extract text via OCR
    try:
        ocr_text = ocr_frames(frames)
        print(f"📝 OCR extracted {len(ocr_text)} characters of text")
    except Exception as e:
        print(f"⚠️ OCR failed: {str(e)}, continuing without OCR text")
        ocr_text = ""
    
    combined_text = (ad_text or "") + " " + ocr_text

    prompt = f"""
You are a marketing analysis assistant.

Given the following extracted captions and text from a Facebook ad video, analyze:
- Emotions / tone (happy, frustrated, calm, excited)
- Scene type (before/after, testimonial, product demo, etc.)
- Product focus (clothing, fitness gear, skincare, etc.)
- Call-to-action cues (“limited time”, “link below”, “shop now”)
- Summarize the creative structure (hook, demo, proof, CTA)

TEXT & CAPTIONS:
{combined_text[:4000]}
    """

    # GPT-5 multimodal analysis
    try:
        print(f"🤖 Calling GPT-5 with {len(frames[:10])} frames...")
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are an expert ad marketing analyst."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        *[{"type": "image_url", "image_url": {"url": frame_to_base64(frame)}} for frame in frames[:10]]
                    ]
                }
            ],
            max_completion_tokens=4000  # Increased to allow for reasoning + output tokens
        )
        
        print(f"🔍 GPT Response: {response}")
        print(f"🔍 Response choices: {response.choices}")
        
        analysis = response.choices[0].message.content
        print(f"✅ GPT-5 returned {len(analysis) if analysis else 0} characters of analysis")
        print(f"🔍 Analysis content: {analysis[:200] if analysis else 'NONE'}")
        
        if not analysis or analysis.strip() == "":
            raise ValueError("GPT-5 returned empty analysis")
        
        return analysis
    except Exception as e:
        print(f"❌ GPT-5 analysis failed: {str(e)}")
        raise ValueError(f"AI analysis failed: {str(e)}")

def frame_to_base64(frame):
    """Convert PIL image to base64 data URI for OpenAI Vision models."""
    buf = BytesIO()
    frame.save(buf, format="JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"
