from __future__ import annotations
from analysis.market_data import fetch_ohlcv
from analysis.indicators import add_indicators
from analysis.smc_ict import smc_snapshot

def simple_replay_backtest(ticker: str, interval='1h', period='1y', rr_target=1.5, atr_mult=1.25):
    df = add_indicators(fetch_ohlcv(ticker, interval, period))
    trades=[]
    for i in range(220, len(df)-10):
        window = df.iloc[:i].copy()
        last = window.iloc[-1]
        snap = smc_snapshot(window)
        direction = snap['structure']['direction']
        if direction == 'bullish' and last['close'] > last['ema_20'] > last['ema_50']:
            entry = float(last['close']); sl = min(float(snap['structure']['last_swing_low']), entry - float(last['atr_14'])*atr_mult)
            risk = entry - sl; tp = entry + risk*rr_target; action='BUY'
        elif direction == 'bearish' and last['close'] < last['ema_20'] < last['ema_50']:
            entry = float(last['close']); sl = max(float(snap['structure']['last_swing_high']), entry + float(last['atr_14'])*atr_mult)
            risk = sl - entry; tp = entry - risk*rr_target; action='SELL'
        else:
            continue
        if risk <= 0: continue
        future = df.iloc[i:i+10]
        result='OPEN'; rr=0
        for _, bar in future.iterrows():
            if action == 'BUY':
                if bar['low'] <= sl: result='LOSS'; rr=-1; break
                if bar['high'] >= tp: result='WIN'; rr=rr_target; break
            else:
                if bar['high'] >= sl: result='LOSS'; rr=-1; break
                if bar['low'] <= tp: result='WIN'; rr=rr_target; break
        if result != 'OPEN': trades.append({'action':action,'entry':entry,'sl':sl,'tp':tp,'result':result,'rr':rr})
    wins = sum(1 for t in trades if t['result']=='WIN')
    losses = sum(1 for t in trades if t['result']=='LOSS')
    total = len(trades)
    return {
        'ticker': ticker, 'interval': interval, 'period': period, 'trades': total,
        'wins': wins, 'losses': losses, 'win_rate': round(wins/total*100,2) if total else 0,
        'net_rr': round(sum(t['rr'] for t in trades),2),
        'sample_trades': trades[-10:]
    }
