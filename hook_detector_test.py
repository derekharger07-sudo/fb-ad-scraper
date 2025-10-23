import cv2
import os
os.environ["CTRANSLATE2_USE_CUDNN"] = "0"  # Force disable cuDNN for faster-whisper
import numpy as np
from ultralytics import YOLO

# === CONFIGURATION ===
VIDEO_PATH = "test_video_fb.mp4"
SECONDS = 6
FRAMES_TO_ANALYZE = 5
MODEL_NAME = "yolov8n.pt"   # small + fast model, auto-downloads once
# =======================

if not os.path.exists(VIDEO_PATH):
    raise FileNotFoundError(f"Video not found: {VIDEO_PATH}")

# Load YOLO model
print("Loading YOLOv8 model locally...")
model = YOLO(MODEL_NAME)

# Open video
cap = cv2.VideoCapture(VIDEO_PATH)
fps = int(cap.get(cv2.CAP_PROP_FPS))
frames_to_read = int(min(cap.get(cv2.CAP_PROP_FRAME_COUNT), fps * SECONDS))
step = max(1, frames_to_read // FRAMES_TO_ANALYZE)

frames = []
for i in range(FRAMES_TO_ANALYZE):
    cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
    ret, frame = cap.read()
    if not ret:
        continue
    frames.append((i * step / fps, frame))  # (timestamp, frame)
cap.release()

print(f"Sampled {len(frames)} frames from the first {SECONDS} s.\n")

from transformers import Blip2Processor, Blip2ForConditionalGeneration
import torch
from PIL import Image

print("\n🧠 Loading BLIP-2 (Flan-T5-XL) model locally...")
processor = Blip2Processor.from_pretrained("Salesforce/blip2-flan-t5-xl")
model = Blip2ForConditionalGeneration.from_pretrained("Salesforce/blip2-flan-t5-xl").to("cuda" if torch.cuda.is_available() else "cpu")

# --- Generate richer captions (BLIP-2 + OCR) ---
from PIL import Image
from transformers import Blip2Processor, Blip2ForConditionalGeneration
import pytesseract
import cv2

print("\n ^=   Loading BLIP-2 (Flan-T5-XL) model locally...")
processor = Blip2Processor.from_pretrained("Salesforce/blip2-flan-t5-xl")
model = Blip2ForConditionalGeneration.from_pretrained("Salesforce/blip2-flan-t5-xl")

print("\n 🔍 Generating richer captions and detecting on-screen text...\n")

frames_captions = []
ocr_texts = []

for idx, (timestamp, frame) in enumerate(frames, start=1):
    # --- BLIP-2 captioning ---
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    inputs = processor(images=pil_img, return_tensors="pt").to(model.device)
    out = model.generate(**inputs, max_new_tokens=40)
    caption = processor.decode(out[0], skip_special_tokens=True)
    frames_captions.append(caption)
    print(f"Frame {idx} ({timestamp:.2f}s): {caption}")

    # --- OCR text detection ---
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)[1]
    text = pytesseract.image_to_string(gray).strip()
    if text:
        ocr_texts.append(text)
        print(f"🧾  OCR @ {timestamp:.2f}s: {text}")

print("\n ✅ Local BLIP-2 captioning and OCR complete.\n")

# --- Subtitles (Whisper) ---
from faster_whisper import WhisperModel

print("\n🎧 Extracting subtitles from the first 6 seconds...")

stt_model = WhisperModel("small", device="cpu")  # change to "cuda" for GPU
AUDIO_PATH = "temp_audio.wav"

# Extract first 6 seconds of audio
os.system(f"ffmpeg -y -i {VIDEO_PATH} -t 6 -ac 1 -ar 16000 -vn {AUDIO_PATH} -loglevel error")

segments, info = stt_model.transcribe(
    AUDIO_PATH,
    beam_size=1,
    language="en",
    vad_filter=False
)

transcript = " ".join([seg.text.strip() for seg in segments]).strip()
print(f"🗣️ Subtitles (0–6s): {transcript if transcript else '[no speech detected]'}")

os.remove(AUDIO_PATH)

# Save transcript for hook analysis
hook_text = transcript

# --- Hook Intelligence Extraction ---
import re, hashlib, json, spacy

nlp = spacy.load("en_core_web_sm")

