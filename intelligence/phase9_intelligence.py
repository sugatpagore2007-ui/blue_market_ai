
"""Phase 9 intelligence layer for Blue Market AI.

Adds the 10 intelligence upgrades automatically to every signal:
1) trade memory AI
2) advanced market regime detection
3) economic calendar/news impact AI
4) multi-agent voting
5) chart-vision intelligence hook
6) session intelligence
7) correlation engine
8) advanced hybrid ML confidence engine: Random Forest + XGBoost + LightGBM + CatBoost
9) A+ setup filter
10) portfolio risk manager

The ML layer is safe-by-default. If the optional ML libraries or enough labeled trade
history are not available, it returns a transparent heuristic estimate instead of crashing.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from statistics import mean
from typing import Any, Dict, List, Tuple

try:
    from config import DATABASE_FILE, AUTO_TRADE_PLANS_FILE
except Exception:  # pragma: no cover
    DATABASE_FILE = 'blue_market_ai.db'
    AUTO_TRADE_PLANS_FILE = 'auto_trade_plans.json'

PHASE9_VERSION = '9.0-hybrid-ml-desk'

CORRELATION_GROUPS = {
    'usd_inverse': ['EURUSD', 'GBPUSD', 'XAUUSD', 'XAGUSD'],
    'usd_direct': ['DXY', 'USDJPY'],
    'crypto': ['BTCUSD', 'ETHUSD'],
    'metals': ['XAUUSD', 'XAGUSD'],
    'indices': ['NAS100', 'US500', 'NQ', 'ES'],
    'oil': ['USOIL', 'WTI'],
}

SESSION_RULES = {
    'asia': {'Gold': -3, 'XAU': -3, 'BTC': 1, 'ETH': 1, 'JPY': 2},
    'london': {'EUR': 4, 'GBP': 4, 'Gold': 3, 'XAU': 3, 'DXY': 2},
    'new york': {'Gold': 4, 'XAU': 4, 'NAS': 4, 'US500': 3, 'BTC': 2, 'EUR': 2, 'GBP': 2},
}

GRADE_POINTS = {'A+': 100, 'A': 88, 'B+': 76, 'B': 64, 'C / Avoid': 40, 'C': 40, 'D': 25, '': 50, None: 50}

try:
    from config import (
        PHASE15_10_NEWS_AS_WARNING_ONLY,
        PHASE15_10_MIN_AUTOPILOT_GRADE,
        PHASE15_10_MIN_AUTOPILOT_CONFIDENCE,
    )
except Exception:
    PHASE15_10_NEWS_AS_WARNING_ONLY = False
    PHASE15_10_MIN_AUTOPILOT_GRADE = 'A+'
    PHASE15_10_MIN_AUTOPILOT_CONFIDENCE = 85


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def _symbol_key(signal: Dict[str, Any]) -> str:
    s = str(signal.get('symbol') or signal.get('ticker') or '').upper().replace('/', '')
    # Normalize common names for correlation/memory.
    if 'GOLD' in s or 'XAU' in s:
        return 'XAUUSD'
    if 'SILVER' in s or 'XAG' in s:
        return 'XAGUSD'
    if 'BTC' in s:
        return 'BTCUSD'
    if 'ETH' in s:
        return 'ETHUSD'
    if 'EUR' in s and 'USD' in s:
        return 'EURUSD'
    if 'GBP' in s and 'USD' in s:
        return 'GBPUSD'
    if 'JPY' in s:
        return 'USDJPY'
    if 'OIL' in s or 'WTI' in s:
        return 'USOIL'
    if 'NAS' in s or 'NQ' in s:
        return 'NAS100'
    if 'SPX' in s or 'US500' in s or 'ES' in s:
        return 'US500'
    return s[:12]


def _timeframe_scores(signal: Dict[str, Any]) -> List[float]:
    out = []
    for d in (signal.get('timeframes') or {}).values():
        out.append(_safe_float(d.get('score')))
    return out


def _grade_value(grade: str) -> int:
    order = {'A+': 6, 'A': 5, 'B+': 4, 'B': 3, 'C / AVOID': 1, 'C': 1, 'D': 0}
    return order.get(str(grade or '').upper().strip(), 0)


def _overall_grade(signal: Dict[str, Any]) -> str:
    g = signal.get('trade_quality_grades') or {}
    return str(g.get('overall') or g.get('setup') or signal.get('setup_grade') or '').strip()


def _read_json(path: str, default: Any) -> Any:
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _open_positions_from_plans() -> List[Dict[str, Any]]:
    plans = _read_json(AUTO_TRADE_PLANS_FILE, {})
    if not isinstance(plans, dict):
        return []
    return [p for p in plans.values() if isinstance(p, dict)]


def _db_rows(limit: int = 5000) -> List[Dict[str, Any]]:
    """Read whatever usable history exists from SQLite without assuming schema."""
    if not os.path.exists(DATABASE_FILE):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        con = sqlite3.connect(DATABASE_FILE)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        table_names = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for t in table_names:
            try:
                cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})").fetchall()]
                useful = {'symbol','ticker','action','confidence','result','profit','profit_r','pnl','session','created_at','grade','setup_grade'}
                if not any(c in useful for c in cols):
                    continue
                q = f"SELECT * FROM {t} LIMIT {int(limit)}"
                for r in cur.execute(q).fetchall():
                    rows.append(dict(r))
            except Exception:
                continue
        con.close()
    except Exception:
        return []
    return rows[-limit:]


def _infer_result(row: Dict[str, Any]) -> int | None:
    # Return 1 win, 0 loss, None unknown.
    for k in ['result', 'outcome', 'status']:
        v = str(row.get(k, '')).lower()
        if any(x in v for x in ['win', 'tp', 'profit']):
            return 1
        if any(x in v for x in ['loss', 'sl', 'lose']):
            return 0
    for k in ['profit_r', 'profit', 'pnl', 'pnl_r']:
        if k in row:
            val = _safe_float(row.get(k), None)
            if val is None:
                continue
            if val > 0:
                return 1
            if val < 0:
                return 0
    return None


def trade_memory_ai(signal: Dict[str, Any]) -> Dict[str, Any]:
    sym = _symbol_key(signal)
    rows = _db_rows(2000)
    labeled = []
    symbol_labeled = []
    for r in rows:
        y = _infer_result(r)
        if y is None:
            continue
        labeled.append(y)
        rsym = _symbol_key({'symbol': r.get('symbol') or r.get('ticker')})
        if rsym == sym:
            symbol_labeled.append(y)
    plans = _open_positions_from_plans()
    current_same = [p for p in plans if _symbol_key(p) == sym]
    if labeled:
        global_wr = round(100 * sum(labeled) / len(labeled), 1)
    else:
        global_wr = None
    if symbol_labeled:
        sym_wr = round(100 * sum(symbol_labeled) / len(symbol_labeled), 1)
    else:
        sym_wr = None

    score_adj = 0
    if sym_wr is not None:
        if sym_wr >= 65: score_adj += 6
        elif sym_wr >= 58: score_adj += 3
        elif sym_wr < 45: score_adj -= 8
    elif global_wr is not None:
        if global_wr >= 60: score_adj += 2
        elif global_wr < 45: score_adj -= 3

    note = 'Not enough closed trade history yet. Memory AI stays neutral.'
    if sym_wr is not None:
        note = f'{sym} historical win rate in Blue journal is about {sym_wr}% from {len(symbol_labeled)} labeled trades.'
    elif global_wr is not None:
        note = f'Global Blue journal win rate is about {global_wr}% from {len(labeled)} labeled trades; symbol-specific sample is not ready.'

    return {
        'symbol_key': sym,
        'global_labeled_trades': len(labeled),
        'symbol_labeled_trades': len(symbol_labeled),
        'global_win_rate': global_wr,
        'symbol_win_rate': sym_wr,
        'open_same_symbol_plans': len(current_same),
        'confidence_adjustment': score_adj,
        'note': note,
    }


def advanced_regime_ai(signal: Dict[str, Any]) -> Dict[str, Any]:
    scores = _timeframe_scores(signal)
    action = str(signal.get('action', 'WAIT')).upper()
    if not scores:
        return {'regime': 'unknown', 'score': 0, 'trade_permission': 'WAIT', 'note': 'No timeframe scores available.'}
    pos = sum(1 for s in scores if s > 0)
    neg = sum(1 for s in scores if s < 0)
    abs_avg = mean(abs(s) for s in scores)
    spread = max(scores) - min(scores)
    regime_text = str(signal.get('regime', '')).lower()
    if pos >= 4 and action == 'BUY' and abs_avg >= 2:
        regime = 'bullish trend expansion'
        permission = 'ALLOW'
    elif neg >= 4 and action == 'SELL' and abs_avg >= 2:
        regime = 'bearish trend expansion'
        permission = 'ALLOW'
    elif spread >= 7:
        regime = 'conflicting/mixed regime'
        permission = 'REDUCE_OR_WAIT'
    elif 'premium' in regime_text or 'discount' in regime_text:
        regime = 'dealing range / liquidity rotation'
        permission = 'ALLOW_ONLY_A_PLUS'
    else:
        regime = 'balanced intraday regime'
        permission = 'ALLOW_ONLY_A'
    return {
        'regime': regime,
        'positive_tfs': pos,
        'negative_tfs': neg,
        'avg_abs_score': round(abs_avg, 2),
        'score_spread': round(spread, 2),
        'trade_permission': permission,
        'note': f'Market regime is {regime}. Permission: {permission}.',
    }


def economic_calendar_ai(signal: Dict[str, Any]) -> Dict[str, Any]:
    news = str(signal.get('news_caution') or signal.get('research_agent_summary') or '').lower()
    symbol = _symbol_key(signal)
    risk = 'normal'
    block = False
    note = 'No high-impact event detected by the current news layer. Still verify live calendar manually.'
    if any(w in news for w in ['high-impact', 'high impact', 'nfp', 'cpi', 'fomc', 'interest rate', 'fed']):
        risk = 'high'
        block = True
        note = 'High-impact macro risk detected. Blue should avoid new auto entries until the event window clears.'
    elif symbol in ['XAUUSD','EURUSD','GBPUSD','USDJPY','NAS100','US500']:
        note = 'USD-sensitive symbol. Blue should check CPI, NFP, FOMC, Fed speeches and rate decisions before entry.'
    return {'risk': risk, 'block_new_trade': block, 'note': note}


def session_intelligence(signal: Dict[str, Any]) -> Dict[str, Any]:
    session = str(signal.get('session') or '').lower()
    sym = _symbol_key(signal)
    score = 0
    reasons = []
    for key, mp in SESSION_RULES.items():
        if key in session:
            for needle, pts in mp.items():
                if needle.upper() in sym.upper() or needle.lower() in str(signal.get('symbol','')).lower():
                    score += pts
                    reasons.append(f'{needle} tends to react well in {key} session')
    if not reasons:
        reasons.append('No special session edge detected; keep normal filters.')
    permission = 'BOOST' if score >= 3 else ('NEUTRAL' if score >= 0 else 'REDUCE')
    return {'session': signal.get('session'), 'score': score, 'permission': permission, 'reasons': reasons}


def correlation_engine(signal: Dict[str, Any]) -> Dict[str, Any]:
    sym = _symbol_key(signal)
    action = str(signal.get('action', 'WAIT')).upper()
    groups = [g for g, members in CORRELATION_GROUPS.items() if any(m in sym for m in members)]
    plans = _open_positions_from_plans()
    exposure = []
    same_direction = 0
    opposite = 0
    for p in plans:
        psym = _symbol_key(p)
        paction = str(p.get('action','')).upper()
        pgroups = [g for g, members in CORRELATION_GROUPS.items() if any(m in psym for m in members)]
        if set(groups) & set(pgroups):
            exposure.append({'ticket': p.get('ticket'), 'symbol': p.get('symbol'), 'action': paction, 'group': list(set(groups)&set(pgroups))})
            if paction == action: same_direction += 1
            elif paction in ['BUY','SELL'] and action in ['BUY','SELL']: opposite += 1
    risk = 'normal'
    if same_direction >= 2:
        risk = 'high_same_direction_exposure'
    elif same_direction == 1:
        risk = 'moderate_correlated_exposure'
    return {
        'symbol_key': sym,
        'groups': groups,
        'correlated_open_positions': exposure,
        'same_direction_count': same_direction,
        'opposite_count': opposite,
        'risk': risk,
        'note': 'Avoid stacking correlated trades in the same direction.' if same_direction else 'No major correlated exposure detected from Blue plan file.',
    }


def portfolio_manager_ai(signal: Dict[str, Any]) -> Dict[str, Any]:
    corr = correlation_engine(signal)
    plans = _open_positions_from_plans()
    action = str(signal.get('action','WAIT')).upper()
    block = False
    reasons = []
    if action == 'WAIT':
        return {'block_new_trade': True, 'risk_level': 'none', 'note': 'No trade signal.'}
    if len(plans) >= 5:
        block = True; reasons.append('Too many Blue-managed open plans already exist.')
    if corr['risk'] == 'high_same_direction_exposure':
        block = True; reasons.append('Too much same-direction correlated exposure.')
    elif corr['risk'] == 'moderate_correlated_exposure':
        reasons.append('One correlated same-direction position already exists; reduce size or skip if not A+.')
    if not reasons:
        reasons.append('Portfolio exposure looks acceptable.')
    risk_level = 'high' if block else ('medium' if 'reduce' in ' '.join(reasons).lower() or corr['same_direction_count'] else 'normal')
    return {'block_new_trade': block, 'risk_level': risk_level, 'open_blue_plans': len(plans), 'reasons': reasons, 'note': ' '.join(reasons)}


def chart_vision_ai(signal: Dict[str, Any]) -> Dict[str, Any]:
    # Hook for screenshot/live screen modules. It stays neutral unless a vision module attaches data.
    vision = signal.get('chart_vision') or signal.get('vision') or {}
    if not vision:
        return {'status': 'not_attached', 'score': 0, 'note': 'Chart vision not attached to this signal. Use screenshot/detect chart commands for visual confirmation.'}
    score = _safe_float(vision.get('score'), 0)
    return {'status': 'attached', 'score': score, 'note': str(vision.get('note', 'Vision evidence attached.'))}


def _feature_vector(signal: Dict[str, Any]) -> Tuple[List[float], List[str]]:
    scores = _timeframe_scores(signal)
    action = str(signal.get('action','WAIT')).upper()
    grades = signal.get('trade_quality_grades') or {}
    heat = signal.get('liquidity_heatmap') or []
    prob = signal.get('probability_engine') or {}
    regime = advanced_regime_ai(signal)
    sess = session_intelligence(signal)
    corr = correlation_engine(signal)
    features = {
        'rule_confidence': _safe_float(signal.get('confidence')),
        'tf_avg': mean(scores) if scores else 0,
        'tf_abs_avg': mean(abs(s) for s in scores) if scores else 0,
        'tf_alignment': sum(1 for s in scores if (s > 0 and action == 'BUY') or (s < 0 and action == 'SELL')),
        'grade_points': GRADE_POINTS.get(grades.get('overall'), 50),
        'tp1_prob_rule': _safe_float(prob.get('tp1') or prob.get('tp1_probability') or prob.get('probability_tp1')),
        'heatmap_count': len(heat),
        'regime_abs_score': _safe_float(regime.get('avg_abs_score')),
        'regime_spread': _safe_float(regime.get('score_spread')),
        'session_score': _safe_float(sess.get('score')),
        'correlated_same_direction': _safe_float(corr.get('same_direction_count')),
    }
    names = list(features.keys())
    return [features[n] for n in names], names


def _heuristic_probability(signal: Dict[str, Any]) -> float:
    x, names = _feature_vector(signal)
    fd = dict(zip(names, x))
    score = 45.0
    score += (fd['rule_confidence'] - 50) * 0.38
    score += fd['tf_alignment'] * 2.5
    score += min(fd['heatmap_count'], 5) * 1.2
    score += fd['session_score'] * 0.8
    score += (fd['grade_points'] - 70) * 0.12
    score -= max(0, fd['correlated_same_direction'] - 0) * 4.0
    score -= max(0, fd['regime_spread'] - 6) * 1.2
    return round(max(5, min(92, score)), 1)


def _load_training_data_from_db() -> Tuple[List[List[float]], List[int]]:
    """Build a small supervised dataset if journal/result columns exist.

    The current Blue DB may not yet have enough labeled outcomes. This function is intentionally
    tolerant. It never raises into the trading engine.
    """
    rows = _db_rows(5000)
    X, y = [], []
    for r in rows:
        label = _infer_result(r)
        if label is None:
            continue
        # Minimal training features available from historical rows.
        confidence = _safe_float(r.get('confidence'), 50)
        symbol = _symbol_key({'symbol': r.get('symbol') or r.get('ticker')})
        action = str(r.get('action','')).upper()
        is_gold = 1 if symbol == 'XAUUSD' else 0
        is_crypto = 1 if symbol in ['BTCUSD','ETHUSD'] else 0
        is_forex = 1 if symbol in ['EURUSD','GBPUSD','USDJPY'] else 0
        is_buy = 1 if action == 'BUY' else 0
        X.append([confidence, is_gold, is_crypto, is_forex, is_buy])
        y.append(int(label))
    return X, y


def _try_model_predictions(current_basic_features: List[float]) -> Dict[str, Any]:
    """Advanced hybrid model: RF + XGBoost + LightGBM + CatBoost.

    If libraries or enough labeled samples are unavailable, returns available=False.
    """
    X, y = _load_training_data_from_db()
    if len(y) < 40 or len(set(y)) < 2:
        return {'available': False, 'reason': f'Need at least 40 labeled win/loss trades with both wins and losses. Found {len(y)}.'}
    # Match feature shape for historical model. We cannot train advanced signal features unless old rows store them.
    # Current input is adapted to the 5-feature historical set.
    hist_input = [current_basic_features[0], 1 if current_basic_features[0] else 0, 0, 0, 1]
    preds = {}
    errors = {}
    try:
        from sklearn.ensemble import RandomForestClassifier
        rf = RandomForestClassifier(n_estimators=150, max_depth=5, random_state=42, class_weight='balanced')
        rf.fit(X, y)
        preds['random_forest'] = float(rf.predict_proba([hist_input])[0][1]) * 100
    except Exception as e:
        errors['random_forest'] = str(e)[:120]
    try:
        from xgboost import XGBClassifier
        xgb = XGBClassifier(n_estimators=120, max_depth=3, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, eval_metric='logloss', random_state=42)
        xgb.fit(X, y)
        preds['xgboost'] = float(xgb.predict_proba([hist_input])[0][1]) * 100
    except Exception as e:
        errors['xgboost'] = str(e)[:120]
    try:
        from lightgbm import LGBMClassifier
        lgbm = LGBMClassifier(n_estimators=160, max_depth=4, learning_rate=0.04, random_state=42, verbose=-1)
        lgbm.fit(X, y)
        preds['lightgbm'] = float(lgbm.predict_proba([hist_input])[0][1]) * 100
    except Exception as e:
        errors['lightgbm'] = str(e)[:120]
    try:
        from catboost import CatBoostClassifier
        cb = CatBoostClassifier(iterations=140, depth=4, learning_rate=0.05, verbose=False, random_seed=42)
        cb.fit(X, y)
        preds['catboost'] = float(cb.predict_proba([hist_input])[0][1]) * 100
    except Exception as e:
        errors['catboost'] = str(e)[:120]
    if not preds:
        return {'available': False, 'reason': 'No optional ML model library is installed or training failed.', 'errors': errors}
    # Weighted ensemble: XGBoost and LightGBM get slightly higher weight for tabular trading data.
    weights = {'random_forest': 1.0, 'xgboost': 1.35, 'lightgbm': 1.25, 'catboost': 1.15}
    total_w = sum(weights[k] for k in preds)
    ensemble = sum(preds[k] * weights[k] for k in preds) / total_w
    return {'available': True, 'predictions': {k: round(v, 1) for k, v in preds.items()}, 'ensemble_probability': round(ensemble, 1), 'training_samples': len(y), 'errors': errors}


def hybrid_ml_confidence_engine(signal: Dict[str, Any]) -> Dict[str, Any]:
    heuristic = _heuristic_probability(signal)
    x, names = _feature_vector(signal)
    models = _try_model_predictions(x)
    if models.get('available'):
        ml_prob = _safe_float(models.get('ensemble_probability'), heuristic)
        mode = 'trained_hybrid_ensemble'
        note = 'Hybrid ML trained from your journal: Random Forest + XGBoost + LightGBM + CatBoost ensemble.'
    else:
        ml_prob = heuristic
        mode = 'heuristic_until_enough_labeled_data'
        note = 'Hybrid ML fallback active: collect more closed win/loss trades to train RF/XGBoost/LightGBM/CatBoost.'
    rule_conf = _safe_float(signal.get('confidence'))
    # Blend rule confidence with ML probability. ML gets stronger after training is available.
    final = round((rule_conf * 0.45 + ml_prob * 0.55), 1) if models.get('available') else round((rule_conf * 0.65 + ml_prob * 0.35), 1)
    return {
        'mode': mode,
        'rule_confidence': rule_conf,
        'ml_probability': ml_prob,
        'final_trade_score': final,
        'feature_names': names,
        'feature_values': [round(_safe_float(v), 4) for v in x],
        'model_stack': ['RandomForest', 'XGBoost', 'LightGBM', 'CatBoost'],
        'trained_models': models.get('predictions', {}),
        'training_samples': models.get('training_samples', 0),
        'model_errors': models.get('errors', {}),
        'note': note + (' ' + str(models.get('reason','')) if not models.get('available') else ''),
    }


def multi_agent_voting(signal: Dict[str, Any]) -> Dict[str, Any]:
    action = str(signal.get('action','WAIT')).upper()
    if action == 'WAIT':
        return {'votes_for_trade': 0, 'votes_total': 6, 'decision': 'WAIT', 'agents': {'desk': 'No trade because base engine is WAIT.'}}
    ml = hybrid_ml_confidence_engine(signal)
    regime = advanced_regime_ai(signal)
    cal = economic_calendar_ai(signal)
    sess = session_intelligence(signal)
    port = portfolio_manager_ai(signal)
    grades = signal.get('trade_quality_grades') or {}
    agents = {}
    votes = 0
    agents['market_analyst'] = 'YES' if _safe_float(signal.get('confidence')) >= 80 else 'NO'
    agents['liquidity_smc'] = 'YES' if GRADE_POINTS.get(grades.get('liquidity'), 50) >= 76 else 'NO'
    agents['risk_manager'] = 'YES' if not port.get('block_new_trade') else 'NO'
    agents['news_agent'] = 'YES' if not cal.get('block_new_trade') else 'NO'
    agents['session_agent'] = 'YES' if sess.get('permission') in ['BOOST','NEUTRAL'] else 'NO'
    agents['ml_agent'] = 'YES' if _safe_float(ml.get('final_trade_score')) >= 72 else 'NO'
    votes = sum(1 for v in agents.values() if v == 'YES')
    decision = 'APPROVED' if votes >= 5 else ('CONDITIONAL' if votes >= 4 else 'REJECT')
    return {'votes_for_trade': votes, 'votes_total': len(agents), 'decision': decision, 'agents': agents, 'note': f'{votes}/{len(agents)} agents approve. Decision: {decision}.'}


def a_plus_filter(signal: Dict[str, Any]) -> Dict[str, Any]:
    action = str(signal.get('action','WAIT')).upper()
    if action not in ['BUY','SELL']:
        return {'allow_autopilot': False, 'grade': 'WAIT', 'reason': 'Base signal is WAIT.'}
    grade = _overall_grade(signal)
    ml = hybrid_ml_confidence_engine(signal)
    vote = multi_agent_voting(signal)
    port = portfolio_manager_ai(signal)
    cal = economic_calendar_ai(signal)
    reasons = []
    allow = True
    min_grade = str(PHASE15_10_MIN_AUTOPILOT_GRADE or 'A+').upper().strip()
    min_conf = float(PHASE15_10_MIN_AUTOPILOT_CONFIDENCE or 85)
    if _grade_value(grade) < _grade_value(min_grade):
        allow = False; reasons.append(f'grade {grade or "N/A"} is below {min_grade}')
    if _safe_float(signal.get('confidence')) < min_conf:
        allow = False; reasons.append(f'rule confidence below {int(min_conf)}')
    if _safe_float(ml.get('final_trade_score')) < 75:
        allow = False; reasons.append('hybrid ML final score below 75')
    if vote.get('decision') == 'REJECT':
        allow = False; reasons.append('multi-agent vote rejected')
    if port.get('block_new_trade'):
        allow = False; reasons.append('portfolio manager blocked exposure')
    if cal.get('block_new_trade'):
        allow = False; reasons.append('economic calendar risk block')
    if not reasons:
        reasons.append('A+ filter passed: grade, confidence, ML, portfolio and news filters agree.')
    return {'allow_autopilot': allow, 'grade': grade, 'min_grade': 'A+', 'reasons': reasons, 'reason': '; '.join(reasons)}


def apply_phase9_intelligence(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Attach all Phase 9 upgrades and adjust final confidence in a transparent way."""
    memory = trade_memory_ai(signal)
    signal['trade_memory_ai'] = memory
    signal['advanced_market_regime_ai'] = advanced_regime_ai(signal)
    signal['economic_calendar_ai'] = economic_calendar_ai(signal)
    signal['session_intelligence'] = session_intelligence(signal)
    signal['correlation_engine'] = correlation_engine(signal)
    signal['chart_vision_ai'] = chart_vision_ai(signal)
    signal['portfolio_manager_ai'] = portfolio_manager_ai(signal)
    signal['hybrid_ml_confidence_engine'] = hybrid_ml_confidence_engine(signal)
    signal['multi_agent_voting'] = multi_agent_voting(signal)
    signal['a_plus_filter'] = a_plus_filter(signal)

    # Conservative final score: never inflate above 95, and do not change WAIT into trade.
    if str(signal.get('action','WAIT')).upper() in ['BUY','SELL']:
        old = _safe_float(signal.get('confidence'))
        ml_final = _safe_float(signal['hybrid_ml_confidence_engine'].get('final_trade_score'), old)
        mem_adj = _safe_float(memory.get('confidence_adjustment'))
        adjusted = max(0, min(95, round((old * 0.55 + ml_final * 0.45) + mem_adj, 1)))
        signal['phase9_original_confidence'] = old
        signal['phase9_final_confidence'] = adjusted
        signal['confidence'] = int(round(adjusted))

    phase9_summary = (
        f"Phase 9 intelligence: ML score {signal['hybrid_ml_confidence_engine']['final_trade_score']}%, "
        f"agent vote {signal['multi_agent_voting']['votes_for_trade']}/{signal['multi_agent_voting']['votes_total']}, "
        f"A+ filter: {'PASS' if signal['a_plus_filter']['allow_autopilot'] else 'BLOCK'} — {signal['a_plus_filter']['reason']}"
    )
    signal['phase9_summary'] = phase9_summary
    signal['phase9_upgrades'] = [
        'Trade Memory AI', 'Advanced Market Regime Detection', 'Economic Calendar AI',
        'Multi-Agent Voting', 'AI Chart Vision Hook', 'Session Intelligence',
        'Correlation Engine', 'Advanced Hybrid ML Confidence Engine: RF + XGBoost + LightGBM + CatBoost',
        'A+ Setup Filter', 'Portfolio Manager AI'
    ]
    base = signal.get('analyst_reason') or signal.get('human_read') or ''
    if phase9_summary not in base:
        signal['analyst_reason'] = (base + '\n\n' + phase9_summary).strip()
        signal['human_read'] = signal['analyst_reason']
    return signal


