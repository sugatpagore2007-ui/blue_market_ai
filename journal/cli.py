from storage.database import list_open_trades, close_trade, journal_stats

def show_open_trades():
    rows = list_open_trades()
    if not rows:
        print('No open journal trades.'); return
    for r in rows:
        print(f"#{r['id']} {r['symbol']} {r['action']} entry={r['entry']} SL={r['stop_loss']} lot={r['lot_size']}")

def close_trade_prompt():
    show_open_trades()
    try:
        tid = int(input('Trade id to close: ').strip())
        result = input('Result WIN/LOSS/BE/TP/SL: ').strip().upper()
        pnl = float(input('PnL amount: ').strip() or 0)
        rr = float(input('RR result, example 1.5 or -1: ').strip() or 0)
        notes = input('Notes: ').strip()
        close_trade(tid, result, pnl, rr, notes)
        print('Trade closed and learning stats updated.')
    except Exception as e:
        print('Could not close trade:', e)

def print_stats():
    print(journal_stats())
