from __future__ import annotations

def coach_feedback(signal: dict) -> str:
    action = signal.get('action')
    conf = signal.get('confidence',0)
    if action == 'WAIT':
        return 'Coach note: Good discipline is waiting when the setup is unclear.'
    if conf < 72:
        return 'Coach note: Setup is valid but not elite. Consider smaller risk or wait for extra confirmation.'
    return 'Coach note: Setup has strong confluence. Still follow risk, SL, and news filter strictly.'
