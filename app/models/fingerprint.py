import io
from PIL import Image
import imagehash
from urllib.parse import urlparse

def image_bytes_phash(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return str(imagehash.phash(img))

def landing_key(url: str | None) -> str:
    if not url:
        return "unknown-landing"
    d = urlparse(url).netloc.lower().split(":")[0]
    return d or "unknown-landing"

def combine_product_hash(frame_hash: str, landing: str) -> str:
    return f"{frame_hash[:8]}-{landing}"
