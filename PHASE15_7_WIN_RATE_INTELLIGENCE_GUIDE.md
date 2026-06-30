# Phase 15.7 — Win Rate Intelligence

Blue can now show a full win-rate/performance report from both text and voice.

## What it reads

1. **Connected MT5 account history** — primary source when MT5 is connected.
2. **Blue journal/demo trades** — trades saved or closed inside Blue.
3. **Imported ML dataset rows** — ready ML datasets, MT5 imports, journal imports, and backtest imports.

This is read-only. It never places, closes, or modifies trades.

## Text commands

```text
win rate
connected account win rate
account win rate
show my win rate
show everything
stats
performance
gold win rate
btc win rate
eur win rate
gbp win rate
jpy win rate
take out win rate of btc
win rate 30d
win rate gold 180d
win rate help
```

## Voice commands

```text
hey blue show my win rate
hey blue connected account win rate
hey blue take out win rate of btc
hey blue show everything
hey blue gold win rate
```

## Report sections

- Connected account number/server/balance/equity
- Closed trades count
- Win/loss/breakeven count
- Win rate
- Net profit
- Gross win/loss
- Profit factor
- Average trade
- Average win/loss
- Win rate by symbol
- Win rate by direction
- Recent closed trades
- Blue journal memory
- Imported ML dataset memory
- Dataset win rate by setup/session

## Notes

- The default history window is **90 days**.
- Use `win rate 30d` or `win rate 180d` for a different period.
- MT5 must already be open and logged in to show connected-account win rate.
- Historical win rate helps analysis, but it does not guarantee future results.
