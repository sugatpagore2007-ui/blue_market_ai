from dataclasses import dataclass
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from config import SWING_LOOKBACK, FVG_LOOKBACK_BARS, OB_LOOKBACK_BARS, LIQUIDITY_LOOKBACK_BARS, PREMIUM_DISCOUNT_LOOKBACK

@dataclass
class Zone:
    kind: str
    direction: str
    low: float
    high: float
    index: str
    strength: int = 1


def _idx_to_str(idx):
    try:
        return str(idx.to_pydatetime())
    except Exception:
        return str(idx)


def detect_swings(df: pd.DataFrame, lookback: int = SWING_LOOKBACK):
    df = df.copy()
    df['swing_high'] = False
    df['swing_low'] = False
    for i in range(lookback, len(df) - lookback):
        h = df['high'].iloc[i]
        l = df['low'].iloc[i]
        if h == df['high'].iloc[i-lookback:i+lookback+1].max():
            df.iloc[i, df.columns.get_loc('swing_high')] = True
        if l == df['low'].iloc[i-lookback:i+lookback+1].min():
            df.iloc[i, df.columns.get_loc('swing_low')] = True
    return df


def structure_state(df: pd.DataFrame):
    d = detect_swings(df)
    swings_hi = d[d['swing_high']]
    swings_lo = d[d['swing_low']]
    close = float(d['close'].iloc[-1])
    last_hi = float(swings_hi['high'].iloc[-1]) if len(swings_hi) else float(d['high'].tail(30).max())
    last_lo = float(swings_lo['low'].iloc[-1]) if len(swings_lo) else float(d['low'].tail(30).min())
    prev_hi = float(swings_hi['high'].iloc[-2]) if len(swings_hi) > 1 else last_hi
    prev_lo = float(swings_lo['low'].iloc[-2]) if len(swings_lo) > 1 else last_lo
    direction = 'range'
    event = 'inside structure'
    score = 0
    if close > last_hi:
        direction, event, score = 'bullish', 'BOS above last swing high', 3
    elif close < last_lo:
        direction, event, score = 'bearish', 'BOS below last swing low', -3
    elif last_hi > prev_hi and last_lo > prev_lo:
        direction, event, score = 'bullish', 'higher-high / higher-low structure', 2
    elif last_hi < prev_hi and last_lo < prev_lo:
        direction, event, score = 'bearish', 'lower-high / lower-low structure', -2
    return {
        'direction': direction, 'event': event, 'score': score,
        'last_swing_high': round(last_hi, 6), 'last_swing_low': round(last_lo, 6),
        'prev_swing_high': round(prev_hi, 6), 'prev_swing_low': round(prev_lo, 6),
    }


def detect_fvg(df: pd.DataFrame, lookback: int = FVG_LOOKBACK_BARS):
    zones = []
    start = max(2, len(df) - lookback)
    for i in range(start, len(df)):
        c1 = df.iloc[i-2]
        c3 = df.iloc[i]
        idx = df.index[i]
        if c1['high'] < c3['low']:
            zones.append(Zone('FVG', 'bullish', float(c1['high']), float(c3['low']), _idx_to_str(idx), 2))
        if c1['low'] > c3['high']:
            zones.append(Zone('FVG', 'bearish', float(c3['high']), float(c1['low']), _idx_to_str(idx), 2))
    return zones[-8:]


def detect_order_blocks(df: pd.DataFrame, lookback: int = OB_LOOKBACK_BARS):
    zones = []
    recent = df.tail(lookback).copy()
    body = (recent['close'] - recent['open']).abs()
    avg_body = body.rolling(10).mean()
    for i in range(11, len(recent)):
        candle = recent.iloc[i]
        prev = recent.iloc[i-1]
        impulse = abs(candle['close'] - candle['open']) > (avg_body.iloc[i] * 1.4 if not np.isnan(avg_body.iloc[i]) else 0)
        if not impulse:
            continue
        idx = recent.index[i-1]
        if candle['close'] > candle['open'] and prev['close'] < prev['open']:
            zones.append(Zone('Order Block', 'bullish', float(prev['low']), float(prev['high']), _idx_to_str(idx), 3))
        if candle['close'] < candle['open'] and prev['close'] > prev['open']:
            zones.append(Zone('Order Block', 'bearish', float(prev['low']), float(prev['high']), _idx_to_str(idx), 3))
    return zones[-8:]


def liquidity_sweep(df: pd.DataFrame, lookback: int = LIQUIDITY_LOOKBACK_BARS):
    if len(df) < 30:
        return {'type': 'none', 'score': 0, 'note': 'not enough candles'}
    recent = df.tail(lookback)
    last = recent.iloc[-1]
    prior = recent.iloc[:-1]
    prior_high = float(prior['high'].max())
    prior_low = float(prior['low'].min())
    if last['high'] > prior_high and last['close'] < prior_high:
        return {'type': 'buy-side liquidity sweep', 'direction': 'bearish', 'score': -3, 'level': round(prior_high, 6), 'note': 'price took highs and closed back below'}
    if last['low'] < prior_low and last['close'] > prior_low:
        return {'type': 'sell-side liquidity sweep', 'direction': 'bullish', 'score': 3, 'level': round(prior_low, 6), 'note': 'price took lows and closed back above'}
    return {'type': 'none', 'direction': 'neutral', 'score': 0, 'level': None, 'note': 'no clean sweep on latest candle'}


def premium_discount(df: pd.DataFrame, lookback: int = PREMIUM_DISCOUNT_LOOKBACK):
    recent = df.tail(lookback)
    hi = float(recent['high'].max())
    lo = float(recent['low'].min())
    mid = (hi + lo) / 2
    close = float(recent['close'].iloc[-1])
    pos = 'equilibrium'
    if close > mid: pos = 'premium'
    if close < mid: pos = 'discount'
    return {'range_high': round(hi, 6), 'range_low': round(lo, 6), 'equilibrium': round(mid, 6), 'price_location': pos}


def nearest_zone(zones, price, direction=None):
    filtered = [z for z in zones if direction is None or z.direction == direction]
    if not filtered:
        return None
    return min(filtered, key=lambda z: abs(((z.low + z.high) / 2) - price))


def killzone_now():
    now = datetime.now(timezone.utc)
    hour = now.hour + now.minute / 60
    if 7 <= hour < 10:
        return 'London kill zone', 'High volatility forex/index window. Prefer confirmation; avoid chasing.'
    if 12 <= hour < 15:
        return 'New York AM kill zone', 'Strong liquidity window. Breakout/sweep setups often matter more here.'
    if 0 <= hour < 3:
        return 'Asian range', 'Often range-building. Mark highs/lows for later liquidity.'
    return 'Off kill zone', 'Lower timing edge. Wait for cleaner displacement or retest.'


def smc_snapshot(df: pd.DataFrame):
    structure = structure_state(df)
    fvgs = detect_fvg(df)
    obs = detect_order_blocks(df)
    sweep = liquidity_sweep(df)
    pd_state = premium_discount(df)
    return {'structure': structure, 'fvgs': fvgs, 'order_blocks': obs, 'liquidity': sweep, 'premium_discount': pd_state}
