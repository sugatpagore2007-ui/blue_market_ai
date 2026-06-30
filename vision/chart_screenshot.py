from __future__ import annotations
import os
from PIL import Image

def analyze_chart_screenshot(path: str):
    if not os.path.exists(path):
        return {"ok": False, "summary": f"Image not found: {path}"}
    try:
        img = Image.open(path).convert('RGB')
        w, h = img.size
        # Lightweight visual scan: brightness/contrast + rough dominant direction placeholder.
        pixels = list(img.resize((80, 60)).getdata())
        avg = sum(sum(p) for p in pixels) / (len(pixels) * 3)
        left = pixels[:len(pixels)//2]; right = pixels[len(pixels)//2:]
        left_b = sum(sum(p) for p in left) / (len(left) * 3)
        right_b = sum(sum(p) for p in right) / (len(right) * 3)
        bias = "possible bullish/right-side strength" if right_b > left_b else "possible bearish/right-side weakness"
        return {
            "ok": True,
            "width": w, "height": h,
            "brightness": round(avg, 2),
            "visual_bias": bias,
            "summary": "Screenshot read complete. This module is a safe computer-vision base; add candle/object detection model later for exact chart markings."
        }
    except Exception as exc:
        return {"ok": False, "summary": f"Could not analyze screenshot: {exc}"}
