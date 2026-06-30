"""Phase 15.20 Human Trader Natural Brain.

Adds a light natural-trader layer on top of the existing signal stack without
changing the whole codebase. It converts the current structured analysis into:
- market story
- scenario planning (Plan A / B / C)
- invalidation logic
- patience / no-chase guidance
- short human-style report text

This module is advisory. It never forces an order and never bypasses risk,
A+ filters, or the Order Punch Shield.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _f(x: Any, d: int = 2) -> float:
    try:
        return round(float(x), d)
    except Exception:
        return 0.0


def _rr(signal: Dict[str, Any]) -> float:
    try:
        entry = float(signal.get("entry") or 0)
        stop = float(signal.get("stop_loss") or 0)
        tp2 = float(signal.get("target_2") or 0)
        risk = abs(entry - stop)
        if risk <= 0:
            return 0.0
        return round(abs(tp2 - entry) / risk, 2)
    except Exception:
        return 0.0


def build_market_story(signal: Dict[str, Any]) -> Dict[str, Any]:
    ctx = signal.get("market_context") or {}
    macro = signal.get("macro_brain") or {}
    no_trade = signal.get("no_trade_intelligence") or {}
    action = str(signal.get("action") or "WAIT").upper()
    direction = action if action in {"BUY", "SELL"} else str(ctx.get("trend") or "mixed").upper()
    symbol = signal.get("symbol", "Market")
    regime = ctx.get("regime_type", "unknown regime")
    align = int(float(ctx.get("timeframe_alignment") or 0) * 100)
    context_score = int(ctx.get("context_score") or 0)
    entry_tf = signal.get("entry_timeframe", "5m")
    session = signal.get("session", "unknown session")
    setup = signal.get("setup_type", "setup")
    event = str(signal.get("regime") or "").strip()
    news_note = str(macro.get("note") or "")
    risk_flags = ctx.get("risk_flags") or []
    note_bits: List[str] = []
    if risk_flags:
        note_bits.append("risk flags: " + ", ".join(risk_flags[:3]))
    if no_trade.get("decision") == "NO_TRADE":
        note_bits.append("best decision right now is WAIT")
    if news_note:
        note_bits.append(news_note)

    if action == "WAIT":
        story = (
            f"{symbol} is not giving a clean trade yet. The market context is {regime} with {align}% timeframe alignment "
            f"and a context score of {context_score}/100. Blue is reading the structure first, then waiting for a cleaner "
            f"entry trigger on {entry_tf}. Current setup type is {setup}. This is human-trader behaviour: do not force a trade "
            f"when the story is incomplete."
        )
    elif action == "BUY":
        story = (
            f"{symbol} has a bullish market story. Higher-timeframe context is {regime} with {align}% alignment and a "
            f"context score of {context_score}/100. Blue wants to buy only because the broader story, structure, and {entry_tf} "
            f"entry timing are supporting the same idea. Setup type: {setup}. Regime read: {event}. This behaves like a human trader: "
            f"wait for the level, confirm buyers are holding, then execute with invalidation already defined."
        )
    else:
        story = (
            f"{symbol} has a bearish market story. Higher-timeframe context is {regime} with {align}% alignment and a "
            f"context score of {context_score}/100. Blue wants to sell only because the broader story, structure, and {entry_tf} "
            f"entry timing are supporting the same idea. Setup type: {setup}. Regime read: {event}. This behaves like a human trader: "
            f"wait for price to confirm weakness near the planned zone instead of chasing after the move."
        )
    if note_bits:
        story += " Caution: " + " | ".join(note_bits[:3]) + "."

    bullets = [
        f"Bias: {direction}",
        f"Session: {session}",
        f"Regime: {regime}",
        f"Alignment: {align}%",
        f"Context score: {context_score}/100",
    ]
    return {
        "bias": direction,
        "story_text": story,
        "quick_story": f"{symbol} story: bias {direction}, regime {regime}, alignment {align}%, context {context_score}/100.",
        "bullets": bullets,
    }


def build_trade_scenarios(signal: Dict[str, Any]) -> Dict[str, Any]:
    symbol = signal.get("symbol", "Market")
    action = str(signal.get("action") or "WAIT").upper()
    entry = _f(signal.get("entry"), 5)
    stop = _f(signal.get("stop_loss"), 5)
    t1 = _f(signal.get("target_1"), 5)
    t2 = _f(signal.get("target_2"), 5)
    rr = _rr(signal)
    no_trade = signal.get("no_trade_intelligence") or {}

    if action == "BUY":
        plan_a = f"Plan A: Buy near {entry} only if price confirms the level and does not lose {stop}. First target {t1}, main target {t2}, RR about {rr}."
        plan_b = f"Plan B: If price runs too far before entry, do not chase. Wait for a retest or new {signal.get('entry_timeframe', '5m')} confirmation."
        plan_c = f"Plan C: If {stop} breaks cleanly, cancel the buy idea. Consider sell only if structure flips and a fresh bearish setup appears."
    elif action == "SELL":
        plan_a = f"Plan A: Sell near {entry} only if price confirms weakness and cannot reclaim {stop}. First target {t1}, main target {t2}, RR about {rr}."
        plan_b = f"Plan B: If price already dropped too far, do not chase. Wait for a pullback or a new {signal.get('entry_timeframe', '5m')} rejection."
        plan_c = f"Plan C: If {stop} breaks cleanly, cancel the sell idea. Consider buy only if structure flips and a fresh bullish setup appears."
    else:
        plan_a = f"Plan A: Wait. {symbol} needs cleaner confluence before any entry is justified."
        plan_b = "Plan B: If price gives a liquidity sweep plus displacement and then a clean retest, Blue can reassess the setup."
        plan_c = "Plan C: If market context worsens or news risk expands, stand aside completely and protect capital."
        if no_trade.get("hard_blocks"):
            plan_a += " Current block: " + "; ".join(no_trade.get("hard_blocks")[:2]) + "."
    return {"plan_a": plan_a, "plan_b": plan_b, "plan_c": plan_c, "plan_text": "\n".join([plan_a, plan_b, plan_c])}


def build_trade_invalidation(signal: Dict[str, Any]) -> str:
    action = str(signal.get("action") or "WAIT").upper()
    stop = _f(signal.get("stop_loss"), 5)
    entry = _f(signal.get("entry"), 5)
    symbol = signal.get("symbol", "Market")
    if action == "BUY":
        return f"{symbol} buy idea becomes invalid if price loses {stop} after entry or fails to hold the planned buy zone around {entry}."
    if action == "SELL":
        return f"{symbol} sell idea becomes invalid if price reclaims {stop} after entry or fails to reject the planned sell zone around {entry}."
    return f"No live trade idea to invalidate now. Wait for a clearer setup before defining invalidation."


def build_patience_filter(signal: Dict[str, Any]) -> Dict[str, Any]:
    action = str(signal.get("action") or "WAIT").upper()
    no_trade = signal.get("no_trade_intelligence") or {}
    context = signal.get("market_context") or {}
    risk_flags = context.get("risk_flags") or []
    notes = []
    if action == "WAIT":
        notes.append("Do not force a trade in the middle of noise.")
    else:
        notes.append("Do not chase after a large move away from the planned entry.")
        notes.append("Wait for the level to hold or reject first.")
    if risk_flags:
        notes.append("Be extra patient because of: " + ", ".join(risk_flags[:3]))
    if no_trade.get("hard_blocks"):
        notes.append("No-trade blocks active: " + "; ".join(no_trade.get("hard_blocks")[:2]))
    return {"allow_entry": action != "WAIT" and not bool(no_trade.get("hard_blocks")), "notes": notes, "note": " ".join(notes)}


def apply_human_trader_natural(signal: Dict[str, Any]) -> Dict[str, Any]:
    story = build_market_story(signal)
    scenarios = build_trade_scenarios(signal)
    invalidation = build_trade_invalidation(signal)
    patience = build_patience_filter(signal)
    signal["market_story"] = story
    signal["trade_scenarios"] = scenarios
    signal["trade_invalidation"] = invalidation
    signal["patience_filter"] = patience
    signal["human_trader_natural_brain"] = {
        "active": True,
        "version": "15.20",
        "note": "Natural human-trader layer active: market story, scenarios, invalidation, patience filter.",
    }
    natural_note = (
        f"Natural Human Trader Brain: {story.get('quick_story')} "
        f"{patience.get('note')} Invalidation: {invalidation}"
    ).strip()
    base = signal.get("analyst_reason", "")
    if natural_note not in base:
        signal["analyst_reason"] = (base + "\n\n" + natural_note).strip()
        signal["human_read"] = signal["analyst_reason"]
    return signal


def human_natural_status_text() -> str:
    return (
        "Blue Human Trader Natural Brain v15.20\n"
        "Features active: market story, scenario planning, trade invalidation, patience filter, natural-language trade explanation.\n"
        "Safety: advisory only; does not bypass risk rules, no-trade intelligence, neural checks, or Order Punch Shield."
    )


def render_human_report(signal: Dict[str, Any]) -> str:
    story = signal.get("market_story") or build_market_story(signal)
    scenarios = signal.get("trade_scenarios") or build_trade_scenarios(signal)
    invalidation = signal.get("trade_invalidation") or build_trade_invalidation(signal)
    patience = signal.get("patience_filter") or build_patience_filter(signal)
    return "\n".join([
        f"{signal.get('symbol', 'Market')} Human Trader Report",
        "-" * 40,
        story.get("story_text", ""),
        "",
        scenarios.get("plan_a", ""),
        scenarios.get("plan_b", ""),
        scenarios.get("plan_c", ""),
        "",
        "Invalidation: " + invalidation,
        "Patience filter: " + patience.get("note", ""),
    ])
