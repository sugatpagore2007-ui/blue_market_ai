"""
Phase 13 Candlestick Intelligence for Blue Forex Market AI.

This module detects a broad library of common Japanese candlestick patterns
from OHLC data without requiring TA-Lib. It is intentionally conservative:
patterns support or warn against a signal, but they never force live trades.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

try:
    from analysis.market_data import fetch_ohlcv
    from analysis.indicators import add_indicators
    from config import TIMEFRAMES
except Exception:  # Lets the detector be imported in isolation during tests.
    fetch_ohlcv = None
    add_indicators = None
    TIMEFRAMES = {}


@dataclass
class PatternHit:
    name: str
    direction: str  # bullish, bearish, neutral
    strength: int   # 1 to 5
    candles: int
    note: str
    index_offset: int = 0  # 0 = latest candle, 1 = previous candle, etc.

    def to_dict(self) -> Dict:
        return asdict(self)


# Most-used pattern catalogue. The detector below implements these families.
PATTERN_CATALOG = {
    "single_candle": [
        "Doji", "Long-Legged Doji", "Dragonfly Doji", "Gravestone Doji", "Spinning Top",
        "High Wave", "Bullish Marubozu", "Bearish Marubozu", "Hammer", "Hanging Man",
        "Inverted Hammer", "Shooting Star", "Bullish Pin Bar", "Bearish Pin Bar",
        "Bullish Belt Hold", "Bearish Belt Hold",
    ],
    "two_candle": [
        "Bullish Engulfing", "Bearish Engulfing", "Piercing Line", "Dark Cloud Cover",
        "Bullish Harami", "Bearish Harami", "Bullish Harami Cross", "Bearish Harami Cross",
        "Tweezer Bottom", "Tweezer Top", "Bullish Kicker", "Bearish Kicker",
        "Matching Low", "Meeting Lines", "On-Neck", "In-Neck", "Thrusting Line",
        "Bullish Separating Lines", "Bearish Separating Lines",
    ],
    "three_plus_candle": [
        "Morning Star", "Evening Star", "Morning Doji Star", "Evening Doji Star",
        "Three White Soldiers", "Three Black Crows", "Three Inside Up", "Three Inside Down",
        "Three Outside Up", "Three Outside Down", "Abandoned Baby Bullish", "Abandoned Baby Bearish",
        "Rising Three Methods", "Falling Three Methods", "Upside Tasuki Gap", "Downside Tasuki Gap",
        "Ladder Bottom", "Advance Block", "Deliberation", "Mat Hold Bullish", "Mat Hold Bearish",
    ],
}


# Optional TA-Lib full CDL* catalogue. If TA-Lib is installed, Blue will scan
# every official TA-Lib candlestick pattern in addition to the built-in fallback
# detectors above. TA-Lib can be tricky to install on Windows, so this stays
# optional and the project works without it.
TALIB_CANDLE_CODES = {
    "CDL2CROWS": "Two Crows",
    "CDL3BLACKCROWS": "Three Black Crows",
    "CDL3INSIDE": "Three Inside Up/Down",
    "CDL3LINESTRIKE": "Three-Line Strike",
    "CDL3OUTSIDE": "Three Outside Up/Down",
    "CDL3STARSINSOUTH": "Three Stars In The South",
    "CDL3WHITESOLDIERS": "Three White Soldiers",
    "CDLABANDONEDBABY": "Abandoned Baby",
    "CDLADVANCEBLOCK": "Advance Block",
    "CDLBELTHOLD": "Belt Hold",
    "CDLBREAKAWAY": "Breakaway",
    "CDLCLOSINGMARUBOZU": "Closing Marubozu",
    "CDLCONCEALBABYSWALL": "Concealing Baby Swallow",
    "CDLCOUNTERATTACK": "Counterattack",
    "CDLDARKCLOUDCOVER": "Dark Cloud Cover",
    "CDLDOJI": "Doji",
    "CDLDOJISTAR": "Doji Star",
    "CDLDRAGONFLYDOJI": "Dragonfly Doji",
    "CDLENGULFING": "Engulfing",
    "CDLEVENINGDOJISTAR": "Evening Doji Star",
    "CDLEVENINGSTAR": "Evening Star",
    "CDLGAPSIDESIDEWHITE": "Up/Down-Gap Side-by-Side White Lines",
    "CDLGRAVESTONEDOJI": "Gravestone Doji",
    "CDLHAMMER": "Hammer",
    "CDLHANGINGMAN": "Hanging Man",
    "CDLHARAMI": "Harami",
    "CDLHARAMICROSS": "Harami Cross",
    "CDLHIGHWAVE": "High-Wave Candle",
    "CDLHIKKAKE": "Hikkake Pattern",
    "CDLHIKKAKEMOD": "Modified Hikkake Pattern",
    "CDLHOMINGPIGEON": "Homing Pigeon",
    "CDLIDENTICAL3CROWS": "Identical Three Crows",
    "CDLINNECK": "In-Neck Pattern",
    "CDLINVERTEDHAMMER": "Inverted Hammer",
    "CDLKICKING": "Kicking",
    "CDLKICKINGBYLENGTH": "Kicking By Length",
    "CDLLADDERBOTTOM": "Ladder Bottom",
    "CDLLONGLEGGEDDOJI": "Long-Legged Doji",
    "CDLLONGLINE": "Long Line Candle",
    "CDLMARUBOZU": "Marubozu",
    "CDLMATCHINGLOW": "Matching Low",
    "CDLMATHOLD": "Mat Hold",
    "CDLMORNINGDOJISTAR": "Morning Doji Star",
    "CDLMORNINGSTAR": "Morning Star",
    "CDLONNECK": "On-Neck Pattern",
    "CDLPIERCING": "Piercing Pattern",
    "CDLRICKSHAWMAN": "Rickshaw Man",
    "CDLRISEFALL3METHODS": "Rising/Falling Three Methods",
    "CDLSEPARATINGLINES": "Separating Lines",
    "CDLSHOOTINGSTAR": "Shooting Star",
    "CDLSHORTLINE": "Short Line Candle",
    "CDLSPINNINGTOP": "Spinning Top",
    "CDLSTALLEDPATTERN": "Stalled Pattern",
    "CDLSTICKSANDWICH": "Stick Sandwich",
    "CDLTAKURI": "Takuri Dragonfly Doji",
    "CDLTASUKIGAP": "Tasuki Gap",
    "CDLTHRUSTING": "Thrusting Pattern",
    "CDLTRISTAR": "Tristar Pattern",
    "CDLUNIQUE3RIVER": "Unique Three River",
    "CDLUPSIDEGAP2CROWS": "Upside Gap Two Crows",
    "CDLXSIDEGAP3METHODS": "Upside/Downside Gap Three Methods",
}


def _talib_available() -> bool:
    try:
        import talib  # type: ignore  # noqa: F401
        return True
    except Exception:
        return False


def _talib_candlestick_patterns(df, lookback: int = 5) -> List[PatternHit]:
    """Detect every TA-Lib CDL* candlestick pattern when TA-Lib is installed.

    TA-Lib outputs positive numbers for bullish patterns and negative numbers for
    bearish patterns. Blue converts those into PatternHit objects so they can be
    used as ML/context features exactly like the built-in detectors.
    """
    hits: List[PatternHit] = []
    if df is None or len(df) < 5:
        return hits
    try:
        import numpy as np  # type: ignore
        import talib  # type: ignore
        opens = np.asarray(df["open"], dtype="float64")
        highs = np.asarray(df["high"], dtype="float64")
        lows = np.asarray(df["low"], dtype="float64")
        closes = np.asarray(df["close"], dtype="float64")
    except Exception:
        return hits

    max_offset = max(1, min(int(lookback or 5), min(10, len(df) - 1)))
    for code, pretty in TALIB_CANDLE_CODES.items():
        try:
            fn = getattr(talib, code, None)
            if fn is None:
                continue
            out = fn(opens, highs, lows, closes)
            for offset in range(max_offset):
                value = int(out[-1 - offset])
                if value == 0:
                    continue
                direction = "bullish" if value > 0 else "bearish"
                strength = 5 if abs(value) >= 200 else 4 if abs(value) >= 100 else 3
                hits.append(PatternHit(
                    name=f"TA-Lib {pretty}",
                    direction=direction,
                    strength=strength,
                    candles=1,
                    note=f"TA-Lib {code} detected a {direction} pattern score {value}.",
                    index_offset=offset,
                ))
        except Exception:
            continue
    return _dedupe_hits(hits)


def _safe_float(x, default: float = 0.0) -> float:
    try:
        if x != x:
            return default
        return float(x)
    except Exception:
        return default


def _row(df, offset: int = 0) -> Optional[Dict[str, float]]:
    if df is None or len(df) <= offset:
        return None
    r = df.iloc[-1 - offset]
    return {
        "open": _safe_float(r.get("open")),
        "high": _safe_float(r.get("high")),
        "low": _safe_float(r.get("low")),
        "close": _safe_float(r.get("close")),
    }


def _body(c: Dict[str, float]) -> float:
    return abs(c["close"] - c["open"])


def _range(c: Dict[str, float]) -> float:
    return max(c["high"] - c["low"], 1e-12)


def _upper_wick(c: Dict[str, float]) -> float:
    return c["high"] - max(c["open"], c["close"])


def _lower_wick(c: Dict[str, float]) -> float:
    return min(c["open"], c["close"]) - c["low"]


def _bull(c: Dict[str, float]) -> bool:
    return c["close"] > c["open"]


def _bear(c: Dict[str, float]) -> bool:
    return c["close"] < c["open"]


def _mid(c: Dict[str, float]) -> float:
    return (c["open"] + c["close"]) / 2


def _near(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


def _avg_body(df, n: int = 20) -> float:
    if df is None or len(df) == 0:
        return 0.0
    tail = df.tail(min(n, len(df)))
    bodies = [abs(_safe_float(r["close"]) - _safe_float(r["open"])) for _, r in tail.iterrows()]
    return sum(bodies) / len(bodies) if bodies else 0.0


def _trend_hint(df, offset: int = 0, lookback: int = 8) -> str:
    """Simple local trend hint before the pattern."""
    if df is None or len(df) < lookback + offset + 1:
        return "unknown"
    end = len(df) - offset
    start = max(0, end - lookback)
    closes = list(df.iloc[start:end]["close"])
    if len(closes) < 3:
        return "unknown"
    first = _safe_float(closes[0])
    last = _safe_float(closes[-1])
    move = last - first
    threshold = max(abs(first) * 0.001, 1e-6)
    if move > threshold:
        return "uptrend"
    if move < -threshold:
        return "downtrend"
    return "sideways"


def _single_candle_patterns(df, offset: int = 0) -> List[PatternHit]:
    hits: List[PatternHit] = []
    c = _row(df, offset)
    if not c:
        return hits
    body = _body(c)
    rng = _range(c)
    up = _upper_wick(c)
    low = _lower_wick(c)
    avg_body = max(_avg_body(df, 20), rng * 0.05, 1e-12)
    trend = _trend_hint(df, offset=offset + 1)

    body_ratio = body / rng
    upper_ratio = up / rng
    lower_ratio = low / rng

    if body_ratio <= 0.07:
        hits.append(PatternHit("Doji", "neutral", 2, 1, "Open and close are almost equal; indecision candle.", offset))
        if upper_ratio >= 0.35 and lower_ratio >= 0.35:
            hits.append(PatternHit("Long-Legged Doji", "neutral", 3, 1, "Long wicks on both sides show strong indecision and liquidity grabs.", offset))
        if lower_ratio >= 0.60 and upper_ratio <= 0.12:
            hits.append(PatternHit("Dragonfly Doji", "bullish", 3, 1, "Long lower wick with close near high; possible rejection from lows.", offset))
        if upper_ratio >= 0.60 and lower_ratio <= 0.12:
            hits.append(PatternHit("Gravestone Doji", "bearish", 3, 1, "Long upper wick with close near low; possible rejection from highs.", offset))

    if 0.08 < body_ratio <= 0.30 and upper_ratio >= 0.25 and lower_ratio >= 0.25:
        hits.append(PatternHit("Spinning Top", "neutral", 2, 1, "Small body with wicks both sides; momentum is not clean.", offset))
    if body_ratio <= 0.30 and upper_ratio >= 0.35 and lower_ratio >= 0.35:
        hits.append(PatternHit("High Wave", "neutral", 2, 1, "Large wicks both sides; market is volatile and undecided.", offset))

    if body >= avg_body * 1.2 and upper_ratio <= 0.08 and lower_ratio <= 0.08:
        if _bull(c):
            hits.append(PatternHit("Bullish Marubozu", "bullish", 4, 1, "Strong bullish candle with almost no wick rejection.", offset))
        elif _bear(c):
            hits.append(PatternHit("Bearish Marubozu", "bearish", 4, 1, "Strong bearish candle with almost no wick rejection.", offset))

    # Hammer family: small real body, long lower wick.
    if lower_ratio >= 0.55 and upper_ratio <= 0.20 and body_ratio <= 0.35:
        direction = "bullish" if trend in ["downtrend", "unknown", "sideways"] else "bearish"
        name = "Hammer" if direction == "bullish" else "Hanging Man"
        note = "Long lower wick shows buyers rejected lower prices." if direction == "bullish" else "Long lower wick after an uptrend can warn of weakening buyers."
        hits.append(PatternHit(name, direction, 4 if direction == "bullish" else 3, 1, note, offset))
        hits.append(PatternHit("Bullish Pin Bar" if direction == "bullish" else "Bearish Pin Bar", direction, 3, 1, "Pin bar wick rejection pattern.", offset))

    # Inverted hammer family: small body, long upper wick.
    if upper_ratio >= 0.55 and lower_ratio <= 0.20 and body_ratio <= 0.35:
        direction = "bullish" if trend in ["downtrend", "unknown", "sideways"] else "bearish"
        name = "Inverted Hammer" if direction == "bullish" else "Shooting Star"
        note = "Upper wick after downside may show early reversal pressure." if direction == "bullish" else "Upper wick after upside shows rejection from highs."
        hits.append(PatternHit(name, direction, 3 if direction == "bullish" else 4, 1, note, offset))
        hits.append(PatternHit("Bullish Pin Bar" if direction == "bullish" else "Bearish Pin Bar", direction, 3, 1, "Pin bar wick rejection pattern.", offset))

    # Belt hold: opens near extreme and pushes strongly one way.
    if _bull(c) and body >= avg_body and lower_ratio <= 0.10 and c["close"] > c["open"]:
        hits.append(PatternHit("Bullish Belt Hold", "bullish", 3, 1, "Bullish candle opened near low and pushed upward.", offset))
    if _bear(c) and body >= avg_body and upper_ratio <= 0.10 and c["close"] < c["open"]:
        hits.append(PatternHit("Bearish Belt Hold", "bearish", 3, 1, "Bearish candle opened near high and pushed downward.", offset))

    return _dedupe_hits(hits)


def _two_candle_patterns(df, offset: int = 0) -> List[PatternHit]:
    hits: List[PatternHit] = []
    c1 = _row(df, offset + 1)  # previous
    c2 = _row(df, offset)      # latest
    if not c1 or not c2:
        return hits
    avg_body = max(_avg_body(df, 20), 1e-12)
    b1, b2 = _body(c1), _body(c2)
    tol = max((_range(c1) + _range(c2)) / 2 * 0.08, 1e-8)

    # Engulfing.
    if _bear(c1) and _bull(c2) and c2["open"] <= c1["close"] and c2["close"] >= c1["open"] and b2 >= b1 * 0.9:
        hits.append(PatternHit("Bullish Engulfing", "bullish", 5, 2, "Bullish candle engulfed the previous bearish body.", offset))
    if _bull(c1) and _bear(c2) and c2["open"] >= c1["close"] and c2["close"] <= c1["open"] and b2 >= b1 * 0.9:
        hits.append(PatternHit("Bearish Engulfing", "bearish", 5, 2, "Bearish candle engulfed the previous bullish body.", offset))

    # Piercing and dark cloud.
    if _bear(c1) and _bull(c2) and c2["open"] < c1["low"] + tol and c2["close"] > _mid(c1) and c2["close"] < c1["open"]:
        hits.append(PatternHit("Piercing Line", "bullish", 4, 2, "Bullish candle pierced above midpoint of prior bearish candle.", offset))
    if _bull(c1) and _bear(c2) and c2["open"] > c1["high"] - tol and c2["close"] < _mid(c1) and c2["close"] > c1["open"]:
        hits.append(PatternHit("Dark Cloud Cover", "bearish", 4, 2, "Bearish candle closed below midpoint of prior bullish candle.", offset))

    # Harami / inside body.
    c2_body_inside_c1 = max(c2["open"], c2["close"]) <= max(c1["open"], c1["close"]) and min(c2["open"], c2["close"]) >= min(c1["open"], c1["close"])
    if c2_body_inside_c1 and b1 >= avg_body * 0.8:
        is_cross = b2 <= _range(c2) * 0.08
        if _bear(c1) and (_bull(c2) or is_cross):
            hits.append(PatternHit("Bullish Harami Cross" if is_cross else "Bullish Harami", "bullish", 3 if is_cross else 3, 2, "Small candle inside prior bearish body; possible downside pause/reversal.", offset))
        if _bull(c1) and (_bear(c2) or is_cross):
            hits.append(PatternHit("Bearish Harami Cross" if is_cross else "Bearish Harami", "bearish", 3 if is_cross else 3, 2, "Small candle inside prior bullish body; possible upside pause/reversal.", offset))

    # Tweezers.
    if _near(c1["low"], c2["low"], tol) and (_bear(c1) or _bull(c2)):
        hits.append(PatternHit("Tweezer Bottom", "bullish", 3, 2, "Two candles rejected nearly the same low.", offset))
    if _near(c1["high"], c2["high"], tol) and (_bull(c1) or _bear(c2)):
        hits.append(PatternHit("Tweezer Top", "bearish", 3, 2, "Two candles rejected nearly the same high.", offset))

    # Kicker patterns: gap/reversal strength. In forex gaps are uncommon, so use body separation tolerance.
    if _bear(c1) and _bull(c2) and c2["open"] > c1["open"] + tol and b2 >= avg_body * 0.8:
        hits.append(PatternHit("Bullish Kicker", "bullish", 5, 2, "Strong bullish reversal with separation from previous bearish candle.", offset))
    if _bull(c1) and _bear(c2) and c2["open"] < c1["open"] - tol and b2 >= avg_body * 0.8:
        hits.append(PatternHit("Bearish Kicker", "bearish", 5, 2, "Strong bearish reversal with separation from previous bullish candle.", offset))

    # Other classic two-candle names.
    if _bear(c1) and _bear(c2) and _near(c1["close"], c2["close"], tol) and c2["low"] >= c1["low"] - tol:
        hits.append(PatternHit("Matching Low", "bullish", 2, 2, "Two bearish candles close near same low; sellers may be losing follow-through.", offset))
    if _bear(c1) and _bull(c2) and _near(c1["close"], c2["close"], tol):
        hits.append(PatternHit("Meeting Lines", "bullish", 2, 2, "Bullish candle met previous bearish close; possible selling exhaustion.", offset))
    if _bull(c1) and _bear(c2) and _near(c1["close"], c2["close"], tol):
        hits.append(PatternHit("Meeting Lines", "bearish", 2, 2, "Bearish candle met previous bullish close; possible buying exhaustion.", offset))

    if _bear(c1) and _bull(c2) and c2["open"] < c1["low"] and c2["close"] <= c1["close"] + tol:
        hits.append(PatternHit("On-Neck", "bearish", 2, 2, "Weak bullish response after bearish candle; bearish continuation caution.", offset))
    if _bear(c1) and _bull(c2) and c2["open"] < c1["low"] and c1["close"] < c2["close"] < _mid(c1):
        hits.append(PatternHit("In-Neck", "bearish", 2, 2, "Small recovery below midpoint; bearish continuation caution.", offset))
    if _bear(c1) and _bull(c2) and c2["open"] < c1["low"] and c2["close"] < _mid(c1):
        hits.append(PatternHit("Thrusting Line", "bearish", 2, 2, "Recovery failed to close above midpoint of prior bearish candle.", offset))

    # Separating lines: same-ish open, opposite color, continuation style.
    if _bear(c1) and _bull(c2) and _near(c1["open"], c2["open"], tol) and b2 >= avg_body * 0.6:
        hits.append(PatternHit("Bullish Separating Lines", "bullish", 3, 2, "Bullish continuation candle opened near prior open and pushed up.", offset))
    if _bull(c1) and _bear(c2) and _near(c1["open"], c2["open"], tol) and b2 >= avg_body * 0.6:
        hits.append(PatternHit("Bearish Separating Lines", "bearish", 3, 2, "Bearish continuation candle opened near prior open and pushed down.", offset))

    return _dedupe_hits(hits)


def _three_plus_patterns(df, offset: int = 0) -> List[PatternHit]:
    hits: List[PatternHit] = []
    c1 = _row(df, offset + 2)
    c2 = _row(df, offset + 1)
    c3 = _row(df, offset)
    c4 = _row(df, offset + 3)
    c5 = _row(df, offset + 4)
    if not c1 or not c2 or not c3:
        return hits
    avg_body = max(_avg_body(df, 20), 1e-12)
    b1, b2, b3 = _body(c1), _body(c2), _body(c3)
    tol = max((_range(c1) + _range(c2) + _range(c3)) / 3 * 0.08, 1e-8)
    c2_small = b2 <= avg_body * 0.65 or b2 <= _range(c2) * 0.25
    c2_doji = b2 <= _range(c2) * 0.08

    # Star patterns.
    if _bear(c1) and c2_small and _bull(c3) and c3["close"] > _mid(c1):
        hits.append(PatternHit("Morning Doji Star" if c2_doji else "Morning Star", "bullish", 5 if c2_doji else 4, 3, "Bearish drive, pause candle, then bullish close above midpoint.", offset))
    if _bull(c1) and c2_small and _bear(c3) and c3["close"] < _mid(c1):
        hits.append(PatternHit("Evening Doji Star" if c2_doji else "Evening Star", "bearish", 5 if c2_doji else 4, 3, "Bullish drive, pause candle, then bearish close below midpoint.", offset))

    # Three soldiers / crows.
    if _bull(c1) and _bull(c2) and _bull(c3) and c2["close"] > c1["close"] and c3["close"] > c2["close"] and min(b1, b2, b3) >= avg_body * 0.45:
        hits.append(PatternHit("Three White Soldiers", "bullish", 5, 3, "Three strong bullish candles closing higher.", offset))
    if _bear(c1) and _bear(c2) and _bear(c3) and c2["close"] < c1["close"] and c3["close"] < c2["close"] and min(b1, b2, b3) >= avg_body * 0.45:
        hits.append(PatternHit("Three Black Crows", "bearish", 5, 3, "Three strong bearish candles closing lower.", offset))

    # Advance block / deliberation: still bullish but warning of exhaustion.
    if _bull(c1) and _bull(c2) and _bull(c3) and c2["close"] > c1["close"] and c3["close"] > c2["close"]:
        if b1 > b2 > b3 and _upper_wick(c3) > b3 * 0.6:
            hits.append(PatternHit("Advance Block", "bearish", 3, 3, "Three bullish candles show shrinking bodies and upper rejection; upside may be tiring.", offset))
        if b3 <= b2 * 0.65 and b2 <= b1 * 0.85:
            hits.append(PatternHit("Deliberation", "bearish", 2, 3, "Uptrend candles are slowing; possible bullish exhaustion.", offset))

    # Inside/outside patterns.
    if _bear(c1) and c2["high"] <= c1["high"] and c2["low"] >= c1["low"] and _bull(c3) and c3["close"] > c1["high"] - tol:
        hits.append(PatternHit("Three Inside Up", "bullish", 4, 3, "Harami-like inside candle followed by bullish breakout.", offset))
    if _bull(c1) and c2["high"] <= c1["high"] and c2["low"] >= c1["low"] and _bear(c3) and c3["close"] < c1["low"] + tol:
        hits.append(PatternHit("Three Inside Down", "bearish", 4, 3, "Harami-like inside candle followed by bearish breakdown.", offset))
    if _bear(c1) and _bull(c2) and c2["open"] <= c1["close"] and c2["close"] >= c1["open"] and _bull(c3) and c3["close"] > c2["close"]:
        hits.append(PatternHit("Three Outside Up", "bullish", 4, 3, "Bullish engulfing followed by further bullish confirmation.", offset))
    if _bull(c1) and _bear(c2) and c2["open"] >= c1["close"] and c2["close"] <= c1["open"] and _bear(c3) and c3["close"] < c2["close"]:
        hits.append(PatternHit("Three Outside Down", "bearish", 4, 3, "Bearish engulfing followed by further bearish confirmation.", offset))

    # Abandoned baby: gap-like star between candle 1 and 3. Forex gaps are rare; conservative approximation.
    if _bear(c1) and c2_doji and _bull(c3) and c2["high"] < c1["low"] + tol and c2["high"] < c3["low"] + tol:
        hits.append(PatternHit("Abandoned Baby Bullish", "bullish", 5, 3, "Doji-like gap/rejection between bearish and bullish candles.", offset))
    if _bull(c1) and c2_doji and _bear(c3) and c2["low"] > c1["high"] - tol and c2["low"] > c3["high"] - tol:
        hits.append(PatternHit("Abandoned Baby Bearish", "bearish", 5, 3, "Doji-like gap/rejection between bullish and bearish candles.", offset))

    # Ladder bottom: three/four red candles then bullish reversal.
    if c4 and _bear(c4) and _bear(c1) and _bear(c2) and _bull(c3) and _lower_wick(c2) > _body(c2) * 0.5 and c3["close"] > c2["open"]:
        hits.append(PatternHit("Ladder Bottom", "bullish", 4, 4, "Bearish sequence with lower wick rejection and bullish recovery.", offset))

    # Five-candle continuation patterns.
    if c4 and c5:
        # Chronological order for five candles: d1 oldest, d5 latest.
        d1, d2, d3, d4, d5 = c5, c4, c1, c2, c3
        mid_three = [d2, d3, d4]
        if _bull(d1) and all(_bear(x) for x in mid_three) and _bull(d5) and d5["close"] > d1["close"] and all(d1["low"] <= x["low"] and x["high"] <= d1["high"] for x in mid_three):
            hits.append(PatternHit("Rising Three Methods", "bullish", 5, 5, "Bullish continuation: strong up candle, controlled pullback, bullish breakout.", offset))
        if _bear(d1) and all(_bull(x) for x in mid_three) and _bear(d5) and d5["close"] < d1["close"] and all(d1["low"] <= x["low"] and x["high"] <= d1["high"] for x in mid_three):
            hits.append(PatternHit("Falling Three Methods", "bearish", 5, 5, "Bearish continuation: strong down candle, controlled bounce, bearish breakdown.", offset))
        if _bull(d1) and all((_bear(x) or _bull(x)) for x in mid_three) and _bull(d5) and d5["close"] > d1["close"] and min(_body(d1), _body(d5)) >= avg_body * 0.8:
            hits.append(PatternHit("Mat Hold Bullish", "bullish", 3, 5, "Bullish continuation family: strong candles hold trend after small pause.", offset))
        if _bear(d1) and all((_bear(x) or _bull(x)) for x in mid_three) and _bear(d5) and d5["close"] < d1["close"] and min(_body(d1), _body(d5)) >= avg_body * 0.8:
            hits.append(PatternHit("Mat Hold Bearish", "bearish", 3, 5, "Bearish continuation family: strong candles hold trend after small pause.", offset))

    # Tasuki gap approximations.
    if c1["low"] > c2["high"] and _bull(c1) and _bear(c2) and _bull(c3) and c3["close"] > c1["close"]:
        hits.append(PatternHit("Upside Tasuki Gap", "bullish", 3, 3, "Bullish gap continuation approximation.", offset))
    if c1["high"] < c2["low"] and _bear(c1) and _bull(c2) and _bear(c3) and c3["close"] < c1["close"]:
        hits.append(PatternHit("Downside Tasuki Gap", "bearish", 3, 3, "Bearish gap continuation approximation.", offset))

    return _dedupe_hits(hits)


def _dedupe_hits(hits: List[PatternHit]) -> List[PatternHit]:
    seen = set()
    out = []
    for h in hits:
        key = (h.name, h.direction, h.index_offset)
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out


def detect_candlestick_patterns(df, lookback: int = 5) -> Dict:
    """Detect current and recent candlestick patterns.

    Returns a stable dictionary that can be embedded into Blue's signal output.
    """
    if df is None or len(df) < 5:
        return {
            "available": False,
            "note": "Not enough candles for candlestick detection.",
            "current_patterns": [], "recent_patterns": [], "bullish_score": 0, "bearish_score": 0,
            "net_score": 0, "confidence_delta": 0, "bias": "neutral",
        }

    lookback = max(1, min(int(lookback or 5), min(10, len(df) - 1)))
    all_hits: List[PatternHit] = []
    for offset in range(lookback):
        all_hits.extend(_single_candle_patterns(df, offset))
        all_hits.extend(_two_candle_patterns(df, offset))
        all_hits.extend(_three_plus_patterns(df, offset))

    # Optional: when TA-Lib is installed, scan the full CDL* candlestick library too.
    talib_hits = _talib_candlestick_patterns(df, lookback=lookback)
    all_hits.extend(talib_hits)

    # Recent hits get less weight than the current candle.
    bullish_score = 0.0
    bearish_score = 0.0
    neutral_score = 0.0
    for h in all_hits:
        recency_weight = max(0.35, 1.0 - h.index_offset * 0.14)
        points = h.strength * recency_weight
        if h.direction == "bullish":
            bullish_score += points
        elif h.direction == "bearish":
            bearish_score += points
        else:
            neutral_score += points
    net_score = bullish_score - bearish_score
    if net_score >= 4:
        bias = "bullish"
    elif net_score <= -4:
        bias = "bearish"
    else:
        bias = "neutral"

    # Small advisory confidence delta only; strong patterns can add/reduce but not dominate ML/risk.
    confidence_delta = int(max(-8, min(8, round(net_score))))
    current = [h.to_dict() for h in all_hits if h.index_offset == 0]
    recent = [h.to_dict() for h in all_hits if h.index_offset > 0]
    top = sorted(all_hits, key=lambda h: (h.index_offset, -h.strength))[:8]
    top_names = [f"{h.name} ({h.direction})" for h in top[:5]]

    note = "No strong candle pattern detected; use SMC/ML/context first."
    if top_names:
        note = "Detected: " + "; ".join(top_names) + "."
        if neutral_score >= 5 and abs(net_score) < 4:
            note += " Several indecision candles detected, so avoid forcing entries."

    return {
        "available": True,
        "catalog_count": sum(len(v) for v in PATTERN_CATALOG.values()),
        "talib_catalog_count": len(TALIB_CANDLE_CODES),
        "talib_available": _talib_available(),
        "talib_patterns_detected": len(talib_hits),
        "catalog": PATTERN_CATALOG,
        "current_patterns": current,
        "recent_patterns": recent[:20],
        "top_patterns": [h.to_dict() for h in top],
        "bullish_score": round(bullish_score, 2),
        "bearish_score": round(bearish_score, 2),
        "neutral_score": round(neutral_score, 2),
        "net_score": round(net_score, 2),
        "confidence_delta": confidence_delta,
        "bias": bias,
        "note": note,
    }


def apply_candlestick_brain(signal: Dict) -> Dict:
    """Apply candle-pattern intelligence to a signal.

    Candlestick patterns only support/warn/block. They do not create a trade by themselves.
    """
    candle = signal.get("candlestick_brain") or {}
    if not candle.get("available"):
        return signal

    action = (signal.get("action") or "WAIT").upper()
    old_confidence = int(signal.get("confidence") or 0)
    delta = int(candle.get("confidence_delta") or 0)
    bias = candle.get("bias") or "neutral"
    decision = "ADVISORY_ONLY"
    notes: List[str] = []

    if action == "BUY":
        if bias == "bullish":
            decision = "CONFIRMS_BUY"
            notes.append("Candlestick bias supports the BUY idea.")
        elif bias == "bearish":
            decision = "WARNS_AGAINST_BUY"
            delta = min(delta, -4)
            notes.append("Bearish candle pattern conflicts with BUY, so confidence is reduced.")
    elif action == "SELL":
        if bias == "bearish":
            decision = "CONFIRMS_SELL"
            notes.append("Candlestick bias supports the SELL idea.")
            delta = abs(delta) if delta < 0 else delta
        elif bias == "bullish":
            decision = "WARNS_AGAINST_SELL"
            delta = -abs(delta) if delta else -4
            notes.append("Bullish candle pattern conflicts with SELL, so confidence is reduced.")
    else:
        decision = "NO_TRADE_CONTEXT"
        notes.append("Patterns were detected but Blue is already in WAIT mode.")
        delta = 0

    new_confidence = int(max(0, min(95, old_confidence + delta)))
    signal["confidence"] = new_confidence

    # If the trade was already weak and candles conflict, turn it into WAIT.
    if action != "WAIT" and decision.startswith("WARNS") and new_confidence < 70:
        signal["action"] = "WAIT"
        notes.append("Trade changed to WAIT because candle conflict pushed confidence below 70%.")

    candle["decision"] = decision
    candle["old_confidence"] = old_confidence
    candle["new_confidence"] = signal.get("confidence")
    candle["applied_delta"] = delta
    candle["integration_note"] = " ".join(notes) if notes else "Candlestick patterns recorded as context only."
    signal["candlestick_brain"] = candle
    return signal


def candlestick_help() -> str:
    return """Phase 13 Candlestick Intelligence commands:

