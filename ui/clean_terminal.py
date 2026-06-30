"""Phase 15.21 Clean Terminal UI.

Keeps terminal output readable by printing a short signal card first.
Verbose engines still run internally; this only changes presentation.
"""
from __future__ import annotations

from typing import Any, Dict


def _short(text: Any, limit: int = 420) -> str:
    s = str(text or "").replace("\n", " ").strip()
    while "  " in s:
        s = s.replace("  ", " ")
    if len(s) <= limit:
        return s
    return s[:limit].rstrip() + "..."


def _line(char: str = "=", n: int = 66) -> str:
    return char * n


def _pick_action_note(r: Dict[str, Any]) -> str:
    action = str(r.get("action", "WAIT")).upper()
    if action == "BUY":
        return "BUY allowed only if risk + broker checks pass. Do not chase late entry."
    if action == "SELL":
        return "SELL allowed only if risk + broker checks pass. Do not chase late entry."
    return "WAIT. Protect capital until the setup becomes cleaner."


def print_clean_signal_card(r: Dict[str, Any]) -> None:
    risk = r.get("risk", {}) or {}
    action = str(r.get("action", "WAIT")).upper()
    symbol = r.get("symbol", "Unknown")
    confidence = r.get("confidence", 0)
    style = r.get("trade_style_label", "Intraday")
    entry_tf = r.get("entry_timeframe", "5m")
    lot = risk.get("recommended_lot_size", 0)
    src = str(r.get("chart_data_source") or "unknown").upper()
    broker_symbol = r.get("broker_chart_symbol") or ""
    story = (r.get("market_story") or {}).get("quick_story") or (r.get("market_story") or {}).get("story_text")
    plans = r.get("trade_scenarios") or {}
    invalidation = r.get("trade_invalidation") or "Not available."
    patience = (r.get("patience_filter") or {}).get("note", "")
    nn = r.get("neural_network_brain") or {}
    ap = r.get("a_plus_filter") or {}
    no_trade = r.get("no_trade_intelligence") or {}
    ds = r.get("dataset_ml_engine") or {}
    ml = r.get("hybrid_ml_confidence_engine") or {}

    print("\n" + _line("="))
    print("BLUE SIGNAL CARD")
    print(_line("-"))
    print(f"Symbol     : {symbol}")
    print(f"Decision   : {action} | Confidence: {confidence}%")
    print(f"Style/TF   : {style} | Entry TF: {entry_tf}")
    print(f"Data       : {src}" + (f" | Broker: {broker_symbol}" if broker_symbol else ""))
    print(f"Entry      : {r.get('entry')}")
    print(f"Stop Loss  : {r.get('stop_loss')}")
    print(f"Targets    : TP1 {r.get('target_1')} | TP2 {r.get('target_2')}")
    print(f"Lot        : {lot} lots")
    if risk.get("lot_note"):
        print(f"Lot note   : {_short(risk.get('lot_note'), 140)}")

    print(_line("-"))
    print("Reason")
    print(_short(r.get("analyst_reason") or r.get("human_read"), 520))

    if story:
        print(_line("-"))
        print("Market Story")
        print(_short(story, 360))

    if plans:
        print(_line("-"))
        print("Plan")
        for key in ["plan_a", "plan_b", "plan_c"]:
            if plans.get(key):
                print("- " + _short(plans.get(key), 220))

    print(_line("-"))
    print("Safety")
    if no_trade:
        print(f"- No-Trade Brain: {no_trade.get('decision', 'CHECKED')} | {_short(no_trade.get('note'), 160)}")
    if nn:
        if nn.get("available"):
            print(f"- Neural Brain: {nn.get('neural_probability')}% | {nn.get('decision')}")
        else:
            print(f"- Neural Brain: {_short(nn.get('note'), 160)}")
    if ds and ds.get("available"):
        print(f"- Dataset ML: {ds.get('dataset_probability')}% | {ds.get('decision')}")
    elif ml:
        print(f"- Hybrid ML: {ml.get('final_trade_score', ml.get('ml_probability', 'n/a'))}% | {_short(ml.get('note'), 120)}")
    if ap:
        print(f"- A+ Filter: {'PASS' if ap.get('allow_autopilot') else 'BLOCK'} | {_short(ap.get('reason'), 160)}")
    print("- Order Punch Shield: MT5 order_check + retry/filling-mode protection before order_send.")

    print(_line("-"))
    print("Invalidation")
    print(_short(invalidation, 260))
    if patience:
        print("Patience   : " + _short(patience, 240))
    print("Next       : " + _pick_action_note(r))
    print(_line("=") + "\n")
