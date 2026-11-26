"""Multilingual devotional poster renderer using HTML/CSS + headless Microsoft Edge."""

from __future__ import annotations

import base64
from html import escape
import os
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

_EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_edge_executable() -> str:
    """Locate Microsoft Edge executable on Windows."""
    custom = os.getenv("EDGE_PATH", "").strip()
    if custom and Path(custom).exists():
        return custom
    for candidate in _EDGE_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError("Microsoft Edge (msedge.exe) not found. Set EDGE_PATH in .env.")


def render_poster(
    background_image: Path,
    output_path: Path,
    weekday_label: str,
    date_label: str,
    tithi_label: str | None,
    greeting_main: str,
    good_morning: str,
    font_family: str,
    text_dir: str = "ltr",
    accent_color: str = "#FFD700",
    brand_tag: str = "",
) -> Path:
    """Composite crisp multilingual typography over the devotional artwork at 1000x1500."""
    bg_b64 = base64.b64encode(background_image.read_bytes()).decode("ascii")
    tithi_html = f'<div class="tithi">{escape(tithi_label)}</div>' if tithi_label else ""
    brand_html = f'<div class="brand">{escape(brand_tag)}</div>' if brand_tag else ""

    html = f"""<!DOCTYPE html>
<html lang="en" dir="{escape(text_dir)}">
<head>
<meta charset="utf-8" />
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
    width: 1000px;
    height: 1500px;
    overflow: hidden;
    font-family: {font_family};
    background: #000;
  }}
  .canvas {{
    position: relative;
    width: 1000px;
    height: 1500px;
    background-image: url('data:image/png;base64,{bg_b64}');
    background-size: cover;
    background-position: center;
  }}
  .top-vignette {{
    position: absolute;
    inset: 0 0 auto 0;
    height: 360px;
    background: linear-gradient(180deg, rgba(10,6,20,0.82) 0%, rgba(10,6,20,0.38) 58%, rgba(10,6,20,0) 100%);
  }}
  .bottom-vignette {{
    position: absolute;
    inset: auto 0 0 0;
    height: 430px;
    background: linear-gradient(0deg, rgba(10,6,20,0.90) 0%, rgba(10,6,20,0.55) 55%, rgba(10,6,20,0) 100%);
  }}
  .frame {{
    position: absolute;
    inset: 18px;
    border: 3px solid rgba(255, 215, 0, 0.55);
    border-radius: 26px;
    pointer-events: none;
  }}
  .header {{
    position: relative;
    z-index: 2;
    padding: 46px 52px 0;
    text-align: center;
  }}
  .weekday {{
    font-size: 74px;
    font-weight: 800;
    line-height: 1.15;
    color: {accent_color};
    text-shadow: 0 4px 16px rgba(0,0,0,0.95), 0 0 28px rgba(0,0,0,0.8);
    letter-spacing: 0.5px;
  }}
  .date-row {{
    margin-top: 18px;
    display: inline-flex;
    align-items: center;
    gap: 16px;
    padding: 10px 28px;
    border-radius: 999px;
    background: rgba(18, 12, 32, 0.72);
    border: 2px solid rgba(255, 215, 0, 0.7);
    box-shadow: 0 6px 20px rgba(0,0,0,0.5);
  }}
  .date-text {{
    font-size: 34px;
    font-weight: 700;
    color: #FFFFFF;
  }}
  .tithi {{
    font-size: 28px;
    font-weight: 600;
    color: {accent_color};
    border-inline-start: 2px solid rgba(255, 215, 0, 0.5);
    padding-inline-start: 16px;
  }}
  .footer {{
    position: absolute;
    z-index: 2;
    left: 48px;
    right: 48px;
    bottom: 54px;
    text-align: center;
  }}
  .morning {{
    font-size: 32px;
    font-weight: 600;
    color: #F7F3E9;
    text-shadow: 0 3px 12px rgba(0,0,0,0.95);
    margin-bottom: 14px;
  }}
  .greeting {{
    font-size: 62px;
    font-weight: 800;
    line-height: 1.22;
    color: {accent_color};
    text-shadow: 0 4px 18px rgba(0,0,0,0.98), 0 0 26px rgba(0,0,0,0.85);
  }}
  .brand {{
    margin-top: 16px;
    font-size: 20px;
    font-weight: 500;
    color: rgba(255,255,255,0.72);
    letter-spacing: 1px;
  }}
</style>
</head>
<body>
  <div class="canvas">
    <div class="top-vignette"></div>
    <div class="bottom-vignette"></div>
    <div class="frame"></div>
    <div class="header">
      <div class="weekday">{escape(weekday_label)}</div>
      <div class="date-row">
        <div class="date-text">{escape(date_label)}</div>
        {tithi_html}
      </div>
    </div>
    <div class="footer">
      <div class="morning">{escape(good_morning)}</div>
      <div class="greeting">{escape(greeting_main)}</div>
      {brand_html}
    </div>
  </div>
</body>
</html>
"""

    edge = find_edge_executable()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        html_file = tmp_path / "poster.html"
        raw_png = tmp_path / "raw.png"
        html_file.write_text(html, encoding="utf-8")

        cmd = [
            edge,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            "--window-size=1000,1500",
            f"--screenshot={raw_png}",
            html_file.as_uri(),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0 or not raw_png.exists():
            raise RuntimeError(
                f"Edge headless screenshot failed (code {result.returncode}): {result.stderr}"
            )

        img = Image.open(raw_png).convert("RGB")
        if img.size != (1000, 1500):
            img = img.crop((0, 0, min(img.width, 1000), min(img.height, 1500)))
            if img.size != (1000, 1500):
                img = img.resize((1000, 1500), Image.Resampling.LANCZOS)
        img.save(output_path, format="PNG")

    return output_path