candles gold              Detect candle patterns on gold 5m entry chart
candles eurusd 15m        Detect candle patterns on a specific timeframe
candlestick patterns      Show the supported pattern catalogue
phase13 status            Show candlestick engine status

Blue uses candles as confirmation only. Candles can support a signal, warn against it, or block a weak trade, but they do not force live orders.
"""


def candlestick_catalog_text() -> str:
    lines = ["Phase 13/14 Candlestick Pattern Catalogue"]
    total = 0
    for group, names in PATTERN_CATALOG.items():
        total += len(names)
        label = group.replace("_", " ").title()
        lines.append(f"\n{label}:")
        for name in names:
            lines.append(f"- {name}")
    lines.append(f"\nBuilt-in supported pattern names: {total}")
    lines.append(f"Optional TA-Lib CDL* patterns available when installed: {len(TALIB_CANDLE_CODES)}")
    lines.append(f"TA-Lib currently installed: {_talib_available()}")
    lines.append("Note: Detection is rule-based and conservative. Use with trend, SMC, ML, risk, and news filters.")
    return "\n".join(lines)


def phase13_status_text() -> str:
    total = sum(len(v) for v in PATTERN_CATALOG.values())
    return (
        "Phase 13 Candlestick Intelligence: ACTIVE\n"
        f"Built-in pattern catalogue: {total}+ common candlestick patterns\n"
        f"Optional TA-Lib full CDL* catalogue: {len(TALIB_CANDLE_CODES)} patterns | installed: {_talib_available()}\n"
        "Connected to signal engine: yes\n"
        "Mode: confirmation / warning / no-trade filter only\n"
        "Live trading force: disabled — candles never force orders alone\n"
        "Commands: candles gold | candles eurusd 15m | candlestick patterns | candle help"
    )


def candlestick_report_for_symbol(symbol_name: str, ticker: str, timeframe: str = "5m") -> str:
    if fetch_ohlcv is None or add_indicators is None:
        return "Candlestick report unavailable: market data modules could not be imported."
    tf = (timeframe or "5m").lower().strip()
    if tf not in TIMEFRAMES:
        tf = "5m" if "5m" in TIMEFRAMES else next(iter(TIMEFRAMES), "15m")
    cfg = TIMEFRAMES[tf]
    try:
        df = add_indicators(fetch_ohlcv(ticker, cfg["interval"], cfg["period"]))
        report = detect_candlestick_patterns(df, lookback=5)
    except Exception as exc:
        return f"Could not build candlestick report for {symbol_name}: {exc}"

    lines = [f"Candlestick report: {symbol_name} | TF: {tf}", "-" * 54]
    lines.append(f"Bias: {report.get('bias')} | Bullish score: {report.get('bullish_score')} | Bearish score: {report.get('bearish_score')} | Delta: {report.get('confidence_delta')}")
    lines.append(f"TA-Lib optional scanner: {report.get('talib_available')} | TA-Lib patterns found: {report.get('talib_patterns_detected', 0)}")
    lines.append(report.get("note", ""))
    top = report.get("top_patterns") or []
    if top:
        lines.append("\nTop detected patterns:")
        for p in top[:10]:
            lines.append(f"- {p.get('name')} | {p.get('direction')} | strength {p.get('strength')} | {p.get('note')}")
    else:
        lines.append("No major current/recent candle pattern detected.")
    return "\n".join(lines)
