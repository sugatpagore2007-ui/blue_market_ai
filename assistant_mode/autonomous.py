from __future__ import annotations
import time
from utils.symbols import resolve_symbol
from analysis.signal_engine import build_signal
from voice.speaker import speak
from mt5_bridge.auto_executor import execute_signal_if_allowed
from mt5_bridge.auto_manager import manage_once

DEFAULT_AUTONOMOUS_SYMBOLS = ['xauusd', 'xagusd', 'ethusd', 'btcusd', 'usoil', 'usdjpy', 'eurusd', 'ustec', 'gbpusd']


def _scan_one(symbol_text: str):
    name, ticker = resolve_symbol(symbol_text)
    if not ticker:
        return f'{symbol_text}: symbol not supported.'
    r = build_signal(name, ticker, account=None)
    line = f"{name}: {r['action']} confidence {r['confidence']} percent. {r.get('analyst_reason','')[:220]}"
    print(line)
    if r['action'] != 'WAIT':
        speak(line)
        auto_msg = execute_signal_if_allowed(r)
        print(auto_msg)
        speak(auto_msg)
    return line


def autonomous_watch(symbol_text='gold', minutes=5, scans=3):
    """Autonomous assistant. Scans one symbol or all pairs. Auto execution depends on config guardrails."""
    all_mode = str(symbol_text).strip().lower() in ['all', 'all pairs', 'market', 'markets', 'everything']
    symbols = DEFAULT_AUTONOMOUS_SYMBOLS if all_mode else [symbol_text]
    speak('Autonomous assistant mode started. Auto execution and auto manager will follow your config guardrails.')
    last = ''
    for i in range(scans):
        print(f'\nAutonomous cycle {i+1}/{scans}')
        for s in symbols:
            try:
                last = _scan_one(s)
            except Exception as e:
                last = f'Autonomous scan error on {s}: {e}'
                print(last)
        try:
            print(manage_once())
        except Exception as e:
            print('Auto manager error:', e)
        if i < scans - 1:
            time.sleep(max(5, int(minutes * 60)))
    speak('Autonomous assistant mode finished.')
    return 'Autonomous assistant mode finished.'
