
"""Phase 8 Human AI Trading Desk upgrades.

This module adds automatic desk-style reasoning to every signal:
- multi-agent opinions
- market regime classification
- probability tree
- trade quality grades
- institutional thesis
- portfolio risk notes
- market narrative
- replay coach note
- research-agent summary

It is intentionally lightweight and offline-safe: no paid API is required.
"""
from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _tf_scores(signal: Dict[str, Any]) -> List[float]:
    vals = []
    for d in (signal.get("timeframes") or {}).values():
        vals.append(_safe_float(d.get("score")))
    return vals or [0.0]


def detect_market_regime(signal: Dict[str, Any]) -> Dict[str, Any]:
    scores = _tf_scores(signal)
    avg = mean(scores)
    spread = max(scores) - min(scores) if scores else 0
    action = str(signal.get("action", "WAIT")).upper()
    confidence = _safe_float(signal.get("confidence"))
    regime_text = str(signal.get("regime", "")).lower()

    if action == "WAIT" or confidence < 66:
        regime = "No-trade / unclear regime"
        strategy = "wait for liquidity sweep, displacement, then 5-minute retest confirmation"
    elif abs(avg) >= 3 and spread <= 4:
        regime = "Trending expansion"
        strategy = "trade pullbacks into FVG/order block with trend continuation logic"
    elif spread > 6:
        regime = "Mixed multi-timeframe regime"
        strategy = "reduce aggressiveness and demand cleaner 5-minute confirmation"
    elif "premium" in regime_text or "discount" in regime_text:
        regime = "Dealing-range liquidity regime"
        strategy = "use premium/discount plus external liquidity as target map"
    else:
        regime = "Balanced intraday regime"
        strategy = "take only high-confluence intraday setups"

    return {"name": regime, "avg_score": round(avg, 2), "score_spread": round(spread, 2), "strategy": strategy}


def probability_tree(signal: Dict[str, Any]) -> Dict[str, Any]:
    confidence = _safe_float(signal.get("confidence"))
    action = str(signal.get("action", "WAIT")).upper()
    if action == "WAIT":
        return {"tp1": 0, "tp2": 0, "sl": 0, "note": "No probability tree because Blue does not see a clean trade."}

    # Convert confidence into a simple probability model. It is a model estimate, not a guarantee.
    tp1 = max(35, min(85, confidence - 5))
    tp2 = max(20, min(70, confidence - 18))
    sl = max(10, min(65, 100 - tp1 + 5))
    return {
        "tp1": round(tp1, 1),
        "tp2": round(tp2, 1),
        "sl": round(sl, 1),
        "note": f"Estimated probability: TP1 {round(tp1,1)}%, TP2 {round(tp2,1)}%, SL-risk {round(sl,1)}%."
    }


def trade_quality_grades(signal: Dict[str, Any]) -> Dict[str, str]:
    confidence = _safe_float(signal.get("confidence"))
    scores = _tf_scores(signal)
    alignment = sum(1 for s in scores if (s > 0 and signal.get("action") == "BUY") or (s < 0 and signal.get("action") == "SELL"))
    heat = len(signal.get("liquidity_heatmap") or [])
    news_text = str(signal.get("news_caution", "")).lower()

    def grade(num: float) -> str:
        if num >= 85: return "A+"
        if num >= 78: return "A"
        if num >= 70: return "B+"
        if num >= 62: return "B"
        return "C / Avoid"

    setup_score = confidence + alignment * 2
    liquidity_score = 68 + heat * 6
    risk_score = confidence - (10 if "high-impact" in news_text else 0)
    execution_score = confidence + (5 if signal.get("entry_timeframe") == "5m" else 0)
    return {
        "setup": grade(setup_score),
        "risk": grade(risk_score),
        "liquidity": grade(liquidity_score),
        "execution": grade(execution_score),
        "overall": grade(mean([setup_score, risk_score, liquidity_score, execution_score])),
    }


def multi_agent_team(signal: Dict[str, Any]) -> Dict[str, Any]:
    action = str(signal.get("action", "WAIT")).upper()
    confidence = _safe_float(signal.get("confidence"))
    grades = trade_quality_grades(signal)
    regime = detect_market_regime(signal)
    probability = probability_tree(signal)

    if action == "WAIT":
        decision = "No trade. Desk team agrees to wait."
    elif confidence >= 80 and grades["overall"] in ["A+", "A", "B+"]:
        decision = f"Approved for {action} if MT5 safeguards, spread, daily loss guard, and news checks remain safe."
    else:
        decision = f"Conditional {action}. Use smaller risk or wait for a cleaner 5-minute confirmation."

    agents = {
        "market_analyst": f"Bias is {action}. Regime: {regime['name']}.",
        "risk_manager": f"Risk grade {grades['risk']}. Respect daily loss and max exposure rules.",
        "liquidity_agent": f"Liquidity grade {grades['liquidity']}. Use mapped liquidity as target/invalidation context.",
        "execution_agent": f"Execution grade {grades['execution']}. Entry timing should stay on {signal.get('entry_timeframe','5m')}.",
        "research_agent": probability.get("note", "Probability model unavailable."),
        "final_desk_decision": decision,
    }
    return agents


