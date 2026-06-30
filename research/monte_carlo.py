import random

def run_monte_carlo(risk_percent=1.0, trades=100, simulations=500, win_rate=0.45, avg_rr=2.0):
    endings = []
    max_dds = []
    for _ in range(simulations):
        equity = 100.0
        peak = equity
        max_dd = 0.0
        for _ in range(trades):
            risk = equity * (risk_percent / 100)
            if random.random() < win_rate:
                equity += risk * avg_rr
            else:
                equity -= risk
            peak = max(peak, equity)
            max_dd = max(max_dd, (peak - equity) / peak * 100)
        endings.append(equity)
        max_dds.append(max_dd)
    endings.sort(); max_dds.sort()
    return {
        'risk_percent': risk_percent,
        'trades': trades,
        'simulations': simulations,
        'median_end_equity_index': round(endings[len(endings)//2], 2),
        'worst_5pct_end_equity_index': round(endings[int(simulations*0.05)], 2),
        'median_max_drawdown_pct': round(max_dds[len(max_dds)//2], 2),
        'bad_case_drawdown_pct': round(max_dds[int(simulations*0.95)], 2),
    }
