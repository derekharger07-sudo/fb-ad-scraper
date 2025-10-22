from typing import List

HOOK_RULES = {
    "testimonial": ["i've been using", "honest review", "after 2 weeks", "my experience"],
    "bodycam": ["pov", "body cam", "first-person"],
    "pain": ["hurts", "problem", "struggle", "cold", "itchy", "back pain", "cramps"],
    "doctor": ["doctor", "dermatologist", "physio", "nurse", "expert"],
    "before_after": ["before", "after", "transformation"],
    "warmth": ["warm", "cozy", "fleece", "winter", "cold"],
}

def tag_angles(caption: str | None) -> List[str]:
    if not caption:
        return ["generic_ugc"]
    c = caption.lower()
    tags = set()
    for tag, keys in HOOK_RULES.items():
        if any(k in c for k in keys):
            tags.add(tag)
    return list(tags) or ["generic_ugc"]
