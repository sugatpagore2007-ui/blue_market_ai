from __future__ import annotations


def live_chart_ocr_hint():
    return (
        'Live chart OCR mode: take a screenshot from TradingView or MT5, then run: screenshot <path>. '
        'The module reads visible text with OCR when pytesseract is installed and combines it with SMC analysis. '
        'For best results keep symbol, timeframe, price scale, and candles visible.'
    )