def phase9_status_text() -> str:
    rows = _db_rows(5000)
    labeled = sum(1 for r in rows if _infer_result(r) is not None)
    return (
        'Phase 9 Intelligence Status\n'
        f'Version                 : {PHASE9_VERSION}\n'
        f'Database file           : {DATABASE_FILE}\n'
        f'Rows scanned            : {len(rows)}\n'
        f'Labeled win/loss rows    : {labeled}\n'
        'Hybrid ML stack         : Random Forest + XGBoost + LightGBM + CatBoost\n'
        'Training rule           : real model activates after 40+ labeled trades with both wins and losses\n'
        'Active upgrades         : memory, regime, calendar, voting, vision hook, session, correlation, hybrid ML, A+ filter, portfolio AI\n'
    )

# -----------------------------------------------------------------------------
# Phase 9.1 -> 9.5 automatic ML learning upgrade
# 9.1 Trade Data Collector
# 9.2 Hybrid ML Engine: RandomForest + XGBoost + LightGBM + CatBoost
# 9.3 Automatic retraining when enough new labeled trades exist
# 9.4 ML trade rejection filter
# 9.5 Adaptive confidence from real outcomes
# -----------------------------------------------------------------------------

PHASE9_AUTO_LEARNING_VERSION = '9.5-auto-learning-hybrid-ensemble'
PHASE9_MODEL_FILE = 'phase9_hybrid_ml_model.joblib'
PHASE9_MODEL_META_FILE = 'phase9_hybrid_ml_meta.json'
PHASE9_MIN_TRAIN_TRADES = 40
PHASE9_RETRAIN_EVERY_NEW_LABELS = 10
PHASE9_FIXED_FEATURES = [
    'rule_confidence', 'is_buy', 'is_sell', 'is_wait',
    'is_gold', 'is_crypto', 'is_forex', 'is_index', 'is_oil',
    'tf_avg', 'tf_abs_avg', 'tf_alignment', 'grade_points',
    'heatmap_count', 'session_score', 'correlated_same_direction',
    'regime_abs_score', 'regime_spread',
]


