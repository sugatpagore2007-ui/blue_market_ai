from __future__ import annotations

def build_liquidity_heatmap(df, lookback=120, tolerance=0.0015):
    d = df.tail(lookback).copy()
    if d.empty:
        return []
    zones = []
    highs = d['high'].tolist(); lows = d['low'].tolist()
    for i, h in enumerate(highs):
        matches = sum(1 for x in highs if abs(x - h) / max(h, 1e-9) <= tolerance)
        if matches >= 2:
            zones.append({"side": "buy-side", "level": float(h), "strength": matches, "reason": "equal/similar highs"})
    for i, l in enumerate(lows):
        matches = sum(1 for x in lows if abs(x - l) / max(l, 1e-9) <= tolerance)
        if matches >= 2:
            zones.append({"side": "sell-side", "level": float(l), "strength": matches, "reason": "equal/similar lows"})
    zones = sorted(zones, key=lambda z: z["strength"], reverse=True)
    out=[]; seen=[]
    for z in zones:
        if all(abs(z['level']-s)/max(z['level'],1e-9)>tolerance for s in seen):
            seen.append(z['level']); out.append(z)
        if len(out)>=8: break
    return out
