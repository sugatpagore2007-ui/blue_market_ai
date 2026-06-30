from __future__ import annotations
from storage.database import journal_stats

def adjust_confidence(symbol: str, action: str, base_confidence: int, tags=None):
    stats = journal_stats(symbol=symbol, action=action)
    trades = stats.get('closed_trades', 0)
    if trades < 10:
        return base_confidence, f"AI learning: only {trades} closed trades, not enough history yet."
    win_rate = stats.get('win_rate', 0)
    profit_factor = stats.get('profit_factor', 0)
    adj = 0
    if win_rate >= 60: adj += 5
    elif win_rate <= 45: adj -= 6
    if profit_factor >= 1.5: adj += 4
    elif 0 < profit_factor < 1.0: adj -= 4
    new_conf = int(max(1, min(95, base_confidence + adj)))
    note = f"AI learning: {trades} closed {symbol} {action} trades, win rate {win_rate}%, PF {profit_factor}. Confidence adjusted {adj:+d}."
    return new_conf, note