def _load_json_file(path: str, default: Any) -> Any:
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _save_json_file(path: str, data: Any) -> None:
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass


def _result_label_from_text(text: Any) -> int | None:
    v = str(text or '').strip().lower()
    if not v or v == 'open':
        return None
    if any(x in v for x in ['win', 'tp', 'profit', 'won']):
        return 1
    if any(x in v for x in ['loss', 'sl', 'lose', 'lost']):
        return 0
    return None


def _parse_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    payload = row.get('payload')
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str) and payload.strip().startswith('{'):
        try:
            return json.loads(payload)
        except Exception:
            return {}
    return {}


def _feature_dict_from_signal(signal: Dict[str, Any]) -> Dict[str, float]:
    sym = _symbol_key(signal)
    action = str(signal.get('action', 'WAIT')).upper()
    scores = _timeframe_scores(signal)
    grades = signal.get('trade_quality_grades') or {}
    heat = signal.get('liquidity_heatmap') or []
    try:
        regime = advanced_regime_ai(signal)
    except Exception:
        regime = {}
    try:
        sess = session_intelligence(signal)
    except Exception:
        sess = {}
    try:
        corr = correlation_engine(signal)
    except Exception:
        corr = {}
    tf_alignment = 0
    for s in scores:
        if action == 'BUY' and s > 0:
            tf_alignment += 1
        elif action == 'SELL' and s < 0:
            tf_alignment += 1
    fd = {
        'rule_confidence': _safe_float(signal.get('confidence'), 50),
        'is_buy': 1.0 if action == 'BUY' else 0.0,
        'is_sell': 1.0 if action == 'SELL' else 0.0,
        'is_wait': 1.0 if action == 'WAIT' else 0.0,
        'is_gold': 1.0 if sym in ['XAUUSD', 'XAGUSD'] else 0.0,
        'is_crypto': 1.0 if sym in ['BTCUSD', 'ETHUSD'] else 0.0,
        'is_forex': 1.0 if sym in ['EURUSD', 'GBPUSD', 'USDJPY'] else 0.0,
        'is_index': 1.0 if sym in ['NAS100', 'US500'] else 0.0,
        'is_oil': 1.0 if sym in ['USOIL'] else 0.0,
        'tf_avg': mean(scores) if scores else 0.0,
        'tf_abs_avg': mean(abs(s) for s in scores) if scores else 0.0,
        'tf_alignment': float(tf_alignment),
        'grade_points': float(GRADE_POINTS.get(grades.get('overall') or grades.get('setup'), 50)),
        'heatmap_count': float(len(heat)),
        'session_score': _safe_float(sess.get('score'), 0),
        'correlated_same_direction': _safe_float(corr.get('same_direction_count'), 0),
        'regime_abs_score': _safe_float(regime.get('avg_abs_score'), 0),
        'regime_spread': _safe_float(regime.get('score_spread'), 0),
    }
    return fd


