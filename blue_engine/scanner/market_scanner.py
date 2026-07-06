from __future__ import annotations
from utils.symbols import resolve_symbol
try:
    from config import MAJOR_WATCHLIST_SYMBOLS
except Exception:
    MAJOR_WATCHLIST_SYMBOLS = ['xauusd', 'xagusd', 'ethusd', 'btcusd', 'usoil', 'usdjpy', 'eurusd', 'ustec', 'gbpusd']
from analysis.signal_engine import build_signal

DEFAULT_SCAN = list(MAJOR_WATCHLIST_SYMBOLS)

def scan_market(symbols=None, min_confidence=70):
    symbols = symbols or DEFAULT_SCAN
    results=[]
    for s in symbols:
        name, ticker = resolve_symbol(s)
        if not ticker: continue
        try:
            r = build_signal(name, ticker, account=None)
            if r.get('action') != 'WAIT' and r.get('confidence',0) >= min_confidence:
                results.append(r)
        except Exception as e:
            results.append({'symbol': name or s, 'action':'ERROR', 'confidence':0, 'error':str(e)})
    
    def _rank_score(x):
        grades = x.get('trade_quality_grades') or {}
        grade_points = {'A+': 5, 'A': 4, 'B+': 3, 'B': 2, 'C / Avoid': 0}
        ml = x.get('hybrid_ml_confidence_engine') or {}
        vote = x.get('multi_agent_voting') or {}
        return (grade_points.get(grades.get('overall'), 1) * 100) + float(ml.get('final_trade_score', 0) or 0) + x.get('confidence', 0) + int(vote.get('votes_for_trade', 0) or 0) * 5
    results.sort(key=_rank_score, reverse=True)
    return results

def print_scan(results):
    if not results:
        print('No high-confidence setups found.')
        return
    for r in results:
        
        g = r.get('trade_quality_grades') or {}
        p = r.get('probability_engine') or {}
        ml = r.get('hybrid_ml_confidence_engine') or {}
        filt = r.get('a_plus_filter') or {}
        print(f"{r.get('symbol')} {r.get('action')} confidence={r.get('confidence')} grade={g.get('overall','?')} ML={ml.get('final_trade_score','?')} A+={'PASS' if filt.get('allow_autopilot') else 'BLOCK'} TP1prob={p.get('tp1','?')} entry={r.get('entry')} SL={r.get('stop_loss')}")
        if r.get('market_narrative'):
            print('  ' + str(r.get('market_narrative'))[:300])
