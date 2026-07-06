import json
import sqlite3
from datetime import datetime
from config import DATABASE_FILE

def _connect():
    return sqlite3.connect(DATABASE_FILE)

def _ensure_column(cur, table, column, definition):
    """Add a missing column to older Blue databases without deleting saved journal data."""
    cols = [row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    con = _connect(); cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, symbol TEXT, ticker TEXT,
        action TEXT, confidence REAL, entry REAL, stop_loss REAL, target_1 REAL, target_2 REAL,
        lot_size REAL DEFAULT 0, result TEXT DEFAULT 'OPEN', pnl REAL DEFAULT 0, payload TEXT
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, closed_at TEXT, symbol TEXT, ticker TEXT,
        action TEXT, entry REAL, stop_loss REAL, target_1 REAL, target_2 REAL, lot_size REAL DEFAULT 0,
        reason TEXT, result TEXT DEFAULT 'OPEN', pnl REAL DEFAULT 0, rr REAL DEFAULT 0, notes TEXT,
        setup_type TEXT, market_regime TEXT, session TEXT, news_risk TEXT,
        spread_at_entry REAL DEFAULT 0, atr_at_entry REAL DEFAULT 0, rr_ratio REAL DEFAULT 0, outcome_label TEXT
    )''')

    # Migration for old databases created before lot-size/autopilot updates.
    # This fixes: sqlite3.OperationalError: table signals has no column named lot_size
    _ensure_column(cur, 'signals', 'lot_size', "REAL DEFAULT 0")
    _ensure_column(cur, 'signals', 'result', "TEXT DEFAULT 'OPEN'")
    _ensure_column(cur, 'signals', 'pnl', "REAL DEFAULT 0")
    _ensure_column(cur, 'signals', 'payload', "TEXT")
    _ensure_column(cur, 'journal', 'lot_size', "REAL DEFAULT 0")
    _ensure_column(cur, 'journal', 'rr', "REAL DEFAULT 0")
    _ensure_column(cur, 'journal', 'notes', "TEXT")
    _ensure_column(cur, 'journal', 'closed_at', "TEXT")
    # Phase 10 human trader memory columns
    _ensure_column(cur, 'journal', 'setup_type', "TEXT")
    _ensure_column(cur, 'journal', 'market_regime', "TEXT")
    _ensure_column(cur, 'journal', 'session', "TEXT")
    _ensure_column(cur, 'journal', 'news_risk', "TEXT")
    _ensure_column(cur, 'journal', 'spread_at_entry', "REAL DEFAULT 0")
    _ensure_column(cur, 'journal', 'atr_at_entry', "REAL DEFAULT 0")
    _ensure_column(cur, 'journal', 'rr_ratio', "REAL DEFAULT 0")
    _ensure_column(cur, 'journal', 'outcome_label', "TEXT")

    con.commit(); con.close()

def save_signal(signal):
    init_db(); con = _connect(); cur = con.cursor()
    lot = (signal.get('risk') or {}).get('recommended_lot_size', 0)
    payload = json.dumps(signal, default=str)
    cur.execute('''INSERT INTO signals(created_at, symbol, ticker, action, confidence, entry, stop_loss, target_1, target_2, lot_size, payload)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
        datetime.utcnow().isoformat(), signal.get('symbol'), signal.get('ticker'), signal.get('action'),
        signal.get('confidence'), signal.get('entry'), signal.get('stop_loss'), signal.get('target_1'),
        signal.get('target_2'), lot, payload))
    if signal.get('action') != 'WAIT':
        reward_risk = signal.get('reward_risk') or {}
        macro = signal.get('macro_brain') or {}
        context = signal.get('market_context') or {}
        cur.execute('''INSERT INTO journal(created_at, symbol, ticker, action, entry, stop_loss, target_1, target_2, lot_size, reason, notes,
            setup_type, market_regime, session, news_risk, rr_ratio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
            datetime.utcnow().isoformat(), signal.get('symbol'), signal.get('ticker'), signal.get('action'),
            signal.get('entry'), signal.get('stop_loss'), signal.get('target_1'), signal.get('target_2'),
            lot, signal.get('analyst_reason'), 'Auto-created from Phase 10 human trader signal engine',
            signal.get('setup_type'), context.get('regime_type') or signal.get('regime'), signal.get('session'),
            macro.get('note'), reward_risk.get('rr_to_tp2', 0)))
    con.commit(); con.close()

def list_open_trades():
    init_db(); con = _connect(); con.row_factory = sqlite3.Row; cur = con.cursor()
    rows = cur.execute("SELECT * FROM journal WHERE result='OPEN' ORDER BY id DESC").fetchall()
    con.close(); return [dict(r) for r in rows]

def close_trade(trade_id:int, result:str, pnl:float=0, rr:float=0, notes:str=''):
    init_db(); con = _connect(); cur = con.cursor()
    cur.execute("UPDATE journal SET result=?, pnl=?, rr=?, notes=?, closed_at=?, outcome_label=? WHERE id=?", (result.upper(), pnl, rr, notes, datetime.utcnow().isoformat(), result.upper(), trade_id))
    con.commit(); con.close()

def journal_stats(symbol=None, action=None):
    init_db(); con = _connect(); con.row_factory = sqlite3.Row; cur = con.cursor()
    q = "SELECT * FROM journal WHERE result!='OPEN'"; args=[]
    if symbol: q += " AND symbol=?"; args.append(symbol)
    if action: q += " AND action=?"; args.append(action)
    rows = cur.execute(q, args).fetchall(); con.close()
    total = len(rows)
    wins = sum(1 for r in rows if str(r['result']).upper() in ('WIN','TP','PROFIT'))
    losses = sum(1 for r in rows if str(r['result']).upper() in ('LOSS','SL'))
    gross_win = sum(float(r['pnl'] or 0) for r in rows if float(r['pnl'] or 0) > 0)
    gross_loss = abs(sum(float(r['pnl'] or 0) for r in rows if float(r['pnl'] or 0) < 0))
    return {
        'closed_trades': total, 'wins': wins, 'losses': losses,
        'win_rate': round((wins/total*100) if total else 0, 2),
        'net_pnl': round(sum(float(r['pnl'] or 0) for r in rows), 2),
        'profit_factor': round((gross_win/gross_loss) if gross_loss else (gross_win if gross_win else 0), 2)
    }
