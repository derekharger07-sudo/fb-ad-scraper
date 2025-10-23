import cv2
import os
os.environ["CTRANSLATE2_USE_CUDNN"] = "0"  # Force disable cuDNN for faster-whisper
import numpy as np
from ultralytics import YOLO

# === CONFIGURATION ===
VIDEO_PATH = "test_video.mp4"
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

print("🔍 Generating richer captions for sampled frames...\n")

for idx, (timestamp, frame) in enumerate(frames, start=1):
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    inputs = processor(images=img, return_tensors="pt").to(model.device)
    out = model.generate(**inputs, max_new_tokens=40)
    caption = processor.decode(out[0], skip_special_tokens=True)
    print(f"Frame {idx} ({timestamp:.2f}s): {caption}")

print("\n✅ Local BLIP-2 captioning complete.")

from faster_whisper import WhisperModel

print("\n🎧 Extracting subtitles from the first 6 seconds...")

stt_model = WhisperModel("small", device="cpu")  # 👈 runs fully on CPU

AUDIO_PATH = "temp_audio.wav"
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

