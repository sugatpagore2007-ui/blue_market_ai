import json
import math
import os
from config import ACCOUNT_FILE, MAX_RISK_PERCENT, DEFAULT_RISK_PERCENT, LOT_SPECS


def load_account():
    if not os.path.exists(ACCOUNT_FILE):
        return None
    try:
        with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def save_account(balance: float, risk_percent: float):
    risk_percent = max(0.1, min(float(risk_percent), MAX_RISK_PERCENT))
    data = {"balance": float(balance), "risk_percent": risk_percent}
    with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    return data


def _read_float(prompt, default=None, min_value=None, max_value=None):
    while True:
        raw = input(prompt).strip()
        if not raw and default is not None:
            value = float(default)
        else:
            try:
                value = float(raw)
            except ValueError:
                print('Please enter numbers only, example: 10000 or 1')
                continue
        if min_value is not None and value < min_value:
            print(f'Value must be at least {min_value}.')
            continue
        if max_value is not None and value > max_value:
            print(f'Risk capped at {max_value}% for safer sizing.')
            value = max_value
        return value


def ask_account_if_missing():
    acc = load_account()
    if acc and acc.get('balance') and acc.get('risk_percent'):
        return acc
    print('\nFirst setup: Blue needs balance and risk % to calculate SL size and lot size.')
    balance = _read_float('Enter account balance: ', min_value=1)
    risk_percent = _read_float(f'Enter risk % per trade [{DEFAULT_RISK_PERCENT}]: ', default=DEFAULT_RISK_PERCENT, min_value=0.1, max_value=MAX_RISK_PERCENT)
    return save_account(balance, risk_percent)


def ask_account_after_analysis(symbol, action, entry, stop_loss, allow_saved=True):
    print('\nRisk setup after analysis')
    print('-' * 40)
    print(f'Signal : {symbol} {action}')
    print(f'Entry  : {entry}')
    print(f'SL     : {stop_loss}')
    saved = load_account() if allow_saved else None
    if saved:
        use = input(f"Use saved balance {saved['balance']} and risk {saved['risk_percent']}%? [Y/n]: ").strip().lower()
        if use in ['', 'y', 'yes']:
            return saved
    balance = _read_float('Enter account size/balance: ', min_value=1)
    risk_percent = _read_float(f'How much % risk to take? [{DEFAULT_RISK_PERCENT}]: ', default=DEFAULT_RISK_PERCENT, min_value=0.1, max_value=MAX_RISK_PERCENT)
    save = input('Save this risk setup for next signals? [Y/n]: ').strip().lower()
    if save in ['', 'y', 'yes']:
        return save_account(balance, risk_percent)
    return {"balance": balance, "risk_percent": risk_percent}


def _floor_to_step(value, step):
    if step <= 0:
        return value
    return math.floor(value / step) * step


def position_size(balance, risk_percent, entry, stop_loss, ticker=None):
    risk_amount = float(balance) * float(risk_percent) / 100
    per_unit_risk = abs(float(entry) - float(stop_loss))
    units = 0 if per_unit_risk == 0 else risk_amount / per_unit_risk

    spec = LOT_SPECS.get(ticker or '', {
        "asset": ticker or "Unknown", "contract_size": 1.0, "lot_step": 0.01,
        "min_lot": 0.01, "max_lot": 100.0, "unit_name": "units"
    })
    raw_lots = units / float(spec['contract_size']) if spec['contract_size'] else 0
    stepped_lots = _floor_to_step(raw_lots, float(spec['lot_step']))
    capped_lots = max(0.0, min(stepped_lots, float(spec['max_lot'])))
    tradable = capped_lots >= float(spec['min_lot']) and per_unit_risk > 0
    suggested_lots = capped_lots if tradable else 0.0
    actual_units = suggested_lots * float(spec['contract_size'])
    actual_risk = actual_units * per_unit_risk

    return {
        'balance': round(float(balance), 2),
        'risk_percent': round(float(risk_percent), 2),
        'risk_amount': round(risk_amount, 2),
        'per_unit_risk': round(per_unit_risk, 6),
        'estimated_units': round(units, 6),
        'contract_size': spec['contract_size'],
        'unit_name': spec['unit_name'],
        'lot_step': spec['lot_step'],
        'min_lot': spec['min_lot'],
        'raw_lot_size': round(raw_lots, 6),
        # raw_lot_size is the exact risk-based sizing. recommended_lot_size is what we display
        # to the user so they can see the true calculated size even when it is below
        # the broker minimum. broker_executable_lot is the rounded lot that may be executable.
        'recommended_lot_size': round(raw_lots, 5),
        'broker_executable_lot': round(suggested_lots, 3),
        'actual_units_at_lot': round(actual_units, 6),
        'actual_risk_at_lot': round(actual_risk, 2),
        'tradable': tradable,
        'lot_note': (
            f"Use about {round(suggested_lots, 3)} lots based on {spec['asset']} contract size."
            if tradable else
            f"Risk-based lot is {round(raw_lots, 5)}, below broker minimum {spec['min_lot']}. Do not force a larger lot unless you accept higher risk."
        ),
        'broker_warning': 'Lot size uses default contract assumptions. Confirm contract size, tick value, min lot, and leverage in your broker/MT5 symbol specification.'
    }


def empty_risk(balance=0, risk_percent=0):
    return {
        'balance': round(float(balance or 0), 2), 'risk_percent': round(float(risk_percent or 0), 2),
        'risk_amount': 0, 'per_unit_risk': 0, 'estimated_units': 0,
        'contract_size': 0, 'unit_name': 'units', 'lot_step': 0, 'min_lot': 0,
        'raw_lot_size': 0, 'recommended_lot_size': 0, 'actual_units_at_lot': 0,
        'actual_risk_at_lot': 0, 'tradable': False,
        'lot_note': 'No lot size because there is no actionable trade.',
        'broker_warning': 'No trade.'
    }