def _features_from_signal_v2(signal: Dict[str, Any]) -> List[float]:
    fd = _feature_dict_from_signal(signal)
    return [round(_safe_float(fd.get(k), 0), 6) for k in PHASE9_FIXED_FEATURES]


def _features_from_row_v2(row: Dict[str, Any]) -> List[float]:
    payload = _parse_payload(row)
    if payload:
        # Fill missing row-level result fields while preserving rich signal payload.
        payload.setdefault('symbol', row.get('symbol') or row.get('ticker'))
        payload.setdefault('ticker', row.get('ticker'))
        payload.setdefault('action', row.get('action'))
        payload.setdefault('confidence', row.get('confidence'))
        return _features_from_signal_v2(payload)
    # Fallback for older journal rows that do not contain full signal payload.
    sym = _symbol_key({'symbol': row.get('symbol') or row.get('ticker')})
    action = str(row.get('action', 'WAIT')).upper()
    fd = {
        'rule_confidence': _safe_float(row.get('confidence'), 50),
        'is_buy': 1.0 if action == 'BUY' else 0.0,
        'is_sell': 1.0 if action == 'SELL' else 0.0,
        'is_wait': 1.0 if action == 'WAIT' else 0.0,
        'is_gold': 1.0 if sym in ['XAUUSD', 'XAGUSD'] else 0.0,
        'is_crypto': 1.0 if sym in ['BTCUSD', 'ETHUSD'] else 0.0,
        'is_forex': 1.0 if sym in ['EURUSD', 'GBPUSD', 'USDJPY'] else 0.0,
        'is_index': 1.0 if sym in ['NAS100', 'US500'] else 0.0,
        'is_oil': 1.0 if sym in ['USOIL'] else 0.0,
        'tf_avg': 0.0,
        'tf_abs_avg': 0.0,
        'tf_alignment': 0.0,
        'grade_points': _safe_float(row.get('grade') or row.get('setup_grade'), 50),
        'heatmap_count': 0.0,
        'session_score': 0.0,
        'correlated_same_direction': 0.0,
        'regime_abs_score': 0.0,
        'regime_spread': 0.0,
    }
    return [round(_safe_float(fd.get(k), 0), 6) for k in PHASE9_FIXED_FEATURES]