def institutional_thesis(signal: Dict[str, Any]) -> Dict[str, str]:
    action = str(signal.get("action", "WAIT")).upper()
    regime = detect_market_regime(signal)
    prob = probability_tree(signal)
    heat = signal.get("liquidity_heatmap") or []
    liq = "No major liquidity pool detected."
    if heat:
        top = heat[0]
        liq = f"Primary liquidity focus: {top.get('side')} liquidity near {round(_safe_float(top.get('level')), 5)}."

    if action == "WAIT":
        thesis = "No institutional thesis is active because confluence is not strong enough."
        invalidation = "Wait until structure and liquidity align."
    else:
        thesis = (
            f"{action} thesis: Blue aligned higher-timeframe context with intraday 5-minute execution. "
            f"Regime is {regime['name']}. {liq} {prob['note']}"
        )
        invalidation = f"Trade idea is invalid if price breaks the protected stop area at {signal.get('stop_loss')}."

    return {
        "bias": action,
        "thesis": thesis,
        "liquidity_target": liq,
        "invalidation": invalidation,
        "execution_plan": f"Use {signal.get('entry_timeframe','5m')} entry timing; avoid chasing after large displacement.",
    }


def portfolio_risk_note(signal: Dict[str, Any]) -> str:
    symbol = str(signal.get("symbol", "symbol"))
    action = str(signal.get("action", "WAIT")).upper()
    if action == "WAIT":
        return "Portfolio note: no new exposure because signal is WAIT."
    correlated = {
        "gold": "silver and USD-related pairs",
        "eurusd": "GBPUSD and DXY inverse exposure",
        "gbpusd": "EURUSD and DXY inverse exposure",
        "btc": "ETH and crypto basket exposure",
        "eth": "BTC and crypto basket exposure",
        "nasdaq": "SPX/US500 index exposure",
    }
    related = "related pairs"
    for k, v in correlated.items():
        if k in symbol.lower():
            related = v
            break
    return f"Portfolio note: before adding this {action}, check existing exposure in {related}. Avoid stacking the same risk direction."


def replay_coach_note(signal: Dict[str, Any]) -> str:
    action = str(signal.get("action", "WAIT")).upper()
    if action == "WAIT":
        return "Coach: good discipline is waiting. No clean confirmation means no forced trade."
    return (
        "Coach: after this trade closes, review whether entry followed sweep → displacement → retest logic, "
        "whether the 5-minute entry was clean, and whether partial profit/trailing rules were followed."
    )


def research_agent_summary(signal: Dict[str, Any]) -> str:
    sentiment = (signal.get("sentiment") or {}).get("note", "No sentiment note.")
    news = signal.get("news_caution", "Check news.")
    return f"Research agent: {sentiment} News filter: {news}"


def market_narrative(signal: Dict[str, Any]) -> str:
    thesis = institutional_thesis(signal)
    grades = trade_quality_grades(signal)
    agents = multi_agent_team(signal)
    return (
        f"Desk narrative: {thesis['thesis']} Overall grade is {grades['overall']}. "
        f"{agents['final_desk_decision']} {thesis['invalidation']}"
    )


def upgrade_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Attach Phase 8 desk intelligence automatically to a signal dict."""
    signal["market_regime_ai"] = detect_market_regime(signal)
    signal["probability_engine"] = probability_tree(signal)
    signal["trade_quality_grades"] = trade_quality_grades(signal)
    signal["multi_agent_team"] = multi_agent_team(signal)
    signal["institutional_thesis"] = institutional_thesis(signal)
    signal["portfolio_risk_note"] = portfolio_risk_note(signal)
    signal["replay_coach_note"] = replay_coach_note(signal)
    signal["research_agent_summary"] = research_agent_summary(signal)
    signal["market_narrative"] = market_narrative(signal)
    signal["phase8_upgrades"] = [
        "multi-agent AI desk", "market regime AI", "probability tree", "trade quality grades",
        "institutional thesis", "portfolio risk note", "market narrative", "replay coach",
        "research agent", "automatic scanner ranking support"
    ]
    # Add the desk narrative to the human explanation so it works automatically everywhere.
    base_reason = signal.get("analyst_reason") or signal.get("human_read") or ""
    desk = signal["market_narrative"]
    if desk not in base_reason:
        signal["analyst_reason"] = (base_reason + "\n\n" + desk).strip()
        signal["human_read"] = signal["analyst_reason"]
    return signal
