"""Phase 10 Human Trader Brain.

Adds eight upgrades:
1) market context brain
2) human-style decision pipeline
3) trade memory brain
4) auto ML learning from outcomes
5) no-trade intelligence
6) news and macro brain
7) broker intelligence hooks
8) trader personality modes
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple
from pathlib import Path
import json
import math

try:
    from config import (
        DEFAULT_TRADER_PERSONALITY_MODE, TRADER_PERSONALITY_MODES,
        HUMAN_BRAIN_NO_TRADE_RULES,
        PHASE15_10_NEWS_AS_WARNING_ONLY,
        PHASE15_10_MIN_AUTOPILOT_CONFIDENCE,
    )
except Exception:
    PHASE15_10_NEWS_AS_WARNING_ONLY = False
    PHASE15_10_MIN_AUTOPILOT_CONFIDENCE = 85
    DEFAULT_TRADER_PERSONALITY_MODE = "balanced"
    TRADER_PERSONALITY_MODES = {
        "balanced": {"label": "Balanced", "min_confidence": 85, "min_rr_to_tp2": 1.5, "max_context_risk_flags": 2, "block_choppy_market": False, "block_news": True, "allow_autopilot": True, "risk_multiplier": 1.0}
    }
    HUMAN_BRAIN_NO_TRADE_RULES = {"minimum_timeframe_alignment": 0.55, "minimum_context_score": 55}

from news.macro_brain import build_macro_brain
from learning.auto_ml_learning import apply_outcome_learning
from memory.trade_memory_brain import infer_setup_type

TRADER_MODE_FILE = Path("trader_mode_settings.json")

def get_saved_trader_mode() -> str:
    try:
        data = json.loads(TRADER_MODE_FILE.read_text(encoding="utf-8"))
        mode = str(data.get("mode", "")).lower().strip()
        if mode in TRADER_PERSONALITY_MODES:
            return mode
    except Exception:
        pass
    return DEFAULT_TRADER_PERSONALITY_MODE

def set_trader_mode_text(mode: str) -> str:
    mode = (mode or "").lower().strip().replace(" ", "_")
    aliases = {"safe": "conservative", "paper": "learning", "demo": "learning", "normal": "balanced", "balanced_mode": "balanced"}
    mode = aliases.get(mode, mode)
    if mode not in TRADER_PERSONALITY_MODES:
        return "Unknown trader mode. Use: trader mode conservative / balanced / aggressive / learning"
    TRADER_MODE_FILE.write_text(json.dumps({"mode": mode}, indent=2), encoding="utf-8")
    cfg = TRADER_PERSONALITY_MODES[mode]
    label = cfg.get("label", mode.title())
    desc = cfg.get("description", "")
    return f"Trader mode set to {mode} — {label}. {desc}"

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return default
        return float(x)
    except Exception:
        return default

def _last(df, col: str, default: float = 0.0) -> float:
    try:
        return _safe_float(df.iloc[-1].get(col), default)
    except Exception:
        return default

def _atr_percent(df) -> float:
    close = _last(df, "close", 0)
    atr = _last(df, "atr_14", 0)
    return round((atr / close * 100) if close else 0, 4)

def _trend_from_scores(tf_results: Dict[str, Any]) -> Tuple[str, float, Dict[str, int]]:
    scores = {tf: _safe_float(v.get("score")) for tf, v in (tf_results or {}).items()}
    bull = sum(1 for s in scores.values() if s > 0.5)
    bear = sum(1 for s in scores.values() if s < -0.5)
    total = max(1, len(scores))
    if bull > bear:
        return "bullish", bull / total, {"bullish": bull, "bearish": bear, "mixed": total - bull - bear}
    if bear > bull:
        return "bearish", bear / total, {"bullish": bull, "bearish": bear, "mixed": total - bull - bear}
    return "mixed", max(bull, bear) / total, {"bullish": bull, "bearish": bear, "mixed": total - bull - bear}

def build_market_context(name: str, ticker: str, raw: Dict[str, Any], tf_results: Dict[str, Any], session: str, news: Dict[str, Any], sentiment: Dict[str, Any]) -> Dict[str, Any]:
    main_df = raw.get("1h")
    if main_df is None:
        main_df = raw.get("15m")
    if main_df is None:
        main_df = raw.get("5m")
    if main_df is None:
        main_df = next(iter(raw.values()))
    entry_df = raw.get("5m")
    if entry_df is None:
        entry_df = main_df
    trend, alignment, counts = _trend_from_scores(tf_results)
    atr_pct_1h = _atr_percent(main_df)
    atr_pct_5m = _atr_percent(entry_df)

    # Human trader style market regime classification.
    if alignment < 0.45:
        regime_type = "choppy/mixed"
    elif atr_pct_1h >= 1.8:
        regime_type = "high-volatility trending" if trend != "mixed" else "high-volatility mixed"
    elif atr_pct_1h <= 0.08:
        regime_type = "low-volatility compression"
    else:
        regime_type = f"{trend} trending" if trend != "mixed" else "balanced range"

    risk_flags = []
    if "choppy" in regime_type or trend == "mixed":
        risk_flags.append("timeframe_conflict")
    if atr_pct_1h >= 1.8:
        risk_flags.append("high_volatility")
    if atr_pct_1h <= 0.08:
        risk_flags.append("dead_market")
    if news.get("blocked"):
        risk_flags.append("high_impact_news")
    if "unavailable" in str(news.get("note", "")).lower():
        risk_flags.append("calendar_unverified")

    score = 50 + int((alignment - 0.5) * 60)
    if trend != "mixed":
        score += 8
    score -= len(risk_flags) * 7
    score = max(0, min(100, score))

    correlation_note = ""
    if ticker in {"EURUSD=X", "GBPUSD=X"}:
        correlation_note = "USD/DXY inverse correlation matters; avoid buying if DXY is strongly bullish."
    elif ticker in {"GC=F", "SI=F"}:
        correlation_note = "Gold/silver are USD and risk-sentiment sensitive; news spikes can fake out SMC setups."
    elif ticker == "JPY=X":
        correlation_note = "USDJPY reacts strongly to USD yields, BOJ/JPY intervention risk and risk sentiment."
    elif ticker in {"BTC-USD", "ETH-USD"}:
        correlation_note = "Crypto can ignore classic forex sessions; volatility and sentiment filters matter more."
    else:
        correlation_note = "Check correlated USD/risk assets before live execution."

    return {
        "timestamp_utc": datetime.utcnow().isoformat(),
        "symbol": name,
        "ticker": ticker,
        "trend": trend,
        "timeframe_alignment": round(alignment, 2),
        "timeframe_counts": counts,
        "regime_type": regime_type,
        "context_score": score,
        "atr_percent_1h": atr_pct_1h,
        "atr_percent_5m": atr_pct_5m,
        "session": session,
        "risk_flags": risk_flags,
        "correlation_note": correlation_note,
        "note": f"Market context: {regime_type}, {round(alignment*100)}% timeframe alignment, context score {score}/100.",
    }

def _rr(signal: Dict[str, Any]) -> Dict[str, float]:
    action = signal.get("action")
    entry = _safe_float(signal.get("entry"))
    sl = _safe_float(signal.get("stop_loss"))
    t1 = _safe_float(signal.get("target_1"))
    t2 = _safe_float(signal.get("target_2"))
    risk = abs(entry - sl)
    if risk <= 0:
        return {"risk_distance": 0, "rr_to_tp1": 0, "rr_to_tp2": 0}
    return {
        "risk_distance": round(risk, 6),
        "rr_to_tp1": round(abs(t1 - entry) / risk, 2),
        "rr_to_tp2": round(abs(t2 - entry) / risk, 2),
    }

def _stage(status: str, name: str, detail: str) -> Dict[str, str]:
    return {"status": status, "stage": name, "detail": detail}

def build_decision_pipeline(signal: Dict[str, Any]) -> List[Dict[str, str]]:
    ctx = signal.get("market_context") or {}
    macro = signal.get("macro_brain") or {}
    rr = signal.get("reward_risk") or _rr(signal)
    action = signal.get("action")
    confidence = int(signal.get("confidence") or 0)
    trend = ctx.get("trend", "mixed")
    alignment = float(ctx.get("timeframe_alignment") or 0)
    risk_flags = ctx.get("risk_flags") or []

    pipeline = []
    pipeline.append(_stage("PASS" if ctx.get("context_score", 0) >= 55 else "WARN", "Market Regime", ctx.get("note", "Context unavailable.")))
    pipeline.append(_stage("PASS" if trend.lower() in str(signal.get("regime", "")).lower() or alignment >= 0.55 else "WARN", "Higher Timeframe Bias", f"Trend={trend}, alignment={round(alignment*100)}%."))
    pipeline.append(_stage("PASS" if signal.get("liquidity_heatmap") else "WARN", "Liquidity / Key Levels", "Liquidity heatmap and SMC zones checked." if signal.get("liquidity_heatmap") else "No strong liquidity map found."))
    pipeline.append(_stage("PASS" if action != "WAIT" else "BLOCK", "Setup Detection", f"Setup type: {signal.get('setup_type') or infer_setup_type(signal)}."))
    pipeline.append(_stage("PASS" if signal.get("entry_timeframe") else "WARN", "Entry Trigger", f"Entry timeframe: {signal.get('entry_timeframe', 'unknown')}."))
    pipeline.append(_stage("PASS" if rr.get("risk_distance", 0) > 0 else "BLOCK", "Stop Loss Logic", f"Risk distance: {rr.get('risk_distance', 0)}."))
    pipeline.append(_stage("PASS" if rr.get("rr_to_tp2", 0) >= 1.5 else "WARN", "Take Profit Logic", f"RR to TP1={rr.get('rr_to_tp1')}, RR to TP2={rr.get('rr_to_tp2')}."))
    risk_status = "PASS" if confidence >= 85 and len(risk_flags) <= 2 and macro.get("risk_score", 0) < 35 else "WARN"
    pipeline.append(_stage(risk_status, "Risk Check", f"Confidence={confidence}%, risk flags={risk_flags or 'none'}, macro risk={macro.get('risk_score', 0)}/100."))
    final_status = "PASS" if action != "WAIT" and confidence >= 85 else "BLOCK"
    pipeline.append(_stage(final_status, "Trade or No Trade", "Trade can be considered only after lot-size and broker checks." if final_status == "PASS" else "No trade until cleaner confluence appears."))
    return pipeline

def _active_mode(signal: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    mode = str(signal.get("trader_mode") or get_saved_trader_mode() or "balanced").lower().strip()
    if mode not in TRADER_PERSONALITY_MODES:
        mode = "balanced" if "balanced" in TRADER_PERSONALITY_MODES else next(iter(TRADER_PERSONALITY_MODES))
    return mode, TRADER_PERSONALITY_MODES[mode]

def apply_no_trade_intelligence(signal: Dict[str, Any]) -> Dict[str, Any]:
    mode_name, mode = _active_mode(signal)
    ctx = signal.get("market_context") or {}
    macro = signal.get("macro_brain") or {}
    rr = signal.get("reward_risk") or _rr(signal)
    blocks = []
    warnings = []
    original_action = signal.get("action")
    confidence = int(signal.get("confidence") or 0)
    risk_flags = ctx.get("risk_flags") or []

    if original_action == "WAIT":
        blocks.append("Base strategy already says WAIT.")
    min_conf = int(mode.get("min_confidence", 85))
    if PHASE15_10_NEWS_AS_WARNING_ONLY:
        min_conf = min(min_conf, int(PHASE15_10_MIN_AUTOPILOT_CONFIDENCE or 80))
    if confidence < min_conf:
        blocks.append(f"Confidence {confidence}% is below {mode_name} mode minimum {min_conf}%.")
    if rr.get("risk_distance", 0) <= 0 and HUMAN_BRAIN_NO_TRADE_RULES.get("block_if_stop_loss_zero", True):
        blocks.append("Invalid stop-loss/risk distance.")
    if rr.get("rr_to_tp2", 0) < float(mode.get("min_rr_to_tp2", 1.5)) and HUMAN_BRAIN_NO_TRADE_RULES.get("block_if_rr_invalid", True):
        blocks.append(f"Reward/risk to TP2 is {rr.get('rr_to_tp2')}, below mode minimum {mode.get('min_rr_to_tp2')}.")
    if ctx.get("context_score", 0) < HUMAN_BRAIN_NO_TRADE_RULES.get("minimum_context_score", 55):
        blocks.append(f"Market context score is weak: {ctx.get('context_score', 0)}/100.")
    if float(ctx.get("timeframe_alignment") or 0) < HUMAN_BRAIN_NO_TRADE_RULES.get("minimum_timeframe_alignment", 0.55):
        blocks.append("Timeframe alignment is not clean enough.")
    if len(risk_flags) > int(mode.get("max_context_risk_flags", 2)):
        blocks.append(f"Too many context risk flags: {', '.join(risk_flags)}.")
    if mode.get("block_choppy_market") and "choppy" in str(ctx.get("regime_type", "")).lower():
        blocks.append("Conservative mode blocks choppy/mixed markets.")
    if mode.get("block_news") and macro.get("risk_score", 0) >= 35:
        if PHASE15_10_NEWS_AS_WARNING_ONLY:
            warnings.append("High-impact macro/news risk detected; demo working mode treats it as warning only.")
        else:
            blocks.append("High-impact macro/news risk blocks the trade.")
    if original_action != "WAIT" and macro.get("risk_score", 0) > 0:
        warnings.append(macro.get("note", "Macro caution present."))
    if not mode.get("allow_autopilot", True):
        warnings.append(f"{mode.get('label', mode_name)} does not allow autopilot execution by default.")

    hard_block = bool(blocks)
    signal["no_trade_intelligence"] = {
        "mode": mode_name,
        "allow_trade": not hard_block,
        "hard_blocks": blocks,
        "warnings": warnings,
        "decision": "NO_TRADE" if hard_block else "TRADE_ALLOWED_AFTER_RISK_CHECK",
        "note": " | ".join(blocks or warnings or ["No-trade filters passed."]),
    }
    if hard_block and original_action != "WAIT":
        signal["original_action_before_no_trade"] = original_action
        signal["action"] = "WAIT"
        reason = signal.get("analyst_reason", "")
        signal["analyst_reason"] = (reason + "\n\nHuman No-Trade Brain: " + signal["no_trade_intelligence"]["note"]).strip()
        signal["human_read"] = signal["analyst_reason"]
    return signal

def apply_trader_personality(signal: Dict[str, Any]) -> Dict[str, Any]:
    mode_name, mode = _active_mode(signal)
    signal["trader_mode"] = mode_name
    signal["trader_personality"] = {
        "mode": mode_name,
        "label": mode.get("label", mode_name.title()),
        "description": mode.get("description", ""),
        "risk_multiplier": mode.get("risk_multiplier", 1.0),
        "allow_autopilot": mode.get("allow_autopilot", True),
    }
    if signal.get("action") != "WAIT" and mode.get("risk_multiplier", 1.0) == 0:
        signal["no_trade_intelligence"] = signal.get("no_trade_intelligence") or {}
        signal["no_trade_intelligence"]["decision"] = "PAPER_TRADE_ONLY"
        signal["no_trade_intelligence"]["warnings"] = list(signal["no_trade_intelligence"].get("warnings", [])) + ["Learning mode is paper-trade only."]
    return signal

def apply_human_trader_brain(signal: Dict[str, Any]) -> Dict[str, Any]:
    signal["setup_type"] = signal.get("setup_type") or infer_setup_type(signal)
    signal["reward_risk"] = _rr(signal)
    signal = apply_outcome_learning(signal)
    signal = apply_trader_personality(signal)
    signal["decision_pipeline"] = build_decision_pipeline(signal)
    signal = apply_no_trade_intelligence(signal)
    signal["human_trader_brain_summary"] = (
        f"Human Brain: mode={signal.get('trader_mode')}, setup={signal.get('setup_type')}, "
        f"context={signal.get('market_context', {}).get('regime_type', 'unknown')}, "
        f"no-trade={signal.get('no_trade_intelligence', {}).get('decision')}."
    )
    base = signal.get("analyst_reason", "")
    summary = signal["human_trader_brain_summary"]
    if summary not in base:
        signal["analyst_reason"] = (base + "\n\n" + summary).strip()
        signal["human_read"] = signal["analyst_reason"]
    return signal

def trader_modes_text() -> str:
    lines = ["Trader Personality Modes"]
    for k, v in TRADER_PERSONALITY_MODES.items():
        lines.append(f"- {k}: {v.get('label')} | min confidence {v.get('min_confidence')}% | min RR {v.get('min_rr_to_tp2')} | autopilot={v.get('allow_autopilot')}")
        if v.get("description"):
            lines.append(f"  {v.get('description')}")
    lines.append("Use in config.py: DEFAULT_TRADER_PERSONALITY_MODE = 'conservative' / 'balanced' / 'aggressive' / 'learning'")
    return "\n".join(lines)

def human_brain_status_text() -> str:
    mode, cfg = _active_mode({"trader_mode": get_saved_trader_mode()})
    return "\n".join([
        "Blue Human Trader Brain v1",
        "Upgrades active: market context, decision pipeline, trade memory, auto outcome learning, no-trade intelligence, macro/news brain, broker intelligence hooks, personality modes.",
        f"Default mode: {mode} — {cfg.get('label', mode)}",
        f"Rules: min confidence={cfg.get('min_confidence')}%, min RR to TP2={cfg.get('min_rr_to_tp2')}, block news={cfg.get('block_news')}, autopilot={cfg.get('allow_autopilot')}",
    ])