def collect_labeled_trade_dataset(limit: int = 10000) -> Dict[str, Any]:
    """Phase 9.1: collect real closed trade outcomes from Blue DB.

    Works with both old journal rows and newer rich signal payload rows. The label is:
    1 = win/profit/TP, 0 = loss/SL.
    """
    rows = _db_rows(limit)
    X: List[List[float]] = []
    y: List[int] = []
    raw: List[Dict[str, Any]] = []
    for r in rows:
        label = _infer_result(r)
        if label is None:
            label = _result_label_from_text(r.get('result') or r.get('outcome') or r.get('status'))
        if label is None:
            continue
        try:
            X.append(_features_from_row_v2(r))
            y.append(int(label))
            raw.append(r)
        except Exception:
            continue
    wins = sum(y)
    losses = len(y) - wins
    return {
        'X': X,
        'y': y,
        'rows': raw,
        'labeled_trades': len(y),
        'wins': wins,
        'losses': losses,
        'feature_names': PHASE9_FIXED_FEATURES,
        'ready': len(y) >= PHASE9_MIN_TRAIN_TRADES and wins > 0 and losses > 0,
    }


def train_hybrid_ensemble(force: bool = True) -> Dict[str, Any]:
    """Phase 9.2/9.3: train and save the hybrid ML ensemble from real outcomes."""
    ds = collect_labeled_trade_dataset()
    if not ds['ready']:
        return {
            'ok': False,
            'message': f"Need {PHASE9_MIN_TRAIN_TRADES}+ labeled trades with both wins and losses. Found {ds['labeled_trades']} ({ds['wins']} wins, {ds['losses']} losses).",
            'dataset': {k: ds[k] for k in ['labeled_trades','wins','losses','ready']},
        }
    X, y = ds['X'], ds['y']
    models: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    try:
        from sklearn.ensemble import RandomForestClassifier
        models['random_forest'] = RandomForestClassifier(n_estimators=250, max_depth=7, min_samples_leaf=2, random_state=42, class_weight='balanced')
        models['random_forest'].fit(X, y)
    except Exception as e:
        errors['random_forest'] = str(e)[:240]
    try:
        from xgboost import XGBClassifier
        models['xgboost'] = XGBClassifier(n_estimators=220, max_depth=4, learning_rate=0.045, subsample=0.9, colsample_bytree=0.9, eval_metric='logloss', random_state=42)
        models['xgboost'].fit(X, y)
    except Exception as e:
        errors['xgboost'] = str(e)[:240]
    try:
        from lightgbm import LGBMClassifier
        models['lightgbm'] = LGBMClassifier(n_estimators=260, max_depth=5, learning_rate=0.035, random_state=42, verbose=-1)
        models['lightgbm'].fit(X, y)
    except Exception as e:
        errors['lightgbm'] = str(e)[:240]
    try:
        from catboost import CatBoostClassifier
        models['catboost'] = CatBoostClassifier(iterations=220, depth=5, learning_rate=0.04, verbose=False, random_seed=42)
        models['catboost'].fit(X, y)
    except Exception as e:
        errors['catboost'] = str(e)[:240]
    if not models:
        return {'ok': False, 'message': 'No ML library trained successfully.', 'errors': errors}
    try:
        import joblib
        bundle = {
            'version': PHASE9_AUTO_LEARNING_VERSION,
            'trained_at': datetime.utcnow().isoformat(),
            'feature_names': PHASE9_FIXED_FEATURES,
            'models': models,
            'weights': {'random_forest': 1.0, 'xgboost': 1.35, 'lightgbm': 1.25, 'catboost': 1.15},
            'labeled_trades': ds['labeled_trades'],
            'wins': ds['wins'],
            'losses': ds['losses'],
        }
        joblib.dump(bundle, PHASE9_MODEL_FILE)
        _save_json_file(PHASE9_MODEL_META_FILE, {k: v for k, v in bundle.items() if k != 'models'})
    except Exception as e:
        return {'ok': False, 'message': 'Training worked but saving model failed.', 'errors': {**errors, 'save': str(e)[:240]}}
    return {
        'ok': True,
        'message': f"Hybrid ML trained: {', '.join(models.keys())} from {ds['labeled_trades']} labeled trades.",
        'trained_models': list(models.keys()),
        'errors': errors,
        'model_file': PHASE9_MODEL_FILE,
        'dataset': {k: ds[k] for k in ['labeled_trades','wins','losses','ready']},
    }


