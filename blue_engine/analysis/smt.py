from __future__ import annotations
from config import SMT_PAIRS
from analysis.market_data import fetch_ohlcv

def detect_smt(ticker: str, base_df, interval="1h", period="60d"):
    other = SMT_PAIRS.get(ticker)
    if not other:
        return {"pair": None, "bias": "neutral", "score": 0, "note": "No SMT pair configured."}
    try:
        odf = fetch_ohlcv(other, interval, period).tail(80)
        b = base_df.tail(80)
        if len(b) < 20 or len(odf) < 20:
            return {"pair": other, "bias": "neutral", "score": 0, "note": "Not enough SMT data."}
        b_new_high = b['high'].iloc[-1] >= b['high'].iloc[:-1].max()
        b_new_low = b['low'].iloc[-1] <= b['low'].iloc[:-1].min()
        o_new_high = odf['high'].iloc[-1] >= odf['high'].iloc[:-1].max()
        o_new_low = odf['low'].iloc[-1] <= odf['low'].iloc[:-1].min()
        inverse = other == "DX-Y.NYB"
        if not inverse:
            if b_new_high and not o_new_high:
                return {"pair": other, "bias": "bearish", "score": -2, "note": f"SMT bearish: {ticker} swept high but {other} did not confirm."}
            if b_new_low and not o_new_low:
                return {"pair": other, "bias": "bullish", "score": 2, "note": f"SMT bullish: {ticker} swept low but {other} did not confirm."}
        else:
            if b_new_high and not o_new_low:
                return {"pair": other, "bias": "bullish", "score": 1, "note": f"Inverse SMT supportive: {ticker} high without strong DXY confirmation."}
            if b_new_low and not o_new_high:
                return {"pair": other, "bias": "bearish", "score": -1, "note": f"Inverse SMT supportive: {ticker} low without strong DXY confirmation."}
        return {"pair": other, "bias": "neutral", "score": 0, "note": f"No clear SMT divergence vs {other}."}
    except Exception as exc:
        return {"pair": other, "bias": "neutral", "score": 0, "note": f"SMT unavailable: {exc}"}
