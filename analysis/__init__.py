"""Analysis package for Blue Forex Market AI."""

try:
    from .candlestick_patterns import (
        PatternHit,
        PATTERN_CATALOG,
        TALIB_CANDLE_CODES,
        detect_candlestick_patterns,
        apply_candlestick_brain,
        candlestick_help,
        candlestick_catalog_text,
        candlestick_report_for_symbol,
        phase13_status_text,
    )
except Exception:  # keep package import safe when optional deps are missing
    pass