def _load_saved_hybrid_bundle() -> Dict[str, Any] | None:
    try:
        if not os.path.exists(PHASE9_MODEL_FILE):
            return None
        import joblib
        return joblib.load(PHASE9_MODEL_FILE)
    except Exception:
        return None


def maybe_auto_retrain() -> Dict[str, Any]:
    """Phase 9.3: retrain automatically when new labeled outcomes are available."""
    ds = collect_labeled_trade_dataset()
    meta = _load_json_file(PHASE9_MODEL_META_FILE, {})
    last_n = int(meta.get('labeled_trades', 0) or 0)
    if not ds['ready']:
        return {'trained': False, 'reason': f"Dataset not ready: {ds['labeled_trades']} labeled trades."}
    if not os.path.exists(PHASE9_MODEL_FILE) or ds['labeled_trades'] >= last_n + PHASE9_RETRAIN_EVERY_NEW_LABELS:
        res = train_hybrid_ensemble(force=True)
        return {'trained': bool(res.get('ok')), 'reason': res.get('message'), 'result': res}
    return {'trained': False, 'reason': f"Saved model is current. Labeled trades {ds['labeled_trades']}, last train {last_n}."}


def _saved_model_predictions(signal: Dict[str, Any]) -> Dict[str, Any]:
    maybe_auto_retrain()
    bundle = _load_saved_hybrid_bundle()
    if not bundle:
        return {'available': False, 'reason': 'No saved trained ensemble yet.'}
    models = bundle.get('models') or {}
    weights = bundle.get('weights') or {}
    X = [_features_from_signal_v2(signal)]
    preds: Dict[str, float] = {}
    errors: Dict[str, str] = {}
    for name, model in models.items():
        try:
            p = float(model.predict_proba(X)[0][1]) * 100.0
            preds[name] = round(max(0, min(100, p)), 1)
        except Exception as e:
            errors[name] = str(e)[:180]
    if not preds:
        return {'available': False, 'reason': 'Saved models exist but prediction failed.', 'errors': errors}
    total_w = sum(float(weights.get(k, 1.0)) for k in preds)
    ensemble = sum(preds[k] * float(weights.get(k, 1.0)) for k in preds) / (total_w or len(preds))
    return {
        'available': True,
        'predictions': preds,
        'ensemble_probability': round(ensemble, 1),
        'training_samples': int(bundle.get('labeled_trades', 0) or 0),
        'trained_at': bundle.get('trained_at'),
        'errors': errors,
    }


