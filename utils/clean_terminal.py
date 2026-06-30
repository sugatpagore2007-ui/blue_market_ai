"""Clean terminal output helpers for Phase 15.21."""
from __future__ import annotations

from typing import Any, Dict

WIDTH = 78


def line(char: str = "-") -> str:
    return char * WIDTH


def title(text: str) -> str:
    text = (text or "").strip()
    return "\n" + line("=") + "\n" + text.upper().center(WIDTH) + "\n" + line("=")


def section(text: str) -> str:
    return "\n" + text.strip().upper() + "\n" + line("-")


def kv(label: str, value: Any) -> str:
    return f"{label:<16}: {value}"


def compact_signal_card(r: Dict[str, Any]) -> str:
    risk = r.get("risk", {}) or {}
    nn = r.get("neural_network_brain") or {}
    ds = r.get("dataset_ml_engine") or {}
    cme = r.get("cme_group_brain") or {}
    nt = r.get("no_trade_intelligence") or {}
    ms = r.get("market_story") or {}
    ts = r.get("trade_scenarios") or {}
    lines = [title(f"Blue Signal — {r.get('symbol', 'Market')}")]
    lines += [
        kv("Action", f"{r.get('action')} | Confidence {r.get('confidence')}%"),
        kv("Style", f"{r.get('trade_style_label', 'Intraday')} | Entry TF {r.get('entry_timeframe', '5m')}"),
        kv("Entry", r.get('entry')),
        kv("Stop Loss", r.get('stop_loss')),
        kv("Target 1", r.get('target_1')),
        kv("Target 2", r.get('target_2')),
        kv("Lot", str(risk.get('recommended_lot_size', 0)) + " lots"),
    ]
    if r.get("broker_chart_symbol"):
        lines.append(kv("Broker Symbol", r.get("broker_chart_symbol")))
    lines.append(section("Trade reason"))
    reason = r.get("analyst_reason") or r.get("human_read") or "No reason generated."
    # Keep terminal readable: only first 8 non-empty lines of reason.
    reason_lines = [x.strip() for x in str(reason).splitlines() if x.strip()]
    lines.extend(reason_lines[:8])
    if len(reason_lines) > 8:
        lines.append("... type 'why' or 'human report' for full reasoning.")
    if ms:
        lines.append(section("Market story"))
        lines.append(ms.get("quick_story") or ms.get("story_text") or "Story unavailable.")
    if ts:
        lines.append(section("Plan"))
        for key in ["plan_a", "plan_b", "plan_c"]:
            v = ts.get(key)
            if v:
                lines.append(v)
    if r.get("trade_invalidation"):
        lines.append(section("Invalidation"))
        lines.append(str(r.get("trade_invalidation")))
    if nn or ds or cme or nt:
        lines.append(section("Brains"))
        if nn:
            if nn.get("available"):
                lines.append(kv("Neural", f"{nn.get('neural_probability')}% | {nn.get('decision')}"))
            else:
                lines.append(kv("Neural", nn.get("note", "not available")))
        if ds:
            if ds.get("available"):
                lines.append(kv("Dataset ML", f"{ds.get('dataset_probability')}% | {ds.get('decision')}"))
            else:
                lines.append(kv("Dataset ML", ds.get("note", "not available")))
        if cme:
            contract = cme.get("contract") or "-"
            conf = cme.get("confirmation") or "neutral"
            delta = cme.get("confidence_delta", 0)
            lines.append(kv("CME", f"{contract} | {conf} | delta {delta}"))
            note = cme.get("note")
            if note and cme.get("available"):
                lines.append("  " + str(note)[:120])
        if nt:
            lines.append(kv("No-Trade", nt.get("decision", "checked")))
            note = nt.get("note")
            if note:
                lines.append("  " + str(note))
    if r.get("patience_filter"):
        lines.append(section("Patience"))
        lines.append(r["patience_filter"].get("note", ""))
    lines.append(line("="))
    return "\n".join(str(x) for x in lines if x is not None)
