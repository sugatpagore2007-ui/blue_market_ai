from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ManagementPlan:
    breakeven_trigger: float
    partial_1_trigger: float
    trailing_start: float
    invalidation: str
    plan_text: str


def build_management_plan(signal: dict) -> dict:
    action = signal.get('action')
    entry = float(signal.get('entry') or 0)
    sl = float(signal.get('stop_loss') or entry)
    t1 = float(signal.get('target_1') or entry)
    t2 = float(signal.get('target_2') or entry)
    if action == 'WAIT' or entry == sl:
        return {
            'mode': 'standby',
            'plan_text': 'No active management plan because there is no clean trade setup.',
            'breakeven_trigger': None,
            'partial_1_trigger': None,
            'trailing_start': None,
        }
    risk = abs(entry - sl)
    if action == 'BUY':
        be = entry + risk
        trail = entry + risk * 1.5
        invalidation = f'If price closes below {sl}, the buy idea is invalid.'
    else:
        be = entry - risk
        trail = entry - risk * 1.5
        invalidation = f'If price closes above {sl}, the sell idea is invalid.'
    text = (
        f'Manage this trade in stages. At 1R near {round(be, 5)}, consider moving stop loss to breakeven. '
        f'At Target 1 near {round(t1, 5)}, consider taking partial profit. '
        f'After Target 1, trail behind the latest protected swing or FVG. Final target is {round(t2, 5)}. '
        f'{invalidation}'
    )
    return {
        'mode': 'rule_based',
        'breakeven_trigger': round(be, 6),
        'partial_1_trigger': round(t1, 6),
        'trailing_start': round(trail, 6),
        'final_target': round(t2, 6),
        'invalidation': invalidation,
        'plan_text': text,
    }


def management_help() -> str:
    return (
        'Smart trade management watches the setup after entry. It gives breakeven, partial-profit, trailing-stop, '
        'and invalidation instructions. It does not place trades automatically.'
    )