# pain points: noun chunks
pain_points = [chunk.text.strip() for chunk in nlp(hook_text).noun_chunks]

# benefits: verbs + adjectives following nouns
benefits = []
for token in nlp(hook_text):
    if token.pos_ in ["ADJ", "VERB"] and token.head.pos_ == "NOUN":
        benefits.append(f"{token.head.text} {token.text}")

# --- Hook type ---
hook_type = None
if re.search(r"\bif you\b|\byou need\b", hook_text, re.I):
    hook_type = "If-you/You-address"
elif re.search(r"\blet me show you\b|\bcheck this out\b", hook_text, re.I):
    hook_type = "Demonstration / Let-me-show-you"
elif re.search(r"\bproblem\b|\bsolution\b|\bfix\b", hook_text, re.I):
    hook_type = "Problem → Solution"
elif re.search(r"\blook at\b|\bwatch\b", hook_text, re.I):
    hook_type = "Pattern interrupt"
else:
    hook_type = "Unknown"

# --- Angle detection ---
angles = []
if re.search(r"warm|cozy|cold|winter|fleece", hook_text, re.I):
    angles.append("Warmth/Comfort")
if re.search(r"pain|relief|support", hook_text, re.I):
    angles.append("Pain-Relief")
if re.search(r"quality|durable|material", hook_text, re.I):
    angles.append("Quality/Durability")
if re.search(r"gift|holiday|christmas", hook_text, re.I):
    angles.append("Giftable/Holiday")
if re.search(r"deal|off|free|save|discount", hook_text, re.I):
    angles.append("Deal/Discount")

# --- Seasonality ---
seasonality = []
if re.search(r"winter|cold|snow|holiday", hook_text, re.I):
    seasonality.append("Winter")
if re.search(r"summer|heat|beach", hook_text, re.I):
    seasonality.append("Summer")

# --- Targeting signals ---
targeting_signals = []
if re.search(r"women|leggings|bra|makeup|fashion", hook_text, re.I):
    targeting_signals.append("Women’s apparel/fashion")
if re.search(r"men|gym|fitness|workout", hook_text, re.I):
    targeting_signals.append("Men’s fitness/wear")

# --- CTA stage ---
cta_stage = "TOFU"
if re.search(r"buy|get yours|shop|order now", hook_text, re.I):
    cta_stage = "BOFU"
elif re.search(r"learn|discover|let me show you", hook_text, re.I):
    cta_stage = "MOFU"

# --- Visual tags (from earlier captions) ---
visual_tags = list(set(re.findall(r"\b\w+\b", " ".join(frames_captions))))[:8]

# --- Product category ---
product_category = "Apparel"
if re.search(r"leggings|tights|pants", hook_text, re.I):
    product_category = "Apparel > Bottoms > Leggings"
elif re.search(r"coat|jacket|vest", hook_text, re.I):
    product_category = "Apparel > Outerwear"

# --- Compliance ---
risk_flags = []
if re.search(r"cure|medical|weight loss|FDA", hook_text, re.I):
    risk_flags.append("Health/Medical claim")

# --- Tone ---
tone = []
if re.search(r"warm|love|amazing|cozy", hook_text, re.I):
    tone.append("Positive/Comforting")
if re.search(r"check|look|show", hook_text, re.I):
    tone.append("Conversational")

# --- Fingerprint ---
angle_fingerprint = hashlib.md5((hook_text.lower() + " ".join(angles)).encode()).hexdigest()[:12]

# --- Output ---
output_data = {
    "hook_text": hook_text,
    "hook_type": hook_type,
    "angle": angles,
    "pain_points": pain_points,
    "benefits": benefits,
    "seasonality_cues": seasonality,
    "targeting_signals": targeting_signals,
    "cta_stage": cta_stage,
    "visual_tags@t≤6s": visual_tags,
    "product_category": product_category,
    "compliance_risk_flags": risk_flags,
    "proof_archetype": "UGC demo / try-on",
    "tone_emotion": tone,
    "angle_fingerprint": angle_fingerprint,
}

print("\n📊 Hook Intelligence Extracted:")
for k, v in output_data.items():
    print(f"{k}: {v}")

# Save structured data
with open("hook_outputs.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(output_data, ensure_ascii=False) + "\n")

print("\n✅ Saved to hook_outputs.jsonl")

