"""Auto ML learning wrapper for trade outcomes.

This does not replace the Phase 9 hybrid ML ensemble. It adds a lightweight,
explainable outcome learner using the journal so Blue can adapt before the
heavier models have enough data.
"""
from __future__ import annotations

from typing import Any, Dict

from memory.trade_memory_brain import memory_snapshot_for_signal

def apply_outcome_learning(signal: Dict[str, Any]) -> Dict[str, Any]:
    memory = memory_snapshot_for_signal(signal)
    signal["trade_memory"] = memory
    adj = int(memory.get("confidence_adjustment") or 0)
    if adj and signal.get("action") != "WAIT":
        old = int(signal.get("confidence") or 0)
        signal["confidence"] = max(0, min(99, old + adj))
        signal["auto_ml_learning"] = {
            "mode": "journal_outcome_learning",
            "old_confidence": old,
            "new_confidence": signal["confidence"],
            "adjustment": adj,
            "note": f"Confidence adjusted from trade memory. {memory.get('note', '')}",
        }
    else:
        signal["auto_ml_learning"] = {
            "mode": "journal_outcome_learning",
            "old_confidence": signal.get("confidence"),
            "new_confidence": signal.get("confidence"),
            "adjustment": 0,
            "note": memory.get("note", "No memory adjustment."),
        }
    return signal
