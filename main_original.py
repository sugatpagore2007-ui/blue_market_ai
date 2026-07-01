from utils.symbols import resolve_symbol, list_symbols
from risk.account import ask_account_if_missing, save_account, load_account
from analysis.signal_engine import build_signal
from storage.database import save_signal
from research.monte_carlo import run_monte_carlo


def print_signal(r):
    print("\n" + "=" * 60)
    print(f"{r['symbol']} SIGNAL: {r['action']} | Confidence: {r['confidence']}%")
    print("-" * 60)
    print(f"Entry     : {r['entry']}")
    print(f"Stop Loss : {r['stop_loss']}")
    print(f"Target 1  : {r['target_1']}")
    print(f"Target 2  : {r['target_2']}")
    print(f"Risk cash : {r['risk']['risk_amount']}")
    print(f"Units est.: {r['risk']['estimated_units']}")
    print(f"Session   : {r['session']} — {r['session_note']}")
    print(f"Regime    : {r['regime']}")
    print(f"News      : {r['news_caution']}")
    print("\nHuman-style read:")
    print(r["human_read"])
    print("\nTimeframes:")
    for tf, d in r["timeframes"].items():
        print(f"  {tf:<4} {d['role']:<22} score={d['score']} reason={', '.join(d['why'])}")
    print("=" * 60 + "\n")


def scan_one(text):
    account = ask_account_if_missing()
    name, ticker = resolve_symbol(text)
    if not ticker:
        print("Supported charts:", ", ".join(list_symbols()))
        return
    result = build_signal(name, ticker, account)
    print_signal(result)
    save_signal(result)


def strongest():
    account = ask_account_if_missing()
    results = []
    unique = ["gold", "eurusd", "btc", "eth", "usoil"]
    for s in unique:
        name, ticker = resolve_symbol(s)
        try:
            results.append(build_signal(name, ticker, account))
        except Exception as e:
            print(f"Skipped {s}: {e}")
    results.sort(key=lambda x: x["confidence"], reverse=True)
    for r in results[:3]:
        print_signal(r)
        save_signal(r)


def set_account():
    balance = float(input("Enter account size/balance: ").strip())
    risk_percent = float(input("Enter risk percent per idea: ").strip())
    save_account(balance, risk_percent)
    print("Saved.")


def main():
    print("Blue Market AI Phase 3")
    print("Commands: check gold | check btc | check eurusd | strongest | account | risk-test | exit")
    while True:
        cmd = input("Blue > ").strip().lower()
        if cmd in ["exit", "quit"]:
            break
        if cmd == "account":
            set_account(); continue
        if cmd == "strongest":
            strongest(); continue
        if cmd == "risk-test":
            acc = load_account() or ask_account_if_missing()
            print(run_monte_carlo(risk_percent=acc["risk_percent"]))
            continue
        scan_one(cmd)

if __name__ == "__main__":
    main()
