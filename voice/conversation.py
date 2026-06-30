"""Human-style voice conversation helpers for Blue Market AI.
This module keeps a tiny in-session memory so voice mode feels like a conversation,
not only a command runner.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConversationState:
    last_result: Optional[Dict[str, Any]] = None
    last_symbol: Optional[str] = None
    last_reply: str = ""
    detail_mode: str = "normal"  # short | normal | detailed
    history: List[str] = field(default_factory=list)

    def remember_user(self, text: str) -> None:
        text = (text or "").strip()
        if text:
            self.history.append("User: " + text)
            self.history[:] = self.history[-12:]

    def remember_assistant(self, text: str) -> None:
        text = (text or "").strip()
        if text:
            self.last_reply = text
            self.history.append("Blue: " + text[:600])
            self.history[:] = self.history[-12:]


conversation = ConversationState()


def _safe(v: Any, fallback: str = "not available") -> str:
    if v is None or v == "":
        return fallback
    return str(v)


def detect_conversation_intent(text: str) -> str:
    """Return special conversational intent, or empty string for normal command parsing."""
    t = (text or "").lower().strip()
    if not t:
        return ""
    if t in {"why", "why this", "why buy", "why sell", "explain", "explain it", "explain this"}:
        return "why_last"
    if t in {"repeat", "say again", "again", "repeat that", "what did you say"}:
        return "repeat_last"
    if any(x in t for x in ["what is entry", "entry price", "where is entry", "entry level"]):
        return "entry_last"
    if any(x in t for x in ["what is stop", "stop loss", "sl level", "where is sl"]):
        return "sl_last"
    if any(x in t for x in ["target", "tp", "take profit"]):
        return "targets_last"
    if any(x in t for x in ["lot", "lot size", "position size", "how much lot"]):
        return "lot_last"
    if any(x in t for x in ["short answer", "be short", "quick reply", "short mode"]):
        return "set_short"
    if any(x in t for x in ["detailed answer", "full detail", "explain deeply", "detail mode"]):
        return "set_detailed"
    if any(x in t for x in ["normal answer", "normal mode"]):
        return "set_normal"
    if any(x in t for x in ["what do you think", "your view", "your opinion"]):
        return "market_opinion"  # let parser also catch symbol if present
    return ""


def answer_conversation_intent(intent: str) -> Optional[str]:
    r = conversation.last_result
    if intent == "set_short":
        conversation.detail_mode = "short"
        return "Okay, I will keep voice replies short and direct."
    if intent == "set_detailed":
        conversation.detail_mode = "detailed"
        return "Okay, I will explain like a full analyst, including structure, liquidity, entry logic, and risk."
    if intent == "set_normal":
        conversation.detail_mode = "normal"
        return "Okay, I will use normal analyst replies."
    if intent == "repeat_last":
        return conversation.last_reply or "I do not have a previous answer to repeat yet."
    if not r:
        return None
    risk = r.get("risk", {}) or {}
    if intent == "why_last":
        return "The reason is: " + _safe(r.get("analyst_reason") or r.get("human_read"), "I do not have a stored reason yet.")
    if intent == "entry_last":
        return f"The entry for {r.get('symbol', 'this setup')} is {_safe(r.get('entry'))}."
    if intent == "sl_last":
        return f"The stop loss for {r.get('symbol', 'this setup')} is {_safe(r.get('stop_loss'))}."
    if intent == "targets_last":
        return f"Target one is {_safe(r.get('target_1'))}. Target two is {_safe(r.get('target_2'))}."
    if intent == "lot_last":
        return f"Recommended lot size is {_safe(risk.get('recommended_lot_size'), '0')} lots. {risk.get('lot_note', '')}"
    return None


def make_human_voice_brief(r: Dict[str, Any]) -> str:
    """Create a more natural spoken analyst explanation."""
    conversation.last_result = r
    conversation.last_symbol = r.get("symbol")

    risk = r.get("risk", {}) or {}
    lot = risk.get("recommended_lot_size", 0)
    lot_note = risk.get("lot_note", "")
    reason = r.get("analyst_reason") or r.get("human_read") or "No detailed reason was generated."
    mgmt = (r.get("management_plan") or {}).get("plan_text", "")
    sentiment = (r.get("sentiment") or {}).get("note", "")
    heat = r.get("liquidity_heatmap") or []
    heat_text = ""
    if heat:
        top = ", ".join([f"{z.get('side', 'nearby')} liquidity around {round(float(z.get('level', 0)), 4)}" for z in heat[:3]])
        heat_text = f" Liquidity map is showing {top}."

    symbol = r.get("symbol", "this market")
    style = r.get("trade_style_label", "Intraday")
    entry_tf = r.get("entry_timeframe", "5m")
    action = r.get("action", "WAIT")
    confidence = r.get("confidence", 0)

    if action == "WAIT":
        reply = f"For {symbol}, I would wait in {style} mode. Blue checked all timeframes, and the planned execution chart is {entry_tf}. Confidence is only {confidence} percent. The reason is: {reason}"
        conversation.remember_assistant(reply)
        return reply

    if conversation.detail_mode == "short":
        reply = (
            f"{symbol}: {action}. Entry {r.get('entry')}, stop loss {r.get('stop_loss')}, "
            f"target one {r.get('target_1')}, target two {r.get('target_2')}, lot size {lot}. "
            f"Main reason: {reason}"
        )
    elif conversation.detail_mode == "detailed":
        reply = (
            f"Here is my full analyst read on {symbol}. Style is {style}, and execution is planned from the {entry_tf} chart. The setup is {action}, with {confidence} percent confidence. "
            f"The planned entry is {r.get('entry')}. The stop loss is {r.get('stop_loss')}. "
            f"Target one is {r.get('target_1')}, and target two is {r.get('target_2')}. "
            f"Based on your account balance and risk percentage, the calculated lot size is {lot} lots. {lot_note}. "
            f"The trade logic is this: {reason}. "
            f"For management: {mgmt or 'manage it only after price confirms continuation; do not chase late entries.'}. "
            f"Sentiment note: {sentiment or 'no strong sentiment warning available.'}.{heat_text} "
            f"My practical view: wait for the entry area, respect the stop loss, and avoid increasing lot size just because the setup looks strong."
        )
    else:
        reply = (
            f"For {symbol}, my {style} read is {action} with {confidence} percent confidence. Entry is planned from the {entry_tf} chart. "
            f"Entry is {r.get('entry')}, stop loss is {r.get('stop_loss')}, target one is {r.get('target_1')}, "
            f"and target two is {r.get('target_2')}. The recommended lot size is {lot} lots. "
            f"Reason: {reason}.{heat_text}"
        )
    conversation.remember_assistant(reply)
    return reply