def hybrid_ml_confidence_engine(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 9.2/9.5: RF + XGBoost + LightGBM + CatBoost with fallback.

    Trained mode uses saved models trained from actual closed trades.
    Fallback mode uses transparent heuristic until enough outcomes exist.
    """
    heuristic = _heuristic_probability(signal)
    models = _saved_model_predictions(signal)
    if models.get('available'):
        ml_prob = _safe_float(models.get('ensemble_probability'), heuristic)
        mode = 'trained_auto_learning_hybrid_ensemble'
        note = 'Auto-learning hybrid ML is active from real trade outcomes.'
    else:
        ml_prob = heuristic
        mode = 'heuristic_until_enough_closed_trades'
        note = 'Fallback ML score active. Close/update trades as WIN/LOSS to train automatic learning.'
    rule_conf = _safe_float(signal.get('confidence'), 50)
    trained = bool(models.get('available'))
    final = round((rule_conf * 0.40 + ml_prob * 0.60), 1) if trained else round((rule_conf * 0.65 + ml_prob * 0.35), 1)
    # Adaptive confidence: trade memory can slightly push final probability up/down.
    try:
        memory = trade_memory_ai(signal)
        final = round(max(0, min(95, final + _safe_float(memory.get('confidence_adjustment'), 0))), 1)
    except Exception:
        memory = {}
    return {
        'mode': mode,
        'rule_confidence': rule_conf,
        'ml_probability': ml_prob,
        'final_trade_score': final,
        'model_stack': ['RandomForest', 'XGBoost', 'LightGBM', 'CatBoost'],
        'trained_models': models.get('predictions', {}),
        'training_samples': models.get('training_samples', 0),
        'trained_at': models.get('trained_at'),
        'model_errors': models.get('errors', {}),
        'memory_adjustment': memory.get('confidence_adjustment', 0),
        'feature_names': PHASE9_FIXED_FEATURES,
        'feature_values': _features_from_signal_v2(signal),
        'note': note + (' ' + str(models.get('reason','')) if not trained else ''),
    }


def ml_trade_rejection_filter(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 15.23 smart filter: confidence stays strict, soft warnings stop over-blocking.

    Hard blocks:
    - base action WAIT
    - ML final score below 75
    - true economic calendar block when warning-only mode is OFF

    Soft warnings:
    - multi-agent disagreement
    - portfolio exposure caution
    - economic calendar warning-only

    This fixes the issue where A/A+ setups with 80%+ confidence were shown but
    blocked only because one advisory agent disagreed.
    """
    action = str(signal.get('action', 'WAIT')).upper()
    if action not in ['BUY', 'SELL']:
        return {'allow_trade': False, 'reasons': ['Base signal is WAIT.'], 'reason': 'Base signal is WAIT.', 'warnings': [], 'ml_final_score': 0}
    ml = hybrid_ml_confidence_engine(signal)
    vote = multi_agent_voting(signal)
    port = portfolio_manager_ai(signal)
    cal = economic_calendar_ai(signal)
    grade = _overall_grade(signal)
    confidence = _safe_float(signal.get('confidence'))
    ml_score = _safe_float(ml.get('final_trade_score'))
    min_conf = float(PHASE15_10_MIN_AUTOPILOT_CONFIDENCE or 80)
    reasons = []
    warnings = []
    allow = True

    if confidence < min_conf:
        allow = False; reasons.append(f'rule confidence below {int(min_conf)}')
    if ml_score < 75:
        allow = False; reasons.append('ML final trade score below 75')

    strong_a_setup = (_grade_value(grade) >= _grade_value('A') and confidence >= min_conf and ml_score >= 75)

    if vote.get('decision') == 'REJECT':
        if strong_a_setup:
            warnings.append('multi-agent disagreement treated as warning for A/A+ 80%+ setup')
        else:
            allow = False; reasons.append('multi-agent system rejected')
    if port.get('block_new_trade'):
        if strong_a_setup:
            warnings.append('portfolio exposure treated as caution; final quota/order guard still applies')
        else:
            allow = False; reasons.append('portfolio exposure blocked')
    if cal.get('block_new_trade'):
        if PHASE15_10_NEWS_AS_WARNING_ONLY:
            warnings.append('economic calendar risk warning only')
        else:
            allow = False; reasons.append('economic calendar risk blocked')

    if not reasons and not warnings:
        reasons.append('Smart filter passed: confidence, grade, ML and hard safety checks OK')
    reason_text = '; '.join(reasons + warnings)
    return {'allow_trade': allow, 'reasons': reasons or ['Smart filter passed'], 'warnings': warnings, 'reason': reason_text, 'ml_final_score': ml.get('final_trade_score')}

def a_plus_filter(signal: Dict[str, Any]) -> Dict[str, Any]:
    action = str(signal.get('action','WAIT')).upper()
    if action not in ['BUY','SELL']:
        return {'allow_autopilot': False, 'grade': 'WAIT', 'reason': 'Base signal is WAIT.'}
    grade = _overall_grade(signal)
    ml_filter = ml_trade_rejection_filter(signal)
    reasons = []
    warnings = list(ml_filter.get('warnings') or [])
    allow = bool(ml_filter.get('allow_trade'))
    min_grade = str(PHASE15_10_MIN_AUTOPILOT_GRADE or 'A').upper().strip()
    min_conf = float(PHASE15_10_MIN_AUTOPILOT_CONFIDENCE or 80)
    if _grade_value(grade) < _grade_value(min_grade):
        allow = False; reasons.append(f'grade {grade or "N/A"} is below {min_grade}')
    if _safe_float(signal.get('confidence')) < min_conf:
        allow = False; reasons.append(f'rule confidence below {int(min_conf)}')
    if not ml_filter.get('allow_trade'):
        reasons.append(ml_filter.get('reason'))
    if not reasons:
        reasons.append('A/A+ smart autopilot filter passed with 80%+ confidence and hard safety checks.')
    all_notes = reasons + warnings
    return {'allow_autopilot': allow, 'grade': grade, 'min_grade': min_grade, 'reasons': all_notes, 'warnings': warnings, 'reason': '; '.join([str(x) for x in all_notes if x]), 'ml_filter': ml_filter}

def ml_learning_report() -> str:
    ds = collect_labeled_trade_dataset()
    meta = _load_json_file(PHASE9_MODEL_META_FILE, {})
    model_exists = os.path.exists(PHASE9_MODEL_FILE)
    status = 'READY' if ds['ready'] else 'COLLECTING DATA'
    return (
        'Phase 9.1–9.5 Auto-Learning ML Report\n'
        f'Status                 : {status}\n'
        f'Labeled trades          : {ds["labeled_trades"]}\n'
        f'Wins / Losses           : {ds["wins"]} / {ds["losses"]}\n'
        f'Model file exists        : {model_exists}\n'
        f'Last trained at          : {meta.get("trained_at", "not trained yet")}\n'
        f'Model stack              : RandomForest + XGBoost + LightGBM + CatBoost\n'
        f'Feature count            : {len(PHASE9_FIXED_FEATURES)}\n'
        'Learning behavior        : retrains automatically after enough new closed trades\n'
        'Autopilot behavior       : blocks trades when ML score/voting/portfolio/news filters fail\n'
    )


def phase9_status_text() -> str:
    ds = collect_labeled_trade_dataset()
    meta = _load_json_file(PHASE9_MODEL_META_FILE, {})
    return (
        'Phase 9 Intelligence Status\n'
        f'Version                 : {PHASE9_AUTO_LEARNING_VERSION}\n'
        f'Database file           : {DATABASE_FILE}\n'
        f'Labeled win/loss trades  : {ds["labeled_trades"]}\n'
        f'Wins / Losses           : {ds["wins"]} / {ds["losses"]}\n'
        f'Model ready             : {os.path.exists(PHASE9_MODEL_FILE)}\n'
        f'Last trained at          : {meta.get("trained_at", "not trained yet")}\n'
        'Hybrid ML stack          : Random Forest + XGBoost + LightGBM + CatBoost\n'
        'Training rule            : train after 40+ labeled trades with both wins and losses\n'
        'Auto retrain             : every 10 new labeled outcomes\n'
        'Active phases            : 9.1 collector, 9.2 hybrid ML, 9.3 auto-retrain, 9.4 rejection filter, 9.5 adaptive confidence\n'
    )
