from __future__ import annotations


def detect_chart_visuals(path: str) -> str:
    try:
        import cv2
        import numpy as np
        img = cv2.imread(path)
        if img is None:
            return 'Could not read image.'
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 60, 160)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80, minLineLength=40, maxLineGap=8)
        count = 0 if lines is None else len(lines)
        h, w = gray.shape[:2]
        return (
            f'Real chart vision scan complete. Image size {w}x{h}. Detected {count} strong line/candle-like edges. '
            'This module is a safe base for candle/zone detection using OpenCV; use screenshot command for OCR + visual scan.'
        )
    except Exception as e:
        return f'Real chart detection unavailable: {e}'
