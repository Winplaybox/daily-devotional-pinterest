"""Daily unique AI devotional artwork generator using Google GenAI (with offline fallback)."""

from __future__ import annotations

import base64
from datetime import date
import hashlib
import io
import os
from pathlib import Path

from PIL import Image, ImageDraw

_DAILY_VARIATIONS = [
    "bathed in warm golden-hour sunrise rays with floating flower petals",
    "surrounded by glowing brass temple diyas and morning mist",
    "framed by lush tropical blossoms, hibiscus, and soft ethereal light",
    "set against a radiant celestial dawn sky with soft golden clouds",
    "adorned with sacred marigold garlands and shimmering morning dew",
    "illuminated by serene divine halo rays and peaceful nature scenery",
    "with tranquil river reflections, lotus flowers, and warm amber glow",
]


def build_art_prompt(prompt_subject: str, target_date: date, religion: str) -> str:
    """Build a unique daily image prompt with no embedded text so typography stays crisp."""
    seed = int(hashlib.sha256(f"{religion}:{target_date.isoformat()}".encode()).hexdigest(), 16)
    variation = _DAILY_VARIATIONS[seed % len(_DAILY_VARIATIONS)]
    return (
        f"{prompt_subject}, {variation}. "
        "Vertical 2:3 Pinterest poster composition, leave clean breathing room at the top and bottom "
        "for typography. Rich vibrant colors, devotional aesthetic, no text, no letters, no watermarks, no logos."
    )


def _generate_fallback_art(output_path: Path, accent_hex: str, target_date: date) -> Path:
    """Create a clean gradient + mandala fallback background when GEMINI_API_KEY is not configured."""
    width, height = 1000, 1500
    img = Image.new("RGB", (width, height), "#140b24")
    draw = ImageDraw.Draw(img)

    # Vertical twilight-to-gold gradient
    for y in range(height):
        t = y / height
        r = int(20 + 60 * math_sin_approx(t))
        g = int(12 + 35 * (1 - abs(t - 0.5) * 2))
        b = int(45 + 50 * (1 - t))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Subtle glowing rings in center
    cx, cy = width // 2, int(height * 0.46)
    for radius in range(380, 60, -45):
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=accent_hex,
            width=2,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG")
    return output_path


def math_sin_approx(t: float) -> float:
    import math
    return max(0.0, math.sin(t * math.pi))


def _generate_pollinations_art(
    prompt: str,
    target_date: date,
    religion: str,
    output_path: Path,
) -> Path | None:
    """Free AI image generation fallback via Pollinations when Gemini image quota is 0."""
    from urllib.parse import quote
    import requests

    seed = int(hashlib.sha256(f"{religion}:{target_date.isoformat()}".encode()).hexdigest()[:8], 16)
    url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=1000&height=1500&nologo=true&seed={seed}"
    try:
        resp = requests.get(url, timeout=60)
        if resp.ok and resp.headers.get("content-type", "").startswith("image/"):
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            img = _fit_vertical_poster(img, 1000, 1500)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, format="PNG")
            return output_path
    except Exception:
        return None
    return None


def generate_artwork(
    prompt_subject: str,
    target_date: date,
    religion: str,
    accent_hex: str,
    output_path: Path,
    model: str | None = None,
) -> tuple[Path, bool]:
    """
    Generate daily devotional artwork using Gemini Image API, falling back to
    free Pollinations AI or procedural background if quota/API key is unavailable.
    """
    prompt = build_art_prompt(prompt_subject, target_date, religion)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if api_key and api_key != "your_gemini_api_key_here":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        primary = model or os.getenv("GEMINI_IMAGE_MODEL", "gemini-nano-banana-2.1")
        candidates = [primary]
        if primary != "gemini-3.1-flash-lite-image":
            candidates.append("gemini-3.1-flash-lite-image")

        for model_name in candidates:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    ),
                )
                for part in getattr(response, "parts", []) or []:
                    inline = getattr(part, "inline_data", None)
                    if inline and getattr(inline, "data", None):
                        data = inline.data
                        image_bytes = base64.b64decode(data) if isinstance(data, str) else bytes(data)
                        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                        img = _fit_vertical_poster(img, 1000, 1500)
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        img.save(output_path, format="PNG")
                        return output_path, True
            except Exception as exc:
                print(f"[warn] Gemini model '{model_name}' unavailable ({type(exc).__name__}); trying fallback...")

    pollinations_path = _generate_pollinations_art(prompt, target_date, religion, output_path)
    if pollinations_path is not None:
        return pollinations_path, True

    return _generate_fallback_art(output_path, accent_hex, target_date), False


def _fit_vertical_poster(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Center-crop and resize an image to exact 1000x1500 Pinterest aspect ratio."""
    src_ratio = img.width / img.height
    dst_ratio = target_w / target_h
    if src_ratio > dst_ratio:
        new_w = int(img.height * dst_ratio)
        left = (img.width - new_w) // 2
        img = img.crop((left, 0, left + new_w, img.height))
    elif src_ratio < dst_ratio:
        new_h = int(img.width / dst_ratio)
        top = (img.height - new_h) // 2
        img = img.crop((0, top, img.width, top + new_h))
    return img.resize((target_w, target_h), Image.Resampling.LANCZOS)
